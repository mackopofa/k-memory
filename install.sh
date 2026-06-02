#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# K-Memory — Auto-Install & Bootstrap
# Détecte, installe et intègre la mémoire persistante
# dans TOUT environnement LLM/IA.
# Usage : curl -sL https://.../install.sh | bash
#         ou bash install.sh
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

KYELLOW='\033[1;33m'
KGREEN='\033[1;32m'
KBLUE='\033[1;34m'
KRED='\033[1;31m'
KWHITE='\033[1;37m'
KRESET='\033[0m'

log() { echo -e "${KBLUE}[K-Memory]${KRESET} $1"; }
ok()  { echo -e "${KGREEN}[✓]${KRESET} $1"; }
warn(){ echo -e "${KYELLOW}[!]${KRESET} $1"; }
err() { echo -e "${KRED}[✗]${KRESET} $1"; }

echo ""
echo -e "${KWHITE}╔══════════════════════════════════════════╗${KRESET}"
echo -e "${KWHITE}║       K-Memory — Auto-Install v1.0       ║${KRESET}"
echo -e "${KWHITE}║    Clé de Mémoire du Kensai System       ║${KRESET}"
echo -e "${KWHITE}╚══════════════════════════════════════════╝${KRESET}"
echo ""

# ──────────────────────────────────────────────
# PHASE 1 : DÉTECTION DE L'ENVIRONNEMENT
# ──────────────────────────────────────────────
log "PHASE 1 : Détection de l'environnement..."

# OS
OS="$(uname -s)"
ARCH="$(uname -m)"
DISTRO=""
if [ -f /etc/os-release ]; then
    DISTRO=$(grep "^NAME=" /etc/os-release | cut -d'"' -f2)
fi
ok "OS: $OS $ARCH ($DISTRO)"

# Python
if command -v python3 &>/dev/null; then
    PYVER=$(python3 --version 2>&1)
    ok "Python: $PYVER"
else
    err "Python3 requis. Installation..."
    if command -v apt &>/dev/null; then
        apt update -qq && apt install -y -qq python3 python3-pip
    elif command -v yum &>/dev/null; then
        yum install -y python3 python3-pip
    else
        err "Impossible d'installer Python. Installez-le manuellement."
        exit 1
    fi
    ok "Python installé"
fi

# ──────────────────────────────────────────────
# PHASE 2 : DÉTECTION DES IA/LLM/AGENTS
# ──────────────────────────────────────────────
log "PHASE 2 : Détection des IA/LLM/Agents..."

# Hermes Agent
if command -v hermes &>/dev/null; then
    HERMES_VER=$(hermes --version 2>&1 | head -1)
    ok "Hermes Agent: $HERMES_VER"
    HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
    if [ -d "$HERMES_HOME" ]; then
        ok "Hermes home: $HERMES_HOME"
        # Injecter K-Memory dans le système Hermes
        if [ -f "$HERMES_HOME/config.yaml" ]; then
            warn "Configuration Hermes détectée — K-Memory s'intégrera"
        fi
    fi
else
    warn "Hermes Agent non détecté — installation autonome"
fi

# Claude / Codex
for cmd in claude codex copilot; do
    if command -v "$cmd" &>/dev/null; then
        ok "Agent détecté: $cmd"
    fi
done

# Provider LLM
API_COUNT=0
for key in OPENAI_API_KEY ANTHROPIC_API_KEY DEEPSEEK_API_KEY OPENROUTER_API_KEY GROQ_API_KEY; do
    if [ -n "${!key:-}" ]; then
        ok "Provider LLM: ${key%_API_KEY}"
        API_COUNT=$((API_COUNT + 1))
    fi
done

