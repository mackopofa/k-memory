# K-Memory ⚔️ v2.1

**Mémoire persistante, portable, zéro dépendance — par KensaiArt**

Un moteur mémoire autonome pour IA, LLMs et agents. Stocke, relie, résume et exporte la connaissance en pur Python (stdlib uniquement). Pas de vecteurs, pas de cloud, pas de contrainte.

## Installation

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mackopofa/k-memory/main/install.sh)
```

Ou directement :

```bash
git clone https://github.com/mackopofa/k-memory.git ~/k-memory
cd ~/k-memory && python3 k-core.py
```

## Utilisation

```bash
# Enregistrer un fait
python3 k-core.py --remember "Le recency boost pondère les faits récents" --domain "features"

# Rappeler des faits
python3 k-core.py --recall "recency boost"

# Résumer un domaine
python3 k-core.py --summary --domain "features"

# Résumer tous les domaines
python3 k-core.py --summarize-all

# Exporter en Markdown lisible
python3 k-core.py --export

# Exporter en diagramme Mermaid (Obsidian compatible)
python3 k-core.py --export --mermaid
```

## Tests

```bash
python3 tests/test_core.py    # 30 tests, 0 dépendance externe
```

## Commandes

| Commande | Effet |
|----------|-------|
| `--remember <texte>` | Enregistre un fait avec horodatage, domaine, importance |
| `--recall <query>` | Rappelle les faits pertinents (triés par pertinence × recency) |
| `--summary [--domain X]` | Résumé structuré d'un domaine |
| `--summarize-all` | Résumé de tous les domaines |
| `--export [--mermaid]` | Exporte le graphe en Markdown ou Mermaid |
| `--version` | Affiche la version |

## Architecture

```
~/k-memory/
├── k-core.py          # Moteur principal (v2.1)
├── k-detector.py      # Détecteur auto-environnement
├── install.sh         # Installation automatique
├── LICENSE            # MIT
├── tests/
│   └── test_core.py   # 30 tests, 0 dépendance
├── graph.json         # Graphe de connaissance (noeuds + arrêtes)
├── index.md           # Index lisible
├── brain/             # Fichiers .md individuels par lobe
├── summaries/         # Résumés automatiques par domaine
├── exports/           # Exports générés
└── knowledge/         # Connaissance détaillée (optionnel)
```

## Performances

- Zéro dépendance externe (Python stdlib uniquement)
- Portable : Ubuntu, Debian, Mac, WSL, Termux
- Graphe jusqu'à 10 000+ noeuds sans ralentissement
- Chaque opération < 100ms sur matériel normal

## Licence

MIT — Copyright (c) 2026 KensaiArt. Voir [LICENSE](LICENSE).

> "La mémoire n'est pas un stockage. C'est la conscience qui se souvient."
