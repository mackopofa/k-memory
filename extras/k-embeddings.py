#!/usr/bin/env python3
"""K-Memory Embeddings v1.0 — Recherche sémantique par vecteurs
Extension de k-core.py. Ajoute la recherche vectorielle sans toucher au core.

Backends:
  ollama   — gratuit, local (nomic-embed-text via Ollama)
  keywords — fallback, zéro dépendance externe

Usage:
  python3 k-embeddings.py --remember "Le chat dort" --domain maison
  python3 k-embeddings.py --recall "animal endormi"   # trouve "chat"!
  python3 k-embeddings.py --auto-summarize
"""
import sys, os, json, math
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BACKEND = "ollama"       # Ollama = gratuit, local
OLLAMA_MODEL = "nomic-embed-text"
SIMILARITY_THRESHOLD = 0.55
OLLAMA_URL = "http://localhost:11434"

# ── Persistance du choix backend ──────────────

def _backend_file(base_dir):
    return os.path.join(base_dir, ".backend")

def _save_backend(base_dir, backend):
    with open(_backend_file(base_dir), "w") as f:
        f.write(backend)

def _load_backend(base_dir):
    bf = _backend_file(base_dir)
    if os.path.exists(bf):
        return open(bf).read().strip()
    return None

# ── Détection backend ─────────────────────────

def _detect_backend(base_dir):
    # 1. Préférence sauvegardée
    saved = _load_backend(base_dir)
    if saved:
        return saved
    
    # 2. Ollama dispo ?
    try:
        import requests
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            if OLLAMA_MODEL in models:
                return "ollama"
    except:
        pass
    
    return "keywords"

# ── Embeddings ────────────────────────────────

def _embed_ollama(text):
    try:
        import requests
        resp = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": OLLAMA_MODEL, "prompt": text},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()["embedding"]
    except Exception as e:
        pass
    return None

# ── Cosine similarity ─────────────────────────

def _cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

# ── Core ──────────────────────────────────────

class KEmbeddings:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.join(os.path.expanduser("~"), ".hermes", "k-memory")
        
        # Import k-core.py (tiret interdit en Python)
        import importlib.util
        core_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "k-core.py")
        if not os.path.exists(core_path):
            core_path = os.path.join(self.base_dir, "k-core.py")
        spec = importlib.util.spec_from_file_location("kcore", core_path)
        kc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kc)
        
        self.core = kc.KMemoryCore(base_dir=self.base_dir)
        self.core.initialize()
        self.embeddings_file = os.path.join(self.base_dir, "embeddings.json")
        self._load_embeddings()
        self.backend = _detect_backend(self.base_dir)
    
    def _load_embeddings(self):
        self.embeddings = {}
        if os.path.exists(self.embeddings_file):
            with open(self.embeddings_file) as f:
                self.embeddings = json.load(f)
    
    def _save_embeddings(self):
        with open(self.embeddings_file, "w") as f:
            json.dump(self.embeddings, f)
    
    def set_backend(self, backend):
        if backend in ("ollama", "keywords"):
            self.backend = backend
            _save_backend(self.base_dir, backend)
            return True
        return False
    
    def remember(self, fact, domain="general", importance=0.5):
        nid = self.core.remember(fact, domain, importance)
        
        if self.backend == "ollama":
            emb = _embed_ollama(fact)
            if emb:
                self.embeddings[nid] = emb
                self._save_embeddings()
                return nid, "embedded"
            return nid, "stored (embed failed)"
        
        return nid, "stored (no backend)"
    
    def recall_semantic(self, query, limit=5):
        if self.backend == "keywords" or not self.embeddings:
            kw = self.core.recall(query, limit)
            for r in kw:
                r["match_type"] = "keyword"
            return kw
        
        query_emb = _embed_ollama(query)
        if not query_emb:
            kw = self.core.recall(query, limit)
            for r in kw:
                r["match_type"] = "keyword (embed failed)"
            return kw
        
        scores = []
        for nid, emb in self.embeddings.items():
            if nid in self.core.nodes:
                sim = _cosine_similarity(query_emb, emb)
                if sim >= SIMILARITY_THRESHOLD:
                    node = self.core.nodes[nid]
                    combined = sim * 0.6
                    combined += node.get("weight", 0.5) * 0.25
                    combined += self.core._recency_score(node.get("created", "")) * 0.15
                    scores.append((nid, combined, sim, node))
        
        scores.sort(key=lambda x: -x[1])
        results = []
        for nid, combined, sim, node in scores[:limit]:
            results.append({
                "label": node["label"],
                "domain": node["domain"],
                "confidence": round(combined, 3),
                "semantic_similarity": round(sim, 3),
                "preview": node.get("content", "")[:150],
                "created": node.get("created", "")[:10] if node.get("created") else "?",
                "match_type": "semantic"
            })
        
        if not results:
            kw = self.core.recall(query, limit)
            for r in kw:
                r["match_type"] = "keyword (fallback)"
            return kw
        
        return results
    
    def auto_summarize(self):
        if not self.embeddings or len(self.embeddings) < 5:
            print(f"Pas assez d'embeddings ({len(self.embeddings)}). Min 5 requis.")
            return
        
        nids = list(self.embeddings.keys())
        visited = set()
        clusters = []
        
        for i, nid1 in enumerate(nids):
            if nid1 in visited or nid1 not in self.core.nodes:
                continue
            cluster = [nid1]
            visited.add(nid1)
            for nid2 in nids[i+1:]:
                if nid2 in visited or nid2 not in self.core.nodes:
                    continue
                sim = _cosine_similarity(self.embeddings[nid1], self.embeddings[nid2])
                if sim > 0.7:
                    cluster.append(nid2)
                    visited.add(nid2)
            if len(cluster) >= 2:
                clusters.append(cluster)
        
        now = datetime.now(timezone.utc).isoformat()[:19].replace("T", " ")
        print(f"# 🧬 Clusters Sémantiques — {now}")
        print(f"# {len(clusters)} clusters sur {len(self.embeddings)} faits\n")
        
        for i, cluster in enumerate(clusters[:10]):
            labels = [self.core.nodes[nid]["label"][:60] for nid in cluster if nid in self.core.nodes]
            domains = set(self.core.nodes[nid]["domain"] for nid in cluster if nid in self.core.nodes)
            print(f"## Cluster {i+1} — {len(cluster)} faits — {', '.join(domains)}")
            for label in labels[:5]:
                print(f"  • {label}")
            if len(labels) > 5:
                print(f"  … et {len(labels) - 5} autres")
            print()
    
    def stats(self):
        s = self.core.stats()
        s["backend"] = self.backend
        s["embeddings_count"] = len(self.embeddings)
        return s

