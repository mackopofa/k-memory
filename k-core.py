#!/usr/bin/env python3
"""K-Memory Core v1.1 — avec déduplication, horodatage, liaison sémantique"""
import json, os, hashlib, glob, re, sys, difflib
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
    def _extract_keywords(self, text):
        words = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', text.lower())
        stop = {"the","and","for","are","but","not","you","all","can","had","her","was","one",
                "our","out","has","have","been","some","same","also","its","than","them","they",
                "this","that","with","from","their","which","what","when","where","how","who",
                "dans","avec","pour","sur","pas","les","des","est","que","une","nous","vous",
                "elle","ils","ont","sont","fait","mais","elus"}
        return [w for w in words if w not in stop]
    
    def _add_node(self, nt, label, content="", source="auto", weight=0.5, tags=None, domain="general"):
        nid = self._hash(f"{nt}:{label}:{content[:200]}")
        now = self._now()
        if nid in self.nodes:
            self.nodes[nid]["access_count"] += 1
            self.nodes[nid]["last_accessed"] = now
            if weight > self.nodes[nid].get("weight",0):
                self.nodes[nid]["weight"] = weight
            return nid
        self.nodes[nid] = {"id":nid,"type":nt,"label":label,"content":content[:3000],"source":source,
                           "weight":weight,"created":now,"last_accessed":now,"access_count":1,
                           "tags":tags or [],"domain":domain}
        self.domain_index[domain].append(nid)
        # Indexer les mots-clés
        for w in self._extract_keywords(label + " " + content[:500]):
            if nid not in self.inverted_index[w]:
                self.inverted_index[w].append(nid)
        return nid
    
    def _add_edge(self, src, dst, relation="related", weight=0.5):
        if src in self.nodes and dst in self.nodes:
            self.edges.append({"source_id":src,"target_id":dst,"relation":relation,
                               "weight":weight,"created":self._now()})
    
    def _find_similar_facts(self, text, threshold=0.5):
        """Déduplication intelligente : Jaccard + ratio de séquence"""
        query_words = set(self._extract_keywords(text))
        if not query_words:
            return []
        scores = []
        for nid, node in self.nodes.items():
            if node.get("type") == "fact":
                node_content = node.get("content","")
                node_words = set(self._extract_keywords(node_content))
                if query_words and node_words:
                    jaccard = len(query_words & node_words) / len(query_words | node_words)
                    # Similarité de séquence (rattrape les synonymes implicites)
                    seq_ratio = difflib.SequenceMatcher(None, text.lower()[:100], node_content.lower()[:100]).ratio()
                    combined = max(jaccard, seq_ratio)
                    if combined >= threshold:
                        scores.append((nid, combined, node))
        return sorted(scores, key=lambda x: -x[1])[:3]
    
    def remember(self, fact, domain="general", importance=0.5):
        now = self._now()
        timestamp = now[:19].replace("T"," ")
        
        # 1. Déduplication : chercher si un fait similaire existe déjà
        similar = self._find_similar_facts(fact)
        if similar:
            nid, score, node = similar[0]
            # Fusionner : enrichir le contenu sans dupliquer
            existing = node.get("content","")
            if fact not in existing and len(existing) < 2000:
                node["content"] = existing + f"\n[{timestamp}] {fact}"
                node["access_count"] += 1
                node["last_accessed"] = now
                self.nodes[nid] = node
                self._index_node(nid, fact)
                # Noter la fusion dans les edges
                for sim_nid, _, _ in similar[1:]:
                    self._add_edge(nid, sim_nid, "merge", 0.3)
                return nid
        
        # 2. Nouveau fait
        nid = self._add_node("fact", fact[:80], f"[{timestamp}] {fact}", 
                            weight=importance, tags=[domain, "fact"], domain=domain)
        
        # 3. Horodatage systématique dans decisions.md
        df = os.path.join(self.brain_dir,"decisions.md")
        with open(df,"a") as f: 
            f.write(f"\n[{timestamp}] [{domain}] {fact}")
        
        # 4. Liaison automatique avec les faits existants du même domaine
        for other_nid, other in self.nodes.items():
            if other_nid != nid and other.get("domain") == domain and other.get("type") == "fact":
                self._add_edge(nid, other_nid, "related", 0.4)
                break  # juste un lien, pas tous
        
        # 5. Lien avec les mots-clés communs dans le graphe
        keywords = self._extract_keywords(fact)
        for kw in keywords[:5]:  # max 5 liens
            for other_nid in self.inverted_index.get(kw, []):
                if other_nid != nid:
                    self._add_edge(nid, other_nid, "keyword", 0.3)
                    break
        
        return nid
    
    def _index_node(self, nid, text):
        """Indexe un texte pour un noeud existant"""
        for w in self._extract_keywords(text):
            if nid not in self.inverted_index[w]:
                self.inverted_index[w].append(nid)
    
    def recall(self, query, limit=5):
        words = self._extract_keywords(query)
        scores = defaultdict(float)
        for w in words:
            for nid in self.inverted_index.get(w, []):
                node = self.nodes.get(nid)
                if node:
                    scores[nid] += node.get("weight",0.5) * (1 + node.get("access_count",0) * 0.02)
        # Bonus si plusieurs mots matchent le même noeud
        for nid in scores:
            count = sum(1 for w in words if nid in self.inverted_index.get(w,[]))
            scores[nid] *= (1 + count * 0.2)
        results = []
        for nid, sc in sorted(scores.items(), key=lambda x:-x[1])[:limit]:
            n = self.nodes[nid]
            content_preview = n.get("content","")[:150]
            results.append({"label":n["label"],"domain":n["domain"],
                           "confidence":round(sc,3),"preview":content_preview,
                           "accessed":n.get("access_count",0)})
            # Marquer comme consulté
            self.nodes[nid]["access_count"] += 1
            self.nodes[nid]["last_accessed"] = self._now()
        return results
    
    def stats(self):
        return {"nodes":len(self.nodes),"edges":len(self.edges),
                "domains":len(self.domain_index),"brain_dir":self.brain_dir,
                "terms":len(self.inverted_index)}
    
    def save(self):
        data = {"nodes":self.nodes,"edges":self.edges,
                "inverted_index":dict(self.inverted_index),
                "domain_index":dict(self.domain_index),
                "updated_at":self._now(),
                "stats":{"total_nodes":len(self.nodes),"total_edges":len(self.edges),
                         "total_domains":len(self.domain_index),
                         "total_indexed_terms":len(self.inverted_index)}}
        with open(self.graph_file,"w") as f: json.dump(data,f,indent=2)
        idx_lines = [f"# K-Memory Index\nMis à jour: {self._now()[:10]}\nNoeuds: {len(self.nodes)}\n"]
        for d in sorted(self.domain_index): idx_lines.append(f"- {d}: {len(self.domain_index[d])}")
        idx_lines.append("")
        with open(self.index_file,"w") as f: f.write("\n".join(idx_lines))

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--remember" and len(sys.argv) > 2:
        fact = " ".join(sys.argv[2:])
        # Support du format --remember "fait" --domain "sujet" --importance 0.8
        domain = "general"
        importance = 0.5
        if "--domain" in sys.argv:
            idx = sys.argv.index("--domain")
            if idx + 1 < len(sys.argv): domain = sys.argv[idx + 1]
        if "--importance" in sys.argv:
            idx = sys.argv.index("--importance")
            if idx + 1 < len(sys.argv):
                try: importance = float(sys.argv[idx + 1])
                except: pass
        core = KMemoryCore().initialize()
        core.remember(fact, domain, importance)
        core.save()
        print(f"✓ Fait enregistré [domaine: {domain}, importance: {importance}]")
    elif len(sys.argv) > 1 and sys.argv[1] == "--recall" and len(sys.argv) > 2:
        core = KMemoryCore().initialize()
        r = core.recall(" ".join(sys.argv[2:]))
        for item in r:
            print(f"  • {item['label']} [{item['domain']}] confiance: {item['confidence']}")
            if item.get('preview'):
                print(f"    ↳ {item['preview'][:120]}")
    else:
        core = KMemoryCore().initialize()
        core.save()
        s = core.stats()
        print(f"✓ K-Memory v1.1 initialisé: {s['nodes']} noeuds, {s['edges']} arêtes, {s['domains']} domaines, {s['terms']} termes")
        print(f"  Base: {s['brain_dir']}")