# Chercher les clés dans les fichiers .env
for env_file in "$HOME/.env" "$HOME/.hermes/.env" ".env"; do
    if [ -f "$env_file" ]; then
        ok "Fichier .env: $env_file"
        # Chercher les clés dedans
        while IFS='=' read -r key value; do
            case "$key" in
                OPENAI_API_KEY|ANTHROPIC_API_KEY|DEEPSEEK_API_KEY|OPENROUTER_API_KEY)
                    API_COUNT=$((API_COUNT + 1))
                    ;;
            esac
        done < <(grep -E '^(OPENAI|ANTHROPIC|DEEPSEEK|OPENROUTER)_API_KEY=' "$env_file" 2>/dev/null || true)
        break
    fi
done

# Ollama local
if command -v ollama &>/dev/null; then
    ok "Ollama détecté (LLM local)"
fi

# GPU
if command -v nvidia-smi &>/dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    ok "GPU NVIDIA: $GPU_INFO"
fi

# Cron/Scheduler
if [ -n "${CRON:-}" ] || [ -n "${HERMES_CRON:-}" ] || [ -n "${RUN_ID:-}" ]; then
    ok "Environnement cron détecté"
fi

# ──────────────────────────────────────────────
# PHASE 3 : INSTALLATION DE K-MEMORY
# ──────────────────────────────────────────────
log "PHASE 3 : Installation de K-Memory..."

# Déterminer le répertoire d'installation
if [ -d "$HOME/.hermes" ]; then
    KMBASE="$HOME/.hermes/k-memory"
elif [ -d "$HOME/.config" ]; then
    KMBASE="$HOME/.config/k-memory"
else
    KMBASE="$HOME/k-memory"
fi

# Pas d'écrasement si déjà installé
if [ -d "$KMBASE" ] && [ -f "$KMBASE/k-core.py" ]; then
    warn "K-Memory déjà installé dans $KMBASE"
    log "Mise à jour en cours..."
else
    mkdir -p "$KMBASE"
    ok "Répertoire créé: $KMBASE"
fi

# Télécharger/copier les fichiers sources
INSTALL_SRC="${BASH_SOURCE[0]%/*}"

# Si on est dans le répertoire source, copier localement
if [ -f "$INSTALL_SRC/k-detector.py" ] && [ -f "$INSTALL_SRC/k-core.py" ]; then
    cp "$INSTALL_SRC/k-detector.py" "$KMBASE/k-detector.py" 2>/dev/null || true
    cp "$INSTALL_SRC/k-core.py" "$KMBASE/k-core.py" 2>/dev/null || true
    ok "Fichiers copiés depuis $INSTALL_SRC"
else
    # Sinon créer les fichiers depuis l'installateur embedded
    warn "Mode installation autonome — création des fichiers..."
    
    # Créer k-detector.py (version légère inline)
    cat > "$KMBASE/k-detector.py" << 'PYEOF'
#!/usr/bin/env python3
"""K-Memory Detector — Version autonome"""
import os, sys, json, subprocess, platform, shutil, re
from datetime import datetime, timezone

class KDetector:
    def __init__(self):
        self.env = {"timestamp": datetime.now(timezone.utc).isoformat(),"os":{},"llm":{},"agent":{},"tools":{},"storage":{},"host":{}}
    def detect_all(self):
        self.env["os"] = {"system":platform.system(),"release":platform.release(),"machine":platform.machine()}
        self.env["host"] = {"cpu_cores": os.cpu_count()}
        try:
            if os.name == 'posix':
                s = os.statvfs('/')
                self.env["storage"] = {"free_gb": round(s.f_frsize*s.f_bavail/(1024**3),1)}
        except: pass
        providers = {}
        for key, name in [("OPENAI_API_KEY","openai"),("ANTHROPIC_API_KEY","anthropic"),("DEEPSEEK_API_KEY","deepseek")]:
            if os.environ.get(key): providers[name] = {"detected":True}
        for env_file in [os.path.expanduser("~/.env"),os.path.expanduser("~/.hermes/.env"),".env"]:
            if os.path.exists(env_file):
                with open(env_file) as f: content = f.read()
                for key, name in [("OPENAI_API_KEY","openai"),("ANTHROPIC_API_KEY","anthropic"),("DEEPSEEK_API_KEY","deepseek")]:
                    if key in content and name not in providers: providers[name] = {"detected":True,"from_file":env_file}
        self.env["llm"]["providers"] = providers
        self.env["llm"]["count"] = len(providers)
        if shutil.which("ollama"): self.env["llm"]["ollama_local"] = True
        if shutil.which("nvidia-smi"):
            try: self.env["gpu"] = subprocess.run(["nvidia-smi","--query-gpu=name","--format=csv,noheader"],capture_output=True,text=True,timeout=5).stdout.strip()[:100]
            except: pass
        return self.env