# ── CLI ───────────────────────────────────────

if __name__ == "__main__":
    km = KEmbeddings()
    
    if len(sys.argv) > 2 and sys.argv[1] == "--remember":
        # Parse args
        args = sys.argv[2:]
        domain = "general"
        importance = 0.5
        backend = None
        cleaned = []
        skip = False
        for i, a in enumerate(args):
            if skip:
                skip = False; continue
            if a == "--domain" and i + 1 < len(args):
                domain = args[i + 1]; skip = True
            elif a == "--importance" and i + 1 < len(args):
                try: importance = float(args[i + 1])
                except: pass
                skip = True
            elif a == "--backend" and i + 1 < len(args):
                backend = args[i + 1]; skip = True
            else:
                cleaned.append(a)
        fact = " ".join(cleaned)
        
        if backend:
            km.set_backend(backend)
        
        _, status = km.remember(fact, domain, importance)
        km.core.save()
        dim = len(list(km.embeddings.values())[0]) if km.embeddings else 0
        print(f"✓ [{status}] backend={km.backend} dim={dim or 'N/A'}")
        print(f"  Total embeddings: {len(km.embeddings)}")
    
    elif len(sys.argv) > 2 and sys.argv[1] == "--recall":
        query = " ".join(sys.argv[2:])
        results = km.recall_semantic(query)
        if results:
            for r in results:
                icon = "🧬" if r.get("match_type") == "semantic" else "🔤"
                sim = f" sim={r['semantic_similarity']}" if "semantic_similarity" in r else ""
                print(f"  {icon} {r['label'][:60]} [{r['domain']}]{sim}")
                print(f"    ↳ {r.get('preview', '')[:120]}")
        else:
            print("  (aucun résultat)")
    
    elif len(sys.argv) > 1 and sys.argv[1] == "--auto-summarize":
        km.auto_summarize()
    
    elif len(sys.argv) > 2 and sys.argv[1] == "--backend":
        if km.set_backend(sys.argv[2]):
            print(f"✓ Backend: {sys.argv[2]} (sauvegardé)")
        else:
            print(f"Backends: ollama, keywords")
    
    else:
        s = km.stats()
        print(f"✓ K-Memory Embeddings v1.0")
        print(f"  Core:    {s['nodes']} nœuds, {s['edges']} arêtes")
        print(f"  Vectors: {s['embeddings_count']} embeddings")
        print(f"  Backend: {s['backend']}")
        if s['embeddings_count'] > 0:
            emb = list(km.embeddings.values())[0]
            print(f"  Dim:     {len(emb)}")
        print(f"\n  --remember 'fait' [--domain X] [--backend ollama]")
        print(f"  --recall 'concept sémantique'")
        print(f"  --auto-summarize")
        print(f"  --backend ollama|keywords")
