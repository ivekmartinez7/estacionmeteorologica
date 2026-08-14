import json
import sys
from pathlib import Path
from graphify.detect import detect
from graphify.extract import collect_files, extract
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json

def build_project_graph():
    Path("graphify-out").mkdir(exist_ok=True)
    root = Path(".").resolve()
    Path("graphify-out/.graphify_python").write_text(sys.executable, encoding="utf-8")
    Path("graphify-out/.graphify_root").write_text(str(root), encoding="utf-8")

    # 1. Detect files
    detection = detect(root)
    code_files = [Path(f) for f in detection.get("files", {}).get("code", [])]
    print(f"Code files detected: {len(code_files)}")

    # 2. Extract AST
    ast_result = extract(code_files, cache_root=root) if code_files else {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}
    nodes = ast_result.get("nodes", [])
    edges = ast_result.get("edges", [])
    print(f"AST extracted: {len(nodes)} nodes, {len(edges)} edges")

    extraction = {
        "nodes": nodes,
        "edges": edges,
        "hyperedges": [],
        "input_tokens": 0,
        "output_tokens": 0
    }

    # 3. Build Graph
    G = build_from_json(extraction, root=str(root), directed=False)
    print(f"Graph nodes: {G.number_of_nodes()}, edges: {G.number_of_edges()}")

    if G.number_of_nodes() > 0:
        communities = cluster(G)
        cohesion = score_all(G, communities)
        gods = god_nodes(G)
        surprises = surprising_connections(G, communities)
        labels = {cid: f"Community {cid}" for cid in communities}
        questions = suggest_questions(G, communities, labels)

        to_json(G, communities, "graphify-out/graph.json")
        tokens = {"input": 0, "output": 0}
        report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, str(root), suggested_questions=questions)
        Path("graphify-out/GRAPH_REPORT.md").write_text(report, encoding="utf-8")
        print("Successfully generated graphify-out/graph.json and graphify-out/GRAPH_REPORT.md!")

if __name__ == "__main__":
    build_project_graph()
