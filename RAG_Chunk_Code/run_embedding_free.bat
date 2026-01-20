@echo off
REM Wrapper script to run free embedding with proper environment variables
REM This prevents TensorFlow DLL errors

set TRANSFORMERS_NO_TF=1
set TF_CPP_MIN_LOG_LEVEL=3

python embed_chunks_free.py %*
