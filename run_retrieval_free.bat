@echo off
REM Wrapper script to run free retrieval with proper environment variables

set TRANSFORMERS_NO_TF=1
set TF_CPP_MIN_LOG_LEVEL=3

python retrieve_chunks_free.py %*
