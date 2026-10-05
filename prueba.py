from llama_cpp import Llama
from pathlib import Path

modelo = next(Path("modelos").glob("*.gguf"))
from guardia_juego import exigir_gpu_libre

exigir_gpu_libre("el modelo")
llm = Llama(model_path=str(modelo), n_gpu_layers=-1, n_ctx=8192, verbose=True)
r = llm.create_chat_completion(messages=[{"role": "user", "content": "Hola, preséntate en una frase."}])
print(r["choices"][0]["message"]["content"])
