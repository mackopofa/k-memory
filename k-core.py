#!/usr/bin/env python3
"""K-Memory Core v2.1 — hybride : code propre v1.2 + features v2.0 sans pièges"""
import json, os, hashlib, glob, re, sys, difflib, math
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ──────────────────────────────────────────────
#  CONSTANTES
# ──────────────────────────────────────────────
VERSION = "2.1"
RECENCY_HALF_LIFE_DAYS = 90
AUTO_SUMMARY_THRESHOLD = 15


class KMemoryCore:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.join(os.path.expanduser("~"), ".hermes", "k-memory")
        self.brain_dir = os.path.join(self.base_dir, "brain")
        self.graph_file = os.path.join(self.base_dir, "graph.json")
        self.index_file = os.path.join(self.base_dir, "index.md")
        self.summary_dir = os.path.join(self.base_dir, "summaries")
        self.export_dir = os.path.join(self.base_dir, "exports")
        self.nodes = {}
        self.edges = []
        self.inverted_index = defaultdict(list)
        self.domain_index = defaultdict(list)

    # ── Initialisation ────────────────────────

    def initialize(self):
        os.makedirs(self.brain_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)
        self._load_graph()
        if not self.nodes:
            now = datetime.now(timezone.utc).isoformat()
            seed = {
                "system-identity": {
                    "label": "Identité",
                    "content": f"K-Memory initialisé {now}",
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
                    "content": f"{now} | Création",
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
            if os.path.basename(fp) == "index.md":
                continue
            with open(fp) as f:
                c = f.read()
            nid = hashlib.sha256(c.encode()).hexdigest()[:16]
            if nid not in self.nodes:
                self._add_node("lobe", os.path.basename(fp).replace(".md", ""), c[:2000], weight=0.8, domain="general")

    # ── Helpers ───────────────────────────────

    def _hash(self, c):
        return hashlib.sha256(c.encode()).hexdigest()[:16]

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def _now_dt(self):
        return datetime.now(timezone.utc)

    def _parse_date(self, date_str):
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    def _extract_keywords(self, text):
        words = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', text.lower())
        stop = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one",
            "our", "out", "has", "have", "been", "some", "same", "also", "its", "than", "them", "they",
            "this", "that", "with", "from", "their", "which", "what", "when", "where", "how", "who",
            "dans", "avec", "pour", "sur", "pas", "les", "des", "est", "que", "une", "nous", "vous",
            "elle", "ils", "ont", "sont", "fait", "mais", "elus", "cette", "comme", "plus", "tout",
            "tous", "leur", "leurs", "deux", "dont", "entre", "apres", "avant", "chez",
            "etre", "peut", "faire"
        }
        return [w for w in words if w not in stop]

    def _recency_score(self, created_str):
        """Score de récence exponentiel. Aujourd'hui=1.0, 90j=0.5, 180j=0.25"""
        created = self._parse_date(created_str)
        if not created:
            return 0.5
        age_days = (self._now_dt() - created).total_seconds() / 86400
        if age_days < 0:
            return 1.0
        return math.exp(-math.log(2) * age_days / RECENCY_HALF_LIFE_DAYS)

    # ── Graphe ────────────────────────────────

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

    def _count_domain_facts(self, domain):
        return sum(1 for n in self.nodes.values()
                   if n.get("domain") == domain and n.get("type") in ("fact", "lobe"))

    # ── Auto-Summary ──────────────────────────

    def _auto_summary(self, domain):
        facts = [n for n in self.nodes.values()
                 if n.get("domain") == domain and n.get("type") == "fact"]
        if len(facts) < AUTO_SUMMARY_THRESHOLD:
            return None

        def score(f):
            w = f.get("weight", 0.5)
            ac = min(f.get("access_count", 1), 20) * 0.05
            rec = self._recency_score(f.get("created", ""))
            return w + ac + rec * 0.5

        facts_sorted = sorted(facts, key=score, reverse=True)
        top = facts_sorted[:10]
        recent = sorted(facts, key=lambda f: f.get("created", ""), reverse=True)[:5]

        now_str = self._now()[:19].replace("T", " ")
        lines = [
            f"# Résumé automatique — {domain}",
            f"Généré le {now_str}",
            f"Total faits : {len(facts)}",
            "",
            "## 🔥 Faits importants (poids × consultation × récence)",
            ""
        ]
        for f in top:
            content = f.get("content", "")
            clean = re.sub(r'^\[\d[\d\-T: ]+\]\s*', '', content)
            if len(clean) > 150:
                clean = clean[:150] + "..."
            lines.append(f"- {clean}")

        lines += ["", "## 🆕 Derniers ajouts", ""]
        for f in recent:
            content = f.get("content", "")
            clean = re.sub(r'^\[\d[\d\-T: ]+\]\s*', '', content)
            if len(clean) > 120:
                clean = clean[:120] + "..."
            lines.append(f"- {clean}")

        oldest = min(facts, key=lambda f: f.get("created", ""))
        newest = max(facts, key=lambda f: f.get("created", ""))
        avg_weight = sum(f.get("weight", 0.5) for f in facts) / len(facts)
        lines += [
            "",
            "## 📊 Statistiques",
            f"- Premier fait : {oldest.get('created', '?')[:10]}",
            f"- Dernier fait : {newest.get('created', '?')[:10]}",
            f"- Poids moyen : {avg_weight:.2f}",
            f"- Consultations totales : {sum(f.get('access_count', 0) for f in facts)}",
        ]

        summary = "\n".join(lines)
        sp = os.path.join(self.summary_dir, f"{domain}.md")
        with open(sp, "w") as f:
            f.write(summary)

        self._add_node("summary", f"Résumé {domain} {now_str[:10]}", summary[:2000],
                       weight=0.7, domain=domain, tags=["auto-summary"])
        return summary

    # ── Remember ──────────────────────────────

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
            if other_nid != nid and other.get("domain") == domain and other.get("type") in ("fact", "lobe"):
                self._add_edge(nid, other_nid, "related", 0.4)
                break

        keywords = self._extract_keywords(fact)
        for kw in keywords[:5]:
            for other_nid in self.inverted_index.get(kw, []):
                if other_nid != nid:
                    self._add_edge(nid, other_nid, "keyword", 0.3)
                    break

        count = self._count_domain_facts(domain)
        if count >= AUTO_SUMMARY_THRESHOLD and count % 5 == 0:
            self._auto_summary(domain)

        return nid

    def _index_node(self, nid, text):
        for w in self._extract_keywords(text):
            if nid not in self.inverted_index[w]:
                self.inverted_index[w].append(nid)

    # ── Recall ────────────────────────────────

    def recall(self, query, limit=5):
        words = self._extract_keywords(query)
        scores = defaultdict(float)
        for w in words:
            for nid in self.inverted_index.get(w, []):
                node = self.nodes.get(nid)
                if node:
                    base = node.get("weight", 0.5) * (1 + node.get("access_count", 0) * 0.02)
                    rec = self._recency_score(node.get("created", ""))
                    scores[nid] += base * (0.7 + 0.3 * rec)
        for nid in scores:
            count = sum(1 for w in words if nid in self.inverted_index.get(w, []))
            scores[nid] *= (1 + count * 0.2)
        results = []
        for nid, sc in sorted(scores.items(), key=lambda x: -x[1])[:limit]:
            n = self.nodes[nid]
            content_preview = n.get("content", "")[:150]
            created = n.get("created", "")[:10] if n.get("created") else "?"
            results.append({
                "label": n["label"], "domain": n["domain"],
                "confidence": round(sc, 3), "preview": content_preview,
                "accessed": n.get("access_count", 0), "created": created,
                "recency": round(self._recency_score(n.get("created", "")), 3)
            })
            self.nodes[nid]["access_count"] += 1
            self.nodes[nid]["last_accessed"] = self._now()
        return results

    # ── Export Markdown ───────────────────────

    def export_markdown(self, domain=None):
        now_str = self._now()[:19].replace("T", " ")
        lines = [
            f"# K-Memory Export v{VERSION}",
            f"Exporté le {now_str}",
            f"Noeuds : {len(self.nodes)} | Arrêtes : {len(self.edges)} | Domaines : {len(self.domain_index)}",
            "", "---", ""
        ]

        domains = sorted(self.domain_index.keys())
        if domain:
            domains = [d for d in domains if d == domain]

        for dom in domains:
            nids = self.domain_index[dom]
            if not nids:
                continue
            lines.append(f"## Domaine : {dom}")
            lines.append(f"*{len(nids)} entrées*")
            lines.append("")

            for nid in nids:
                node = self.nodes.get(nid)
                if not node:
                    continue
                label = node.get("label", "?")
                content = node.get("content", "")
                created = node.get("created", "?")[:10]
                ntype = node.get("type", "?")
                accessed = node.get("access_count", 0)

                lines.append(f"### {label}")
                lines.append(f"*Type: {ntype} | Créé: {created} | Consultations: {accessed}*")
                lines.append("")
                clean = content.replace("\n", "\n\n") if "\n\n" not in content else content
                lines.append(clean)
                lines.append("")
                lines.append("---")
                lines.append("")

        if os.path.isdir(self.summary_dir):
            summaries = glob.glob(os.path.join(self.summary_dir, "*.md"))
            if summaries:
                lines += ["", "# Résumés automatiques", ""]
                for sp in sorted(summaries):
                    lines.append(f"## {os.path.basename(sp).replace('.md', '')}")
                    lines.append("")
                    with open(sp) as f:
                        lines.append(f.read())
                    lines.append("")
                    lines.append("---")
                    lines.append("")

        export = "\n".join(lines)
        export_path = os.path.join(self.export_dir, f"k-memory-export-{now_str[:10]}.md")
        with open(export_path, "w") as f:
            f.write(export)
        return export_path

    # ── Export Mermaid (v2.1+) ─────────────────

    def export_mermaid(self, max_nodes=100):
        now_str = self._now()[:19].replace("T", " ")
        # Top N noeuds les plus importants
        scored_nodes = []
        for nid, node in self.nodes.items():
            w = node.get("weight", 0.5) * (0.7 + 0.3 * self._recency_score(node.get("created", "")))
            w *= (1 + node.get("access_count", 0) * 0.05)
            scored_nodes.append((w, nid, node))
        scored_nodes.sort(key=lambda x: -x[0])
        top_nodes = {nid for _, nid, _ in scored_nodes[:max_nodes]}

        lines = ["```mermaid", "graph LR", ""]

        label_seen = defaultdict(int)
        for _, nid, node in scored_nodes[:max_nodes]:
            label = node.get("label", "?").replace("[", "(").replace("]", ")")
            label = re.sub(r'[^a-zA-Z0-9_À-ÿ\s\-]', '', label)[:40]
            if not label.strip():
                label = node.get("domain", "unknown")
            key = re.sub(r'\s+', '_', label.strip().lower())[:20]
            label_seen[key] += 1
            if label_seen[key] > 1:
                key = f"{key}_{label_seen[key]}"
            lines.append(f"    {key}[\"{label}\"]")

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
        lines.append("```")
        lines.append("")
        lines.append(f"_K-Memory v{VERSION} — {len(top_nodes)} noeuds, {len(self.edges)} connexions_")

        content = "\n".join(lines)
        path = os.path.join(self.export_dir, f"k-memory-mermaid-{now_str[:10]}.md")
        with open(path, "w") as f:
            f.write(content)
        return path

    # ── Résumé multi-domaines (v2.1+) ─────────

    def summarize_all_domains(self):
        output = [
            f"# K-Memory — Résumé multi-domaines",
            f"Généré le {self._now()[:19].replace('T', ' ')}",
            f"Total : {len(self.nodes)} noeuds, {len(self.edges)} arêtes",
            ""
        ]
        for domain in sorted(self.domain_index.keys()):
            nids = self.domain_index[domain]
            fact_count = sum(1 for n in nids if self.nodes.get(n, {}).get("type") == "fact")
            lines_out = [
                f"### {domain}",
                f"Facts: {fact_count} | Total: {len(nids)} entrées"
            ]
            # Si assez de faits, faire un mini-résumé
            if fact_count >= AUTO_SUMMARY_THRESHOLD:
                s = self._auto_summary(domain)
                if s:
                    for line in s.split("\n")[4:8]:  # top keywords + 2 lignes
                        lines_out.append(f"  {line}")
            output.append("\n".join(lines_out))
            output.append("")

        output.append("---")
        output.append(f"_K-Memory v{VERSION}_")
        return "\n".join(output)

    # ── Stats ─────────────────────────────────

    def stats(self):
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "domains": len(self.domain_index),
            "brain_dir": self.brain_dir,
            "terms": len(self.inverted_index),
            "version": VERSION
        }

    # ── Sauvegarde ────────────────────────────

    def save(self):
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

        idx_lines = [
            f"# K-Memory Index",
            f"Version: {VERSION}",
            f"Mis à jour: {self._now()[:19].replace('T', ' ')}",
            f"Noeuds: {len(self.nodes)}",
            f"Arrêtes: {len(self.edges)}",
            "",
            "## Domaines"
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
        core.save()
        s = core.stats()
        print(f"✓ K-Memory v{VERSION}: {s['nodes']} noeuds, {s['edges']} arêtes, {s['domains']} domaines, {s['terms']} termes")
        print(f"  Base: {s['brain_dir']}")
        sys.exit(0)

    cmd = sys.argv[1]

    # ── --version ──────────────────────────────
    if cmd == "--version":
        print(f"K-Memory v{VERSION}")

    # ── --remember ─────────────────────────────
    elif cmd == "--remember" and len(sys.argv) > 2:
        args = sys.argv[2:]
        domain = "general"
        importance = 0.5
        cleaned = []
        skip_next = False
        for i, a in enumerate(args):
            if skip_next:
                skip_next = False
                continue
            if a == "--domain" and i + 1 < len(args):
                domain = args[i + 1]
                skip_next = True
                continue
            if a == "--importance" and i + 1 < len(args):
                try:
                    importance = float(args[i + 1])
                except ValueError:
                    pass
                skip_next = True
                continue
            cleaned.append(a)
        fact = " ".join(cleaned)
        nid = core.remember(fact, domain, importance)
        core.save()
        print(f"✓ Fait enregistré [domaine: {domain}, importance: {importance}]")

    # ── --recall ───────────────────────────────
    elif cmd == "--recall" and len(sys.argv) > 2:
        r = core.recall(" ".join(sys.argv[2:]))
        for item in r:
            rec_str = f" récence: {item['recency']}" if item.get("recency") else ""
            print(f"  • {item['label']} [{item['domain']}] confiance: {item['confidence']}{rec_str}")
            if item.get("preview"):
                print(f"    ↳ {item['preview'][:120]}")
            if item.get("created"):
                print(f"    🗓️ {item['created']}")

    # ── --summary ──────────────────────────────
    elif cmd == "--summary":
        domain = "general"
        if "--domain" in sys.argv:
            idx = sys.argv.index("--domain")
            if idx + 1 < len(sys.argv):
                domain = sys.argv[idx + 1]
        summary = core._auto_summary(domain)
        if summary:
            print(summary)
        else:
            count = core._count_domain_facts(domain)
            print(f"Pas assez de faits pour un résumé ({count}/{AUTO_SUMMARY_THRESHOLD})")

    # ── --summarize-all (v2.1+) ───────────────
    elif cmd == "--summarize-all":
        print(core.summarize_all_domains())

    # ── --export ───────────────────────────────
    elif cmd == "--export":
        domain = None
        if "--domain" in sys.argv:
            idx = sys.argv.index("--domain")
            if idx + 1 < len(sys.argv):
                domain = sys.argv[idx + 1]
        if "--mermaid" in sys.argv:
            path = core.export_mermaid()
        else:
            path = core.export_markdown(domain)
        print(f"✓ Exporté → {path}")

    else:
        print(f"K-Memory v{VERSION}")
        print(f"Usage: python3 k-core.py [--version|--remember|--recall|--summary|--summarize-all|--export]")
        print(f"  --version")
        print(f"  --remember <fait> [--domain <sujet>] [--importance 0.0-1.0]")
        print(f"  --recall <query>")
        print(f"  --summary [--domain <sujet>]")
        print(f"  --summarize-all")
        print(f"  --export [--domain <sujet>] [--mermaid]")
