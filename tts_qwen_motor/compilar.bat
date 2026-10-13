@echo off
rem Compila servidor.cpp contra un build de llama.cpp en el commit fijado (81bc6b83f827df746eb129235488d325c49cae52,
rem con GGML_CUDA=ON, CUDA 13.4, sm_120, LLAMA_CURL=OFF, LLAMA_OPENSSL=OFF; ver cerebro/decisiones/qwen3-tts-windows.md).
rem Uso: tts_qwen_motor\compilar.bat <carpeta llama.cpp> <carpeta de salida>
setlocal
set "L=%~1"
set "O=%~2"
if "%L%"=="" exit /b 2
if "%O%"=="" exit /b 2
for /f %%h in ('git -C "%L%" rev-parse HEAD') do set "SHA=%%h"
if not "%SHA%"=="81bc6b83f827df746eb129235488d325c49cae52" (
  echo llama.cpp no esta en el commit fijado: %SHA%
  exit /b 3
)
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 4
cl /nologo /EHsc /O2 /std:c++17 /utf-8 /MD "%~dp0servidor.cpp" /Fo"%O%\\" /Fe"%O%\tts_qwen_servidor.exe" ^
  /I"%L%\common" /I"%L%\include" /I"%L%\ggml\include" /I"%L%\tools\mtmd" /I"%L%\vendor" ^
  /link /LIBPATH:"%L%\build\common" /LIBPATH:"%L%\build\src" /LIBPATH:"%L%\build\tools\mtmd" /LIBPATH:"%L%\build\ggml\src" ^
  llama-common.lib llama-common-base.lib llama.lib mtmd.lib ggml.lib ggml-base.lib || exit /b 5
del "%O%\servidor.obj" 2>nul
echo COMPILADO
