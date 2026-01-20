#!/usr/bin/env bash
# Render build script - fixes Rust compilation issues for tiktoken

set -e

echo "==> Setting up Cargo environment..."
export CARGO_HOME=/tmp/cargo
export RUSTUP_HOME=/tmp/rustup
export CARGO_NET_GIT_FETCH_WITH_CLI=true
mkdir -p $CARGO_HOME

echo "==> Upgrading pip..."
pip install --upgrade pip wheel setuptools

echo "==> Installing core dependencies first..."
# Install packages that don't need tiktoken
pip install fastapi uvicorn pydantic python-dotenv numpy tqdm requests groq faiss-cpu

echo "==> Installing sentence-transformers (may pull tiktoken)..."
# Try with --no-deps first to avoid tiktoken, then install remaining deps
pip install --no-deps sentence-transformers transformers huggingface-hub tokenizers safetensors

# Install the actual dependencies these packages need (without tiktoken)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install scipy scikit-learn pillow regex filelock packaging pyyaml

echo "==> Verifying installation..."
python -c "import fastapi; import sentence_transformers; import faiss; print('All imports successful!')"

echo "==> Build complete!"
