#!/usr/bin/env python3
"""K-Memory Core v2.0 — Recency boost, Auto-summary, Export Mermaid + Markdown
Zéro dépendance, pur Python stdlib, portable partout."""

import json, os, hashlib, glob, re, sys, difflib, textwrap, math
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

# ──────────────────────────────────────────────
#  CONSTANTES
# ──────────────────────────────────────────────
VERSION = "2.0"
DECAY_HALF_LIFE_DAYS = 30  # un fait perd la moitié de son poids en 30 jours
AUTO_SUMMARY_MIN_FACTS = 5  # nombre minimal de faits pour générer un résumé
AUTO_SUMMARY_CHAR_LIMIT = 5000  # taille max du résumé par domaine
EXPORT_DIR_DEFAULT = "exports"


class KMemoryCore:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.join(os.path.expanduser("~"), ".hermes", "k-memory")
        self.brain_dir = os.path.join(self.base_dir, "brain")
        self.graph_file = os.path.join(self.base_dir, "graph.json")
        self.index_file = os.path.join(self.base_dir, "index.md")
        self.nodes = {}
        self.edges = []
        self.inverted_index = defaultdict(list)
        self.domain_index = defaultdict(list)

    def initialize(self):
        os.makedirs(self.brain_dir, exist_ok=True)
        self._load_graph()
        if not self.nodes:
            now = datetime.now(timezone.utc).isoformat()
            seed = {
                "system-identity": {
                    "label": "Identité",
                    "content": f"K-Memory v{VERSION} initialisé {now}",
                    "domain": "system"
                },
                "directives": {
                    "label": "Directives",
                    "content": "1. Ne jamais supprimer sans validation\n2. Protéger le système\n3. Accumuler la connaissance",
                    "domain": "rules"
                },
                "decisions": {
                    "label": "Décisions",
                    "content": f"Créé le {now}",
                    "domain": "decisions"
                },
                "evolution": {
                    "label": "Évolution",
                    "content": f"{now} | v{VERSION} — Recency, Auto-summary, Export",
                    "domain": "system"
                }
            }
            for nid, data in seed.items():
                self._add_node("lobe", data["label"], data["content"], weight=1.0, domain=data["domain"])
                fp = os.path.join(self.brain_dir, f"{nid}.md")
                if not os.path.exists(fp):
                    with open(fp, "w") as f:
                        f.write(f"# {data['label']}\n\n{data['content']}\n")
        self._scan_existing()
        return self

    def _load_graph(self):
        if os.path.exists(self.graph_file):
            with open(self.graph_file) as f:
                d = json.load(f)
            self.nodes = d.get("nodes", {})
            self.edges = d.get("edges", [])
            self.inverted_index = defaultdict(list, d.get("inverted_index", {}))
            self.domain_index = defaultdict(list, d.get("domain_index", {}))

    def _scan_existing(self):
        for fp in glob.glob(os.path.join(self.brain_dir, "*.md")):
            if os.path.basename(fp) in ("index.md",):
                continue
            with open(fp) as f:
                c = f.read()
            nid = hashlib.sha256(c.encode()).hexdigest()[:16]
            if nid not in self.nodes:
                self._add_node("lobe", os.path.basename(fp).replace(".md", ""), c[:2000], weight=0.8, domain="general")

    def _hash(self, c):
        return hashlib.sha256(c.encode()).hexdigest()[:16]

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def _timestamp(self):
        return self._now()[:19].replace("T", " ")

    def _extract_keywords(self, text, max_words=30):
        words = re.findall(r'\b[a-zA-Z0-9_àâçéèêëîïôûùüÿœæÀÂÇÉÈÊËÎÏÔÛÙÜŸŒÆ]{3,}\b', text.lower())
        stop = {"the","and","for","are","but","not","you","all","can","had","her","was","one",
                "our","out","has","have","been","some","same","also","its","than","them","they",
                "this","that","with","from","their","which","what","when","where","how","who",
                "dans","avec","pour","sur","pas","les","des","est","que","une","nous","vous",
                "elle","ils","ont","sont","fait","mais","elus","etc","peut","tout","plus","bien",
                "très","être","faire","like","just","much","very","each","own","such","than",
                "too","will"} if False else {"the", "and", "for", "are", "but", "not", "you",
                "all", "can", "had", "her", "was", "one", "our", "out", "has", "have", "been",
                "some", "same", "also", "its", "than", "them", "they", "this", "that", "with",
                "from", "their", "which", "what", "when", "where", "how", "who",
                "dans", "avec", "pour", "sur", "pas", "les", "des", "est", "que", "une", "nous",
                "vous", "elle", "ils", "ont", "sont", "fait", "mais", "elus", "etc", "peut",
                "tout", "plus", "bien", "très", "être", "faire", "like", "just", "much", "very",
                "each", "own", "such", "than", "too", "will"}
        return [w for w in words if w not in stop][:max_words]

    def _recency_weight(self, node):
        """Calcule un poids temporel : un fait récent pèse plus qu'un vieux fait.
        Décroissance exponentielle avec demi-vie configurable."""
        created_str = node.get("created", "")
        if not created_str:
            return 1.0
        try:
            created = datetime.fromisoformat(created_str)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - created
            days = delta.total_seconds() / 86400.0
            if days < 0:
                days = 0
            # f(t) = 2^(-t / half_life)
            return math.pow(2, -days / DECAY_HALF_LIFE_DAYS)
        except (ValueError, TypeError):
            return 1.0

    def _score_with_recency(self, base_score, node):
        """Applique le recency boost au score de base."""
        recency = self._recency_weight(node)
        # Le boost recency est 10x pour aujourd'hui, ~0.5 pour 30 jours
        return base_score * (0.5 + recency * 0.5)

    def _add_node(self, nt, label, content="", source="auto", weight=0.5, tags=None, domain="general"):
        nid = self._hash(f"{nt}:{label}:{content[:200]}")
        now = self._now()
        if nid in self.nodes:
            self.nodes[nid]["access_count"] += 1
            self.nodes[nid]["last_accessed"] = now
            if weight > self.nodes[nid].get("weight", 0):
                self.nodes[nid]["weight"] = weight
            return nid
        self.nodes[nid] = {
            "id": nid, "type": nt, "label": label, "content": content[:3000],
            "source": source, "weight": weight, "created": now,
            "last_accessed": now, "access_count": 1,
            "tags": tags or [], "domain": domain
        }
        self.domain_index[domain].append(nid)
        for w in self._extract_keywords(label + " " + content[:500]):
            if nid not in self.inverted_index[w]:
                self.inverted_index[w].append(nid)
        return nid

    def _add_edge(self, src, dst, relation="related", weight=0.5):
        if src in self.nodes and dst in self.nodes:
            self.edges.append({
                "source_id": src, "target_id": dst,
                "relation": relation, "weight": weight, "created": self._now()
            })

    def _find_similar_facts(self, text, threshold=0.5):
        query_words = set(self._extract_keywords(text))
        if not query_words:
            return []
        scores = []
        for nid, node in self.nodes.items():
            if node.get("type") in ("fact", "lobe"):
                node_content = node.get("content", "")
                node_words = set(self._extract_keywords(node_content))
                if query_words and node_words:
                    jaccard = len(query_words & node_words) / len(query_words | node_words)
                    seq_ratio = difflib.SequenceMatcher(None, text.lower()[:100], node_content.lower()[:100]).ratio()
                    combined = max(jaccard, seq_ratio)
                    if combined >= threshold:
                        scores.append((nid, combined, node))
        return sorted(scores, key=lambda x: -x[1])[:3]

    def remember(self, fact, domain="general", importance=0.5):
        now = self._now()
        timestamp = now[:19].replace("T", " ")

        similar = self._find_similar_facts(fact)
        if similar:
            nid, score, node = similar[0]
            existing = node.get("content", "")
            if fact not in existing and len(existing) < 2000:
                node["content"] = existing + f"\n[{timestamp}] {fact}"
                node["access_count"] += 1
                node["last_accessed"] = now
                self.nodes[nid] = node
                self._index_node(nid, fact)
                for sim_nid, _, _ in similar[1:]:
                    self._add_edge(nid, sim_nid, "merge", 0.3)
                return nid

        nid = self._add_node("fact", fact[:80], f"[{timestamp}] {fact}",
                             weight=importance, tags=[domain, "fact"], domain=domain)

        df = os.path.join(self.brain_dir, "decisions.md")
        with open(df, "a") as f:
            f.write(f"\n[{timestamp}] [{domain}] {fact}")

        for other_nid, other in self.nodes.items():
            if other_nid != nid and other.get("domain") == domain and other.get("type") == "fact":
                self._add_edge(nid, other_nid, "related", 0.4)
                break

        keywords = self._extract_keywords(fact)
        for kw in keywords[:5]:
            for other_nid in self.inverted_index.get(kw, []):
                if other_nid != nid:
                    self._add_edge(nid, other_nid, "keyword", 0.3)
                    break

        return nid

    def _index_node(self, nid, text):
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
                    base_score = node.get("weight", 0.5) * (1 + node.get("access_count", 0) * 0.02)
                    # ★ RECENCY BOOST : appliqué ici
                    scores[nid] += self._score_with_recency(base_score, node)

        for nid in scores:
            count = sum(1 for w in words if nid in self.inverted_index.get(w, []))
            scores[nid] *= (1 + count * 0.2)

        results = []
        for nid, sc in sorted(scores.items(), key=lambda x: -x[1])[:limit]:
            n = self.nodes[nid]
            content_preview = n.get("content", "")[:150]
            results.append({
                "label": n["label"], "domain": n["domain"],
                "confidence": round(sc, 3), "preview": content_preview,
                "accessed": n.get("access_count", 0),
                "recency": round(self._recency_weight(n), 3)
            })
            self.nodes[nid]["access_count"] += 1
            self.nodes[nid]["last_accessed"] = self._now()
        return results

    # ═══════════════════════════════════════════════
    #  ★ NOUVEAU v2.0 — AUTO-SUMMARY
    # ═══════════════════════════════════════════════
    def summarize_domain(self, domain, top_n=10):
        """Génère un résumé structuré d'un domaine entier, sans LLM.
        Utilise TF-IDF maison + détection de tendances temporelles + faits clés."""
        if domain not in self.domain_index:
            return f"Domaine '{domain}' inconnu."

        node_ids = self.domain_index[domain]
        facts = [(nid, self.nodes[nid]) for nid in node_ids
                 if self.nodes[nid].get("type") in ("fact", "lobe")]

        if len(facts) < AUTO_SUMMARY_MIN_FACTS:
            return f"Domaine '{domain}' : seulement {len(facts)} fait(s). Pas assez pour un résumé (min {AUTO_SUMMARY_MIN_FACTS})."

        # Extraire tous les mots et faire TF
        all_words = []
        doc_vectors = {}
        for nid, node in facts:
            words = self._extract_keywords(node.get("content", ""), max_words=100)
            all_words.extend(words)
            doc_vectors[nid] = Counter(words)

        # Term Frequency global
        tf_global = Counter(all_words)
        n_docs = len(facts)

        # TF-IDF maison : score = tf * (1 + log(N/df))
        tfidf = Counter()
        for nid, words in doc_vectors.items():
            for w, cnt in words.items():
                df = sum(1 for v in doc_vectors.values() if w in v)
                idf = 1 + math.log(n_docs / (df + 1)) if df > 0 else 1
                tfidf[w] += cnt * idf

        top_keywords = [w for w, _ in tfidf.most_common(top_n)]

        # Détection de tendances temporelles
        recent_facts = []
        old_facts = []
        now = datetime.now(timezone.utc)
        for nid, node in facts:
            try:
                created = datetime.fromisoformat(node.get("created", ""))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                days_ago = (now - created).total_seconds() / 86400.0
                if days_ago <= 30:
                    recent_facts.append((nid, node, days_ago))
                else:
                    old_facts.append((nid, node, days_ago))
            except (ValueError, TypeError):
                old_facts.append((nid, node, 999))

        # Top faits récents (poids × recency)
        scored_recent = []
        for nid, node, days in recent_facts:
            w = node.get("weight", 0.5) * math.pow(2, -days / DECAY_HALF_LIFE_DAYS)
            preview = node.get("content", "")[:200]
            scored_recent.append((w, nid, preview))
        scored_recent.sort(key=lambda x: -x[0])

        # Top faits importants (tous temps)
        scored_all = []
        for nid, node in facts:
            w = node.get("weight", 0.5) * (1 + node.get("access_count", 0) * 0.05)
            preview = node.get("content", "")[:200]
            scored_all.append((w, nid, preview))
        scored_all.sort(key=lambda x: -x[0])

        # Construction du résumé
        lines = []
        lines.append(f"# Résumé du domaine : {domain}")
        lines.append(f"_Généré le {self._timestamp()}_")
        lines.append(f"_{len(facts)} faits, {len(recent_facts)} récents (<30j), {len(old_facts)} anciens_")
        lines.append("")

        lines.append("## Mots-clés principaux")
        lines.append(", ".join(top_keywords[:15]))
        lines.append("")

        lines.append("## Faits les plus récents (top 5)")
        for w, nid, preview in scored_recent[:5]:
            label = self.nodes.get(nid, {}).get("label", "?").replace("_", " ").capitalize()
            lines.append(f"- **{label}** [poids {w:.2f}] : {preview}")

        lines.append("")
        lines.append("## Faits les plus importants (top 5)")
        for w, nid, preview in scored_all[:5]:
            label = self.nodes.get(nid, {}).get("label", "?").replace("_", " ").capitalize()
            lines.append(f"- **{label}** [score {w:.2f}] : {preview}")

        # Tendances : quel sujet domine récemment ?
        if recent_facts:
            recent_keywords = Counter()
            for nid, node, _ in recent_facts:
                recent_keywords.update(self._extract_keywords(node.get("content", ""), max_words=50))
            top_recent = [w for w, _ in recent_keywords.most_common(10) if w not in top_keywords[:5]]
            if top_recent:
                lines.append("")
                lines.append("## Tendances émergentes (30 derniers jours)")
                lines.append(", ".join(top_recent[:8]))

        lines.append("")
        lines.append("---")
        lines.append(f"_K-Memory v{VERSION} — Résumé automatique_")

        return "\n".join(lines)

    def summarize_all_domains(self):
        """Génère un résumé de tous les domaines non-vides."""
        output = []
        output.append(f"# K-Memory — Résumé multi-domaines")
        output.append(f"_Généré le {self._timestamp()}_")
        output.append(f"_Total : {len(self.nodes)} noeuds, {len(self.edges)} arêtes_")
        output.append("")

        for domain in sorted(self.domain_index.keys()):
            summary = self.summarize_domain(domain)
            if summary and "Pas assez" not in summary and "inconnu" not in summary:
                # Extraire juste la première section pour la vue d'ensemble
                lines = summary.split("\n")
                kw_line = ""
                for i, line in enumerate(lines):
                    if line.startswith("## Mots-clés"):
                        kw_line = lines[i + 1] if i + 1 < len(lines) else ""
                output.append(f"### {domain}")
                output.append(f"Mots-clés : {kw_line if kw_line else '(pas assez de données)'}")
                output.append("")

        output.append("---")
        output.append(f"_K-Memory v{VERSION}_")
        return "\n".join(output)

    # ═══════════════════════════════════════════════
    #  ★ NOUVEAU v2.0 — EXPORT
    # ═══════════════════════════════════════════════
    def export_markdown(self, output_path=None):
        """Exporte tout le graphe en Markdown lisible (humain + Obsidian-friendly)."""
        if output_path is None:
            os.makedirs(os.path.join(self.base_dir, EXPORT_DIR_DEFAULT), exist_ok=True)
            output_path = os.path.join(self.base_dir, EXPORT_DIR_DEFAULT, "k-memory-export.md")

        lines = []
        lines.append(f"# K-Memory Export v{VERSION}")
        lines.append(f"_Exporté le {self._timestamp()}_")
        lines.append(f"")
        lines.append(f"## Statistiques")
        lines.append(f"- **Noeuds** : {len(self.nodes)}")
        lines.append(f"- **Arrêtes** : {len(self.edges)}")
        lines.append(f"- **Domaines** : {len(self.domain_index)}")
        lines.append(f"- **Termes indexés** : {len(self.inverted_index)}")
        lines.append("")

        for domain in sorted(self.domain_index.keys()):
            lines.append(f"## Domaine : {domain}")
            lines.append("")
            node_ids = self.domain_index[domain]
            for nid in node_ids:
                node = self.nodes.get(nid, {})
                label = node.get("label", "?")
                content = node.get("content", "")
                weight = node.get("weight", 0.5)
                created = node.get("created", "")[:10]
                accessed = node.get("access_count", 0)
                lines.append(f"### {label}")
                lines.append(f"- **Poids** : {weight} | **Créé** : {created} | **Consulté** : {accessed}x")
                lines.append(f"- **Contenu** :")
                lines.append(f"  > {content[:300].replace(chr(10), chr(10) + '  > ').strip()}")
                lines.append("")

            # Connexions dans ce domaine
            domain_edges = [e for e in self.edges
                            if e["source_id"] in node_ids or e["target_id"] in node_ids]
            if domain_edges:
                lines.append(f"#### Connexions ({len(domain_edges)})")
                for e in domain_edges[:20]:  # max 20 par domaine pour lisibilité
                    src_label = self.nodes.get(e["source_id"], {}).get("label", "?")
                    tgt_label = self.nodes.get(e["target_id"], {}).get("label", "?")
                    lines.append(f"- {src_label} → {tgt_label} [{e.get('relation', 'related')}]")
                if len(domain_edges) > 20:
                    lines.append(f"- _... et {len(domain_edges) - 20} autres connexions_")
                lines.append("")

        lines.append("---")
        lines.append(f"_Généré par K-Memory v{VERSION}_")
        content = "\n".join(lines)

        with open(output_path, "w") as f:
            f.write(content)

        return output_path

    def export_mermaid(self, output_path=None, max_nodes=100):
        """Exporte le graphe au format Mermaid (diagramme direct dans Obsidian/Markdown)."""
        if output_path is None:
            os.makedirs(os.path.join(self.base_dir, EXPORT_DIR_DEFAULT), exist_ok=True)
            output_path = os.path.join(self.base_dir, EXPORT_DIR_DEFAULT, "k-memory-mermaid.md")

        # Sélectionner les max_nodes noeuds les plus importants (poids × recency × accès)
        scored_nodes = []
        for nid, node in self.nodes.items():
            w = node.get("weight", 0.5) * self._recency_weight(node)
            w *= (1 + node.get("access_count", 0) * 0.1)
            scored_nodes.append((w, nid, node))
        scored_nodes.sort(key=lambda x: -x[0])
        top_nodes = {nid for _, nid, _ in scored_nodes[:max_nodes]}

        lines = []
        lines.append("```mermaid")
        lines.append("graph LR")
        lines.append("")

        # Noeuds
        label_count = defaultdict(int)
        for _, nid, node in scored_nodes[:max_nodes]:
            label = node.get("label", "?").replace("(", "[").replace(")", "]")
            label = re.sub(r'[^a-zA-Z0-9_À-ÿ\-\s]', '', label)[:40]
            # Éviter les labels vides
            if not label.strip():
                label = node.get("domain", "unknown")
            # Suffix pour unicité
            key = re.sub(r'\s+', '_', label.strip().lower())[:20]
            label_count[key] += 1
            if label_count[key] > 1:
                key = f"{key}_{label_count[key]}"
            domain_class = node.get("domain", "general").replace(" ", "_")
            lines.append(f"    {key}[{label}]:::{domain_class}")

        # Arrêtes entre les top nodes
        for e in self.edges:
            src = e["source_id"]
            tgt = e["target_id"]
            if src in top_nodes and tgt in top_nodes:
                src_label = self.nodes.get(src, {}).get("label", "?")
                tgt_label = self.nodes.get(tgt, {}).get("label", "?")
                src_key = re.sub(r'\s+', '_', src_label.strip().lower())[:20]
                tgt_key = re.sub(r'\s+', '_', tgt_label.strip().lower())[:20]
                rel = e.get("relation", "related")
                lines.append(f"    {src_key} -->|{rel}| {tgt_key}")

        lines.append("")
        # Styles par domaine
        colors = {
            "system": "#6c5ce7",
            "rules": "#d63031",
            "decisions": "#fdcb6e",
            "general": "#00b894",
            "ai": "#0984e3",
            "security": "#e17055",
            "games": "#a29bfe",
            "knowledge": "#00cec9",
            "math": "#fd79a8",
            "physics": "#e84393"
        }
        for domain in self.domain_index:
            color = colors.get(domain, "#636e72")
            class_name = domain.replace(" ", "_")
            lines.append(f"    classDef {class_name} fill:{color}33,stroke:{color},stroke-width:2px;")

        lines.append("")
        lines.append("```")
        lines.append("")
        lines.append(f"_K-Memory v{VERSION} — {len(top_nodes)} noeuds, {len(self.edges)} connexions_")

        content = "\n".join(lines)
        with open(output_path, "w") as f:
            f.write(content)
        return output_path

    # ═══════════════════════════════════════════════
    #  STATS
    # ═══════════════════════════════════════════════
    def stats(self):
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "domains": len(self.domain_index),
            "brain_dir": self.brain_dir,
            "terms": len(self.inverted_index),
            "version": VERSION,
            "decay_half_life_days": DECAY_HALF_LIFE_DAYS
        }

    def save(self):
        """Sauvegarde l'état complet du graphe sur disque."""
        data = {
            "nodes": self.nodes,
            "edges": self.edges,
            "inverted_index": dict(self.inverted_index),
            "domain_index": dict(self.domain_index),
            "updated_at": self._now(),
            "version": VERSION,
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "total_domains": len(self.domain_index),
                "total_indexed_terms": len(self.inverted_index)
            }
        }
        with open(self.graph_file, "w") as f:
            json.dump(data, f, indent=2)

        # Mise à jour de l'index.md
        idx_lines = [
            f"# K-Memory Index",
            f"Version: {VERSION}",
            f"Mis à jour: {self._now()[:19].replace('T', ' ')}",
            f"Noeuds: {len(self.nodes)}",
            f"Arrêtes: {len(self.edges)}",
            f"",
            f"## Domaines"
        ]
        for d in sorted(self.domain_index):
            idx_lines.append(f"- {d}: {len(self.domain_index[d])}")
        idx_lines.append("")
        with open(self.index_file, "w") as f:
            f.write("\n".join(idx_lines))


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    core = KMemoryCore().initialize()

    if len(sys.argv) < 2:
        s = core.stats()
        print(f"✓ K-Memory v{VERSION}: {s['nodes']} noeuds, {s['edges']} arêtes, {s['domains']} domaines, {s['terms']} termes")
        print(f"  Recency: demi-vie {DECAY_HALF_LIFE_DAYS} jours")
        print(f"  Base: {s['brain_dir']}")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "--remember" and len(sys.argv) > 2:
        fact = " ".join(sys.argv[2:])
        domain = "general"
        importance = 0.5
        if "--domain" in sys.argv:
            idx = sys.argv.index("--domain")
            if idx + 1 < len(sys.argv):
                domain = sys.argv[idx + 1]
        if "--importance" in sys.argv:
            idx = sys.argv.index("--importance")
            if idx + 1 < len(sys.argv):
                try:
                    importance = float(sys.argv[idx + 1])
                except ValueError:
                    pass
        nid = core.remember(fact, domain, importance)
        core.save()
        print(f"✓ Fait enregistré [domaine: {domain}, importance: {importance}, id: {nid}]")

    elif cmd == "--recall" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = core.recall(query)
        if results:
            for item in results:
                rec = item.get("recency", "?")
                print(f"  • {item['label']} [{item['domain']}] confiance: {item['confidence']} (recency: {rec})")
                if item.get("preview"):
                    print(f"    ↳ {item['preview'][:120]}")
        else:
            print(f"  Aucun résultat pour: {query}")

    elif cmd == "--summarize":
        if "--domain" in sys.argv:
            idx = sys.argv.index("--domain")
            if idx + 1 < len(sys.argv):
                domain = sys.argv[idx + 1]
                print(core.summarize_domain(domain))
            else:
                print("Erreur: --domain nécessite un nom de domaine")
        else:
            # Résumé multi-domaines
            print(core.summarize_all_domains())

    elif cmd == "--export":
        fmt = "markdown"
        if "--mermaid" in sys.argv:
            fmt = "mermaid"
        path = core.export_mermaid() if fmt == "mermaid" else core.export_markdown()
        print(f"✓ Exporté vers: {path}")

    elif cmd == "--version":
        print(f"K-Memory v{VERSION}")

    else:
        print(f"Usage: python3 k-core.py [--remember|--recall|--summarize|--export]")
        print(f"  --remember <fait> [--domain <sujet>] [--importance 0.0-1.0]")
        print(f"  --recall <query>")
        print(f"  --summarize [--domain <sujet>]")
        print(f"  --export [--mermaid]")
