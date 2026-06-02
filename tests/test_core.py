#!/usr/bin/env python3
"""K-Memory Test Suite — 0 dépendance, pur Python stdlib"""
import sys, os, tempfile, shutil, importlib.util

# Charger k-core.py sans dépendance de chemin
core_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "k-core.py")
spec = importlib.util.spec_from_file_location("kcore", core_path)
kcore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kcore)
KMemoryCore = kcore.KMemoryCore

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        suffix = f" — {detail}" if detail else ""
        print(f"  ❌ {name}{suffix}")


def test():
    global PASS, FAIL
    tmp = tempfile.mkdtemp(prefix="kmem_test_")

    try:
        # ── 1. Initialisation ───────────────────
        print("\n📦 Initialisation")
        core = KMemoryCore(base_dir=tmp)
        core.initialize()
        check("Brain créé", os.path.isdir(core.brain_dir))
        check("4 lobes initiaux", len(core.nodes) >= 4)
        check("Domaines minimum", len(core.domain_index) >= 3)

        # ── 2. Remember ─────────────────────────
        print("\n🧠 Remember")
        core.remember("KensaiArt est une marque wabi-sabi", domain="brand", importance=1.0)
        check("1 fait brand", core._count_domain_facts("brand") == 1)
        core.remember("L'eau bout à 100 degrés Celsius", domain="science", importance=0.9)
        core.remember("Le soleil est une étoile de type G", domain="science", importance=0.7)
        check("2 faits science", core._count_domain_facts("science") == 2)

        # ── 3. Déduplication ────────────────────
        print("\n🔄 Déduplication")
        before = core._count_domain_facts("science")
        core.remember("Le soleil est une étoile de type G dans la Voie lactée", domain="science")
        after = core._count_domain_facts("science")
        check("Phrase similaire = fusion (pas doublon)", after <= before)
        core.remember("Pangolin est un mammifère à écailles", domain="science")
        check("Sujet unique = nouveau fait", core._count_domain_facts("science") > before)

        # ── 4. Recall ───────────────────────────
        print("\n🔍 Recall")
        results = core.recall("étoile soleil")
        check("Recall trouve le fait", len(results) > 0)
        results = core.recall("kensaiart marque wabi")
        check("Recall multi-mots", len(results) > 0)
        results = core.recall("inexistant_xyz_123")
        check("Recall mot inexistant = vide", len(results) == 0)

        # ── 5. Recency boost ────────────────────
        print("\n⏱️ Recency")
        results = core.recall("soleil étoile")
        if results and "recency" in results[0]:
            check("Récence du dernier recall >= 0.9", results[0]["recency"] >= 0.9)

        # ── 6. Graphe ───────────────────────────
        print("\n🔗 Graphe")
        check("Arrêtes créées", len(core.edges) > 0)
        check("Index inversé rempli", len(core.inverted_index) > 0)

        # ── 7. Export ───────────────────────────
        print("\n📄 Export")
        path = core.export_markdown()
        check("Export créé", os.path.exists(path))
        with open(path) as f:
            content = f.read()
        check("Export contient science", "science" in content.lower())
        check("Export contient brand", "brand" in content.lower())

        # ── 8. Export Mermaid ───────────────────
        print("\n🧜 Export Mermaid")
        path = core.export_mermaid(max_nodes=5)
        check("Mermaid exporté", os.path.exists(path))
        with open(path) as f:
            content = f.read()
        check("Contient mermaid block", "```mermaid" in content)
        check("Contient graph LR", "graph LR" in content)

        # ── 9. Résumé multi-domaines ───────────
        print("\n📊 Résumé")
        summary = core.summarize_all_domains()
        check("summarize_all retourne du texte", len(summary) > 100)
        check("Contient K-Memory", "K-Memory" in summary)

        # ── 10. Persistance ────────────────────
        print("\n💾 Persistance")
        core.save()
        n_before = len(core.nodes)
        e_before = len(core.edges)
        core2 = KMemoryCore(base_dir=tmp)
        core2.initialize()
        check("Recharge préserve les noeuds", len(core2.nodes) >= n_before)
        check("Recharge préserve les arrêtes", len(core2.edges) >= e_before)
        check("Domaines préservés",
              set(core2.domain_index.keys()) == set(core.domain_index.keys()))

        # ── 11. Stats ──────────────────────────
        print("\n📊 Stats")
        s = core.stats()
        check("Noeuds > 0", s["nodes"] > 0)
        check("Arrêtes > 0", s["edges"] > 0)
        check("Domaines > 0", s["domains"] > 0)
        check("Termes > 0", s["terms"] > 0)
        check("Version présente", bool(s.get("version")))

        # ── 12. Version ────────────────────────
        print("\n🏷️ Version")
        check("Version = 2.1", kcore.VERSION == "2.1")

    finally:
        shutil.rmtree(tmp)

    total = PASS + FAIL
    print(f"\n{'=' * 50}")
    print(f"  {'✅ TOUT OK' if FAIL == 0 else '⚠️ ÉCHECS'}")
    print(f"  {PASS}/{total} tests réussis")
    print(f"{'=' * 50}\n")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if test() else 1)