if __name__ == "__main__":
    d = KDetector()
    env = d.detect_all()
    with open("k-memory-env.json","w") as f: json.dump(env,f,indent=2)
    print(f"Environnement: {env['os']['system']} | Providers: {env['llm']['count']} | Libre: {env.get('storage',{}).get('free_gb','?')} Go")
PYEOF
    ok "k-detector.py créé"
    
    # Créer k-core.py (version autonome)
    cat > "$KMBASE/k-core.py" << 'PYEOF'
#!/usr/bin/env python3
"""K-Memory Core — Version autonome installable"""
import json, os, hashlib, glob, re, sys
from datetime import datetime, timezone
from collections import defaultdict

class KMemoryCore:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.join(os.path.expanduser("~"),"k-memory")
        self.brain_dir = os.path.join(self.base_dir,"brain")
        self.graph_file = os.path.join(self.base_dir,"graph.json")
        self.index_file = os.path.join(self.base_dir,"index.md")
        self.nodes = {}; self.edges = []
        self.inverted_index = defaultdict(list)
        self.domain_index = defaultdict(list)
    
    def initialize(self):
        os.makedirs(self.brain_dir, exist_ok=True)
        self._load_graph()
        if not self.nodes:
            now = datetime.now(timezone.utc).isoformat()
            for nid, data in {"system-identity":{"label":"Identité","content":f"K-Memory initialisé {now}","domain":"system"},
                              "directives":{"label":"Directives","content":"1. Ne jamais supprimer sans validation\n2. Protéger le système\n3. Accumuler la connaissance","domain":"rules"},
                              "decisions":{"label":"Décisions","content":"Créé le "+now,"domain":"decisions"},
                              "evolution":{"label":"Évolution","content":now+" | Création","domain":"system"}}.items():
                self._add_node("lobe",data["label"],data["content"],weight=1.0,domain=data["domain"])
                fp = os.path.join(self.brain_dir,f"{nid}.md")
                if not os.path.exists(fp):
                    with open(fp,"w") as f: f.write(f"# {data['label']}\n\n{data['content']}\n")
        self._scan_existing()
        return self
    
    def _load_graph(self):
        if os.path.exists(self.graph_file):
            with open(self.graph_file) as f: d = json.load(f)
            self.nodes = d.get("nodes",{}); self.edges = d.get("edges",[])
            self.inverted_index = defaultdict(list,d.get("inverted_index",{}))
            self.domain_index = defaultdict(list,d.get("domain_index",{}))
    
    def _scan_existing(self):
        for fp in glob.glob(os.path.join(self.brain_dir,"*.md")):
            if os.path.basename(fp)=="index.md": continue
            with open(fp) as f: c = f.read()
            nid = hashlib.sha256(c.encode()).hexdigest()[:16]
            if nid not in self.nodes:
                self._add_node("lobe",os.path.basename(fp).replace(".md",""),c[:2000],weight=0.8,domain="general")
    
    def _hash(self,c): return hashlib.sha256(c.encode()).hexdigest()[:16]
    def _now(self): return datetime.now(timezone.utc).isoformat()
    
    def _add_node(self,nt,label,content="",source="auto",weight=0.5,tags=None,domain="general"):
        nid = self._hash(f"{nt}:{label}:{content[:200]}")
        if nid in self.nodes: return nid
        self.nodes[nid] = {"id":nid,"type":nt,"label":label,"content":content[:2000],"source":source,
                           "weight":weight,"created":self._now(),"last_accessed":self._now(),"access_count":1,
                           "tags":tags or [],"domain":domain}
        self.domain_index[domain].append(nid)
        return nid
    
    def remember(self, fact, domain="general", importance=0.5):
        nid = self._add_node("fact",fact[:100],f"[{self._now()}] {fact}",weight=importance,tags=[domain],domain=domain)
        df = os.path.join(self.brain_dir,"decisions.md")
        with open(df,"a") as f: f.write(f"\n[{self._now()[:10]}] {fact}")
        return nid
    
    def recall(self, query, limit=5):
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        scores = defaultdict(float)
        for w in words:
            for nid in [n for n in self.nodes if w in self.nodes[n].get("content","").lower()]:
                scores[nid] += self.nodes[nid].get("weight",0.5)
        results = []
        for nid, sc in sorted(scores.items(),key=lambda x:-x[1])[:limit]:
            n = self.nodes[nid]; results.append({"label":n["label"],"domain":n["domain"],"confidence":round(sc,3)})
        return results
    
    def stats(self):
        return {"nodes":len(self.nodes),"edges":len(self.edges),"domains":len(self.domain_index),"brain_dir":self.brain_dir}
    
    def save(self):
        data = {"nodes":self.nodes,"edges":self.edges,"inverted_index":dict(self.inverted_index),
                "domain_index":dict(self.domain_index),"updated_at":self._now()}
        with open(self.graph_file,"w") as f: json.dump(data,f,indent=2)
        idx_lines = [f"# K-Memory Index\nMis à jour: {self._now()[:10]}\nNoeuds: {len(self.nodes)}\n"]
        for d in sorted(self.domain_index): idx_lines.append(f"- {d}: {len(self.domain_index[d])}")
        idx_lines.append("")
        with open(self.index_file,"w") as f: f.write("\n".join(idx_lines))

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--remember" and len(sys.argv) > 2:
        KMemoryCore().initialize().remember(" ".join(sys.argv[2:]))
        print("✓ Fait enregistré")
    elif len(sys.argv) > 1 and sys.argv[1] == "--recall" and len(sys.argv) > 2:
        r = KMemoryCore().initialize().recall(" ".join(sys.argv[2:]))
        for item in r: print(f"  • {item['label']} [{item['domain']}] confiance: {item['confidence']}")
    else:
        core = KMemoryCore().initialize()
        core.save()
        s = core.stats()
        print(f"✓ K-Memory initialisé: {s['nodes']} noeuds, {s['edges']} arêtes, {s['domains']} domaines")
        print(f"  Base: {s['brain_dir']}")
