// Servidor de Qwen3-TTS para Cacao: proceso hijo por tubería (stdin/stdout), sin red ni puertos.
// Se compila contra llama.cpp 81bc6b83f827df746eb129235488d325c49cae52 (compilar.bat); basado en tools/tts/tts.cpp.
//
// Arranque: los argumentos de llama (-m, --mmproj, --tts-speaker-file, --tts-lang, -ngl, -c, --seed...). Carga el
// modelo y la voz, sintetiza «hola» para calentar y escribe «LISTO <tasa>\n» en stdout.
// Pedido (stdin, UTF-8, una línea): «<id>\t<texto>\n». Respuesta (stdout, binario):
//   «A <id> <muestras> <tasa>\n» seguido de <muestras> int16 LE (mono), o «E <id> <motivo>\n».
// «SALIR\n» o el fin de stdin terminan el proceso. Los registros de llama van a stderr.
#include "arg.h"
#include "common.h"
#include "log.h"
#include "sampling.h"
#include "llama.h"
#include "mtmd.h"
#include "mtmd-helper.h"

#include <cmath>
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

struct Motor {
    common_params & params;
    llama_context * lctx;
    common_sampler * smpl;
    mtmd_context * mctx;
    mtmd_bitmap * speaker;
    mtmd_helper::gen_audio gen;

    // devuelve 0 y rellena pcm/tasa, o != 0 con el motivo
    int sintetizar(const std::string & texto, std::vector<int16_t> & pcm, int32_t & tasa, std::string & motivo) {
        gen.reset();
        llama_memory_clear(llama_get_memory(lctx), true);
        common_sampler_reset(smpl);
        mtmd_helper_gen_audio_inp inp{};
        inp.seq_id      = 0;
        inp.prompt      = texto.c_str();
        inp.prompt_len  = texto.size();
        inp.speaker_ref = speaker;
        inp.lang        = params.tts_lang.c_str();
        inp.top_k       = params.sampling.top_k;
        inp.top_p       = params.sampling.top_p;
        inp.seed        = params.sampling.seed;
        inp.out_type    = MTMD_HELPER_GEN_AUDIO_OUTTYPE_PCM;
        if (gen.set_input(&inp) != 0) { motivo = "set_input"; return 1; }
        for (;;) {
            int32_t r = gen.step_prompt(params.n_batch);
            if (r < 0) { motivo = "prompt"; return 1; }
            if (r == 0) break;
        }
        llama_token t = common_sampler_sample(smpl, lctx, -1);
        common_sampler_accept(smpl, t, true);
        const float * h = llama_get_embeddings_ith(lctx, -1);
        const int max_new = params.n_predict > 0 ? params.n_predict : 600;
        int frames = 0;
        bool stop = false;
        while (!stop && frames < max_new) {
            const float * h2 = nullptr;
            if (gen.step_gen(t, h, &h2, &stop) != 0) { motivo = "step_gen"; return 1; }
            if (!h2) break;
            frames++;
            h = h2;
            t = common_sampler_sample(smpl, lctx, -1);
            common_sampler_accept(smpl, t, true);
        }
        if (!stop && frames >= max_new) { motivo = "limite_de_tramas"; return 1; }
        const char * datos = nullptr; size_t len = 0; int64_t n = 0;
        if (gen.get_output(&tasa, &datos, &len, &n) != 0) { motivo = "salida"; return 1; }
        const float * f = (const float *) datos;
        const size_t muestras = len / sizeof(float);
        pcm.resize(muestras);
        for (size_t i = 0; i < muestras; i++) {
            float v = f[i] * 32767.0f;
            pcm[i] = (int16_t) (v > 32767.0f ? 32767 : (v < -32768.0f ? -32768 : std::lround(v)));
        }
        return 0;
    }
};

int main(int argc, char ** argv) {
#ifdef _WIN32
    _setmode(_fileno(stdout), _O_BINARY);
    _setmode(_fileno(stdin), _O_BINARY);
#endif
    common_params params;
    common_init();
    params.prompt = "hola";  // el analizador de argumentos de tts lo exige; los textos llegan por stdin
    if (!common_params_parse(argc, argv, params, LLAMA_EXAMPLE_TTS, nullptr)) {
        return 1;
    }
    mtmd_helper_log_set(common_log_default_callback, nullptr);
    params.embedding = true;

    llama_backend_init();
    auto llama_init = common_init_from_params(params);
    llama_model   * model = llama_init->model();
    llama_context * lctx  = llama_init->context();
    common_sampler * smpl = llama_init->sampler(0);
    if (!model || !lctx || !smpl) { LOG_ERR("init fallido\n"); return 2; }
    mtmd_context_params mp = mtmd_context_params_default();
    mp.use_gpu = params.mmproj_use_gpu;
    mp.device  = params.mmproj_device;
    mtmd::context_ptr mctx(mtmd_init_from_file(params.mmproj.path.c_str(), model, mp));
    if (!mctx) { LOG_ERR("mmproj fallido\n"); return 3; }
    if (mtmd_gen_audio_get_info(mctx.get()).type == MTMD_GEN_AUDIO_TYPE_NONE) { LOG_ERR("sin audio\n"); return 3; }
    mtmd::bitmap_ptr speaker;
    if (!params.tts_speaker_file.empty()) {
        auto w = mtmd_helper_bitmap_init_from_file(mctx.get(), params.tts_speaker_file.c_str(), false,
                                                   mtmd_helper_init_opt_default());
        if (!w.bitmap) { LOG_ERR("referencia fallida\n"); return 4; }
        speaker.reset(w.bitmap);
    }

    Motor motor{params, lctx, smpl, mctx.get(), speaker.get(), mtmd_helper::gen_audio(lctx, mctx.get())};
    std::vector<int16_t> pcm;
    int32_t tasa = 0;
    std::string motivo;
    if (motor.sintetizar("Hola.", pcm, tasa, motivo) != 0) { LOG_ERR("calentamiento: %s\n", motivo.c_str()); return 5; }
    printf("LISTO %d\n", tasa);
    fflush(stdout);

    std::string linea;
    while (std::getline(std::cin, linea)) {
        if (!linea.empty() && linea.back() == '\r') linea.pop_back();
        if (linea == "SALIR") break;
        const size_t tab = linea.find('\t');
        if (tab == std::string::npos) continue;
        const std::string id = linea.substr(0, tab), texto = linea.substr(tab + 1);
        if (texto.empty()) {
            printf("E %s vacio\n", id.c_str());
            fflush(stdout);
            continue;
        }
        if (motor.sintetizar(texto, pcm, tasa, motivo) != 0) {
            printf("E %s %s\n", id.c_str(), motivo.c_str());
            fflush(stdout);
            continue;
        }
        printf("A %s %zu %d\n", id.c_str(), pcm.size(), tasa);
        fwrite(pcm.data(), sizeof(int16_t), pcm.size(), stdout);
        fflush(stdout);
    }
    llama_backend_free();
    return 0;
}
