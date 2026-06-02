# K-Memory Extras — Optional plugins

These plugins extend K-Memory with advanced capabilities. They require **external dependencies** — unlike `k-core.py` which is pure Python stdlib.

## Semantic Search — `k-embeddings.py`

Adds vector similarity search via Ollama (local, free, private). Finds facts by **meaning**, not just keywords.

**Requirements:**
- Ollama installed → `curl -fsSL https://ollama.ai/install.sh | sh`
- Embedding model → `ollama pull nomic-embed-text` (274 MB)
- Python `requests` → `pip install requests`

**Usage:**
```bash
python3 extras/k-embeddings.py --remember "Le chat dort sur le canapé" --domain maison
python3 extras/k-embeddings.py --recall "animal endormi"   # finds "chat" without the word!
python3 extras/k-embeddings.py --auto-summarize            # cluster facts by meaning
python3 extras/k-embeddings.py --backend ollama|keywords   # switch mode
```

**How it works:**
- At `--remember`: generates a 768-dim vector via Ollama, stores it alongside the fact
- At `--recall`: compares your query vector against all stored vectors using cosine similarity
- Falls back to keyword search if Ollama is unavailable

**Why it's in extras/:**
K-Memory's core promise is "zero dependencies — just `python3`". Adding `requests` and Ollama would break that contract. By keeping it in `extras/`, users who want semantic search can opt in without compromising the core.