PYEOF
    ok "k-core.py créé"
fi

chmod +x "$KMBASE/k-detector.py" "$KMBASE/k-core.py"

# ──────────────────────────────────────────────
# PHASE 4 : DÉTECTION DE LA MÉMOIRE EXISTANTE
# ──────────────────────────────────────────────
log "PHASE 4 : Détection et intégration de la mémoire existante..."

INTEGRATED=0

# Chercher la mémoire Kensai existante
for dir in "$HOME/.hermes/memories/brain" "$HOME/k-memory/brain" "$HOME/.hermes/brain"; do
    if [ -d "$dir" ]; then
        COUNT=$(find "$dir" -name "*.md" 2>/dev/null | wc -l)
        if [ "$COUNT" -gt 0 ]; then
            warn "Mémoire existante: $dir ($COUNT fichiers)"
            # Copier vers K-Memory (sans écraser)
            cp -rn "$dir"/*.md "$KMBASE/brain/" 2>/dev/null || true
            INTEGRATED=$((INTEGRATED + COUNT))
            ok "$COUNT fichiers intégrés depuis $dir"
        fi
    fi
done

# Vérifier si on tourne dans un agent Hermes
if [ -n "${HERMES_HOME:-}" ] || [ -d "$HOME/.hermes" ]; then
    HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
    
    # Intégration avec le prompt Hermes
    INJECT_FILE="$HERMES_HOME/k-memory-inject.md"
    cat > "$INJECT_FILE" << INJEOF
# K-Memory Injection — Chargé automatiquement
Ce fichier est lu par l'IA pour accéder à la mémoire persistante.
Source: K-Memory Auto-Install
Date: $(date -I)

## Mémoire disponible
- Base: $KMBASE
- Fichiers brain: $(ls "$KMBASE/brain/"*.md 2>/dev/null | wc -l) fichiers
- Graphe: $KMBASE/graph.json

## Usage
Pour accéder à la mémoire : python3 $KMBASE/k-core.py --recall "ma requête"
Pour enregistrer : python3 $KMBASE/k-core.py --remember "mon fait important"
INJEOF
    ok "Fichier d'injection créé: $INJECT_FILE"
fi

# ──────────────────────────────────────────────
# PHASE 5 : INITIALISATION ET TEST
# ──────────────────────────────────────────────
log "PHASE 5 : Initialisation et test..."

cd "$KMBASE"
python3 k-detector.py 2>&1 | tail -3
python3 k-core.py 2>&1 | tail -3

# Test d'enregistrement
python3 k-core.py --remember "K-Memory installé le $(date -I)"
python3 k-core.py --remember "Système: $OS $DISTRO"
python3 k-core.py --remember "$API_COUNT providers LLM détectés"

ok "K-Memory fonctionnel — tests réussis"

# ──────────────────────────────────────────────
# PHASE 6 : CRON DE MAINTENANCE (optionnel)
# ──────────────────────────────────────────────
log "PHASE 6 : Mise en place de la maintenance..."

CRON_JOB="0 */6 * * * cd $KMBASE && python3 k-core.py >/dev/null 2>&1"
if crontab -l 2>/dev/null | grep -q "k-memory"; then
    warn "Cron K-Memory déjà présent"
