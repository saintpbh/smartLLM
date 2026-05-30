"""Community detection, noise filtering, and cohesion metrics for knowledge graphs."""

from __future__ import annotations

import networkx as nx
from collections import Counter
from networkx.algorithms.community import greedy_modularity_communities

def _filter_noise_nodes(G: nx.DiGraph) -> set[str]:
    """Identify noise and placeholder nodes that should be ignored during community clustering."""
    noise = set()
    generic_labels = {"__init__", "index", "main", "utils", "helpers", "types", "config"}
    
    for nid in G.nodes():
        deg = G.degree(nid)
        label = G.nodes[nid].get("label", "").lower()
        file_type = G.nodes[nid].get("file_type", "")
        
        if "__unresolved__" in nid or file_type == "placeholder":
            noise.add(nid)
        elif deg == 0:
            noise.add(nid)
        elif deg == 1 and (len(label) <= 3 or label in generic_labels):
            noise.add(nid)
            
    return noise

def cluster_graph(G: nx.DiGraph, min_size: int = 3) -> dict[int, list[str]]:
    """Cluster graph nodes into communities using Greedy Modularity with noise filtering and tiny community merging."""
    if G.number_of_nodes() == 0:
        return {0: []}
        
    noise = _filter_noise_nodes(G)
    clean_nodes = [n for n in G.nodes() if n not in noise]
    
    if not clean_nodes:
        return {0: []}
        
    subgraph = G.subgraph(clean_nodes).copy()
    undirected = subgraph.to_undirected()
    
    try:
        raw_communities = list(greedy_modularity_communities(undirected))
    except Exception:
        return {0: clean_nodes}
        
    # Build initial mappings
    node_to_comm: dict[str, int] = {}
    communities: dict[int, list[str]] = {}
    for i, comm in enumerate(raw_communities):
        communities[i] = sorted(comm)
        for nid in comm:
            node_to_comm[nid] = i

    # Merge tiny communities
    tiny_cids = [cid for cid, members in communities.items() if len(members) < min_size]
    for cid in tiny_cids:
        members = communities[cid]
        neighbor_comm_counts: Counter[int] = Counter()
        
        for nid in members:
            for neighbor in undirected.neighbors(nid):
                ncid = node_to_comm.get(neighbor)
                if ncid is not None and ncid != cid and ncid not in tiny_cids:
                    neighbor_comm_counts[ncid] += 1
                    
        if neighbor_comm_counts:
            target_cid = neighbor_comm_counts.most_common(1)[0][0]
            communities[target_cid].extend(members)
            for nid in members:
                node_to_comm[nid] = target_cid
            del communities[cid]

    # Re-index to sequential IDs
    result: dict[int, list[str]] = {}
    for new_id, (_, members) in enumerate(sorted(communities.items())):
        result[new_id] = sorted(members)
        
    return result

def calculate_cohesion(G: nx.DiGraph, communities: dict[int, list[str]]) -> dict[int, float]:
    """Score each community's internal link density as cohesion (0.0 to 1.0)."""
    scores: dict[int, float] = {}
    undirected = G.to_undirected()
    
    for cid, members in communities.items():
        n = len(members)
        if n <= 1:
            scores[cid] = 1.0
            continue
            
        possible = n * (n - 1) / 2
        member_set = set(members)
        internal = 0
        
        for u in members:
            for v in undirected.neighbors(u):
                if v in member_set and v > u:
                    internal += 1
                    
        scores[cid] = internal / possible if possible > 0 else 0.0
        
    return scores
