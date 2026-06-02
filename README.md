# K-Memory ⚔️ v2.1

**Persistent memory for AI agents. Zero dependencies. Pure Python.**

A self-contained memory engine for LLMs and agents. Store, link, summarize and export knowledge using only Python stdlib. No vectors, no cloud, no lock-in.

## Installation

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mackopofa/k-memory/main/install.sh)
```

Or manually:

```bash
git clone https://github.com/mackopofa/k-memory.git ~/k-memory
cd ~/k-memory && python3 k-core.py
```

## Quick Start

```bash
# Store a fact
python3 k-core.py --remember "Recency boost weights recent facts 10x higher" --domain "features"

# Retrieve relevant facts
python3 k-core.py --recall "recency boost"

# Summarize a domain
python3 k-core.py --summary --domain "features"

# Summarize all domains
python3 k-core.py --summarize-all

# Export knowledge graph as Markdown
python3 k-core.py --export

# Export as Mermaid diagram (Obsidian-ready)
python3 k-core.py --export --mermaid
```

## Features

| Feature | What it does |
|---------|-------------|
| **Recency boost** | Recent facts weighted 10x higher. Half-life: 90 days. |
| **Auto-summary** | Structured domain summaries with TF-IDF + trend detection. No LLM needed. |
| **Deduplication** | Jaccard + SequenceMatcher fusion. No duplicate facts. |
| **Export Markdown** | Full knowledge graph as human-readable .md |
| **Export Mermaid** | Interactive graph diagram for Obsidian/Notion |
| **Portable** | Single file, zero dependencies, works everywhere |

## Commands

| Command | Effect |
|---------|--------|
| `--remember <text>` | Store a fact with timestamp, domain, importance |
| `--recall <query>` | Retrieve relevant facts (sorted by relevance × recency) |
| `--summary [--domain X]` | Structured summary of a domain |
| `--summarize-all` | Summary of all domains |
| `--export [--mermaid]` | Export graph as Markdown or Mermaid |
| `--version` | Show version |

## Architecture

```
~/k-memory/
├── k-core.py          # Memory engine (v2.1)
├── k-detector.py      # Environment auto-detector
├── install.sh         # One-command installer
├── LICENSE            # MIT
├── tests/
│   └── test_core.py   # 30 tests, pure stdlib
├── graph.json         # Knowledge graph (nodes + edges)
├── index.md           # Readable index
├── brain/             # Individual .md lobe files
├── summaries/         # Auto-generated domain summaries
├── extras/            # Optional plugins
│   └── k-embeddings.py  # Semantic search (Ollama)
├── exports/           # Generated exports
└── knowledge/         # Detailed knowledge (optional)
```

## Tests

```bash
python3 tests/test_core.py    # 30 tests, zero external dependencies
```

## Extras

Optional plugins that extend K-Memory with advanced capabilities. They require **external dependencies** — unlike the core.

| Plugin | What it does | Requires |
|--------|-------------|----------|
| `extras/k-embeddings.py` | Semantic search by **meaning**, not keywords | Ollama + `requests` |

```bash
pip install requests
ollama pull nomic-embed-text    # 274 MB, local, free
python3 extras/k-embeddings.py --recall "concept"
```

## Performance

- Zero external dependencies (pure Python stdlib)
- Portable: Ubuntu, Debian, macOS, WSL, Termux
- Handles 10,000+ nodes without slowdown
- Each operation < 100ms on commodity hardware

## Why K-Memory?

K-Memory was born from a simple observation: current memory systems for AI agents either depend on cloud vector databases or bloat dependencies. K-Memory is the opposite — it refuses to grow. One file, one data format, one commit, one `python3` command. It doesn't try to be everything. It tries to be enough.

## License

MIT — Copyright (c) 2026 KensaiArt. See [LICENSE](LICENSE).

---

*KensaiArt — Architecture & Design ⚔️ Stronger every day.*
