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
