# ════════════════════════════════════════════
# K-Memory — Clé de Mémoire du Kensai System
# ════════════════════════════════════════════

Une mémoire persistante qui se déploie toute seule.
Détecte l'environnement (OS, LLM, IA, providers), s'installe,
et devient la mémoire permanente de n'importe quel système.

## Installation

```bash
# 1. Télécharger les fichiers
git clone https://github.com/mackopopa/k-memory.git
cd k-memory

# 2. Installer (auto-détection complète)
bash install.sh
```

Ou en un clic :
```bash
curl -sL https://raw.githubusercontent.com/mackopopa/k-memory/main/install.sh | bash
```

## Utilisation

```bash
# Voir l'état de la mémoire
python3 k-core.py

# Enregistrer un fait important
python3 k-core.py --remember "Ma décision importante"

# Chercher dans la mémoire
python3 k-core.py --recall "sujet à retrouver"

# Voir les décisions enregistrées
cat k-memory/brain/decisions.md
```

## Architecture

```
k-memory/
├── install.sh        # Auto-installateur
├── k-detector.py     # Détecteur d'environnement
├── k-core.py         # Moteur de mémoire principal
├── brain/            # Fichiers de mémoire (lobes)
│   ├── decisions.md
│   ├── directives.md
│   ├── evolution.md
│   └── system-identity.md
├── graph.json        # Graphe de connaissances
└── index.md          # Table des matières
```

## Ce qu'il détecte automatiquement

- **OS**: Linux, Mac, Windows (WSL)
- **LLM Providers**: OpenAI, Anthropic, DeepSeek, OpenRouter, Ollama
- **Agents**: Hermes, Claude Code, Codex
- **API Keys**: dans .env, config.yaml, variables d'environnement
- **GPU**: NVIDIA (nvidia-smi)
- **Stockage**: espace disque disponible
- **Mémoire existante**: intègre les fichiers déjà présents
- **Cron**: maintenance automatique toutes les 6h

## Dépendances

- Python 3.8+
- Bash
- Aucune bibliothèque externe

100% local. 100% gratuit. Rien n'est oublié.
