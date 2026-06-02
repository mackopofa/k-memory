# ════════════════════════════════════════════
# K-Memory — The Memory Key for AI Systems
# ════════════════════════════════════════════

<div align="center">
  <a href="https://github.com/mackopofa/k-memory">
    <img src="https://img.shields.io/badge/K-Memory-KensaiArt-blueviolet?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgdmlld0JveD0iMCAwIDY0IDY0Ij48cGF0aCBkPSJNMzIgMkwyIDMyaDMwVjJ6TTMyIDYybDMwLTMwSDMyVjYyeiIgZmlsbD0iIzhCNkRGRiIvPjwvc3ZnPg==" alt="KensaiArt"/>
  </a>
  <br/>
  <sub><b>KensaiArt</b> — architecture & design ⚔️ <i>Stronger every day.</i></sub>
</div>

<br/>

A self-deploying persistent memory that detects your environment (OS, LLM, providers, agents), installs itself, and becomes the permanent memory of any AI system — without dependencies, without cloud, without limits.

## One-Click Install

```bash
curl -sL https://raw.githubusercontent.com/mackopofa/k-memory/main/install.sh | bash
```

Or manually:
```bash
git clone https://github.com/mackopofa/k-memory.git
cd k-memory
bash install.sh
```

## Usage

```bash
# View memory status
python3 k-core.py

# Remember an important fact
python3 k-core.py --remember "The user prefers concise responses"

# Search memory
python3 k-core.py --recall "user preferences"

# Read all decisions
cat k-memory/brain/decisions.md
```

## Architecture

```
k-memory/
├── install.sh        # Auto-installer (detects everything)
├── k-detector.py     # Environment detector
├── k-core.py         # Core memory engine
├── brain/            # Memory files (lobes)
│   ├── decisions.md
│   ├── directives.md
│   ├── evolution.md
│   └── system-identity.md
├── graph.json        # Knowledge graph
└── index.md          # Table of contents
```

## Auto-Detection

K-Memory automatically discovers:
- **OS**: Linux, macOS, Windows (WSL)
- **LLM Providers**: OpenAI, Anthropic, DeepSeek, OpenRouter, Ollama (local)
- **Agents**: Hermes, Claude Code, Codex
- **API Keys**: from .env, config.yaml, environment variables
- **GPU**: NVIDIA (nvidia-smi), ROCm, Metal
- **Storage**: available disk space
- **Existing memory**: integrates any existing files
- **Cron**: sets up 6h maintenance automatically

## Dependencies

- Python 3.8+
- Bash
- Zero external libraries

100% local. 100% free. Nothing is forgotten.

---

📦 **K-Memory** — Built for the Kensai System  
🎨 **KensaiArt** — architecture & design  
⚔️ *Stronger every day.*