else
    (crontab -l 2>/dev/null || true; echo "$CRON_JOB") | crontab -
    ok "Cron ajouté: toutes les 6h"
fi

# ──────────────────────────────────────────────
# RAPPORT FINAL
# ──────────────────────────────────────────────
echo ""
echo -e "${KWHITE}╔══════════════════════════════════════════╗${KRESET}"
echo -e "${KWHITE}║    K-Memory — Installation Terminée !    ║${KRESET}"
echo -e "${KWHITE}╚══════════════════════════════════════════╝${KRESET}"
echo ""
echo -e "  ${KBLUE}📍${KRESET} Base:      $KMBASE"
echo -e "  ${KBLUE}🧠${KRESET} Moteur:    k-core.py"
echo -e "  ${KBLUE}🔍${KRESET} Détecteur: k-detector.py"
echo -e "  ${KBLUE}📂${KRESET} Mémoire:   $(ls "$KMBASE/brain/"*.md 2>/dev/null | wc -l) fichiers"
echo -e "  ${KBLUE}📊${KRESET} Graphe:    graph.json"
echo -e "  ${KBLUE}🔗${KRESET} Fournisseurs LLM: $API_COUNT"
echo -e "  ${KBLUE}⏰${KRESET} Maintenance: cron toutes les 6h"
echo ""
echo -e "  ${KGREEN}Commandes :${KRESET}"
echo "    python3 $KMBASE/k-core.py                   → Statut"
echo "    python3 $KMBASE/k-core.py --remember 'fait' → Enregistrer"
echo "    python3 $KMBASE/k-core.py --recall 'sujet'  → Chercher"
echo "    cat $KMBASE/brain/decisions.md               → Décisions"
echo ""

# Nettoyage
rm -f "$KMBASE/k-memory-env.json" 2>/dev/null

echo -e "${KGREEN}K-Memory opérationnel. Rien ne sera oublié.${KRESET}"
