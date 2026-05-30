"""Hierarchical knowledge graph building and reference resolution with semantic edge weighting."""

from __future__ import annotations

import networkx as nx
import numpy as np
from smart_llm.embed import SimpleSemanticVectorizer

def build_graph(extraction: dict) -> nx.DiGraph:
    """Build a NetworkX DiGraph, resolve cross-file unresolved references, and compute semantic weights on edges."""
    G = nx.DiGraph()

    # 1. Add all defined nodes
    seen_nodes: set[str] = set()
    label_to_node_id: dict[str, str] = {}
    node_texts: dict[str, str] = {}  # nid -> text for semantic similarity

    for node in extraction.get("nodes", []):
        nid = node["id"]
        if nid in seen_nodes:
            continue
        seen_nodes.add(nid)
        
        attrs = {k: v for k, v in node.items() if k != "id"}
        G.add_node(nid, **attrs)
        
        label = node.get("label", "").lower()
        if label:
            label_to_node_id[label] = nid
            
        # Compile a semantic text description of this node
        desc = f"{label} {node.get('entity_type', '')} {node.get('source_file', '')}"
        node_texts[nid] = desc

    # 2. Build semantic vectorizer for node texts to compute cosine similarity
    vectorizer = SimpleSemanticVectorizer()
    node_ids = list(node_texts.keys())
    texts = list(node_texts.values())
    
    node_embeddings: dict[str, np.ndarray] = {}
    if texts:
        try:
            vectorizer.fit(texts)
            embeddings = vectorizer.transform(texts)
            for idx, nid in enumerate(node_ids):
                node_embeddings[nid] = embeddings[idx]
        except Exception:
            pass

    # 3. Add edges and resolve references
    for edge in extraction.get("edges", []):
        src = edge["source"]
        tgt = edge["target"]

        # Resolve unresolved reference links
        if tgt.startswith("__unresolved__::ref::"):
            ref_label = tgt.split("::")[-1]
            if ref_label in label_to_node_id:
                tgt = label_to_node_id[ref_label]
            else:
                if tgt not in G:
                    G.add_node(tgt, label=ref_label, file_type="placeholder", source_file="", source_location=None)
        
        if src.startswith("__unresolved__::ref::"):
            ref_label = src.split("::")[-1]
            if ref_label in label_to_node_id:
                src = label_to_node_id[ref_label]
            else:
                if src not in G:
                    G.add_node(src, label=ref_label, file_type="placeholder", source_file="", source_location=None)

        if src not in G:
            G.add_node(src, label=src, file_type="placeholder", source_file="", source_location=None)
        if tgt not in G:
            G.add_node(tgt, label=tgt, file_type="placeholder", source_file="", source_location=None)

        # 4. Calculate semantic weight (distance = 1.0 - cosine_similarity)
        distance = 1.0
        if src in node_embeddings and tgt in node_embeddings:
            v_src = node_embeddings[src]
            v_tgt = node_embeddings[tgt]
            if v_src.shape == v_tgt.shape:
                similarity = float(np.dot(v_src, v_tgt))
                # Map similarity to distance: more similar = smaller distance (e.g. 0.1 to 1.0)
                distance = max(0.1, 1.0 - similarity)

        attrs = {k: v for k, v in edge.items() if k not in ("source", "target")}
        attrs["weight"] = distance  # Dijkstra semantic distance weight
        G.add_edge(src, tgt, **attrs)

    return G

def serialize_graph(G: nx.DiGraph) -> dict:
    """Serialize DiGraph to standard JSON structure."""
    nodes = []
    for nid, data in G.nodes(data=True):
        node_dict = {"id": nid}
        node_dict.update(data)
        nodes.append(node_dict)
        
    links = []
    for src, tgt, data in G.edges(data=True):
        link_dict = {"source": src, "target": tgt}
        link_dict.update(data)
        links.append(link_dict)
        
    return {
        "nodes": nodes,
        "links": links
    }
