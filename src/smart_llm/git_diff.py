"""Git diff analysis and incremental knowledge graph compilation."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from smart_llm.detect import EXT_MAP, SKIP_DIRS, SKIP_DATA_FILES, BINARY_DOCUMENT_EXTS

def get_git_changes(workspace_path: Path) -> dict[str, list[str]]:
    """Determine modified, added, and deleted files using git status."""
    workspace_path = Path(workspace_path).resolve()
    
    # Verify if it is a git repository
    if not (workspace_path / ".git").exists():
        return {"modified": [], "deleted": []}

    try:
        # Run git status porcelain for parsing-friendly output
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return {"modified": [], "deleted": []}

    modified = []
    deleted = []

    for line in res.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        file_path_str = line[3:].strip()
        
        # Handle renames (R status has "old -> new" structure)
        if " -> " in file_path_str:
            file_path_str = file_path_str.split(" -> ")[1].strip()

        # Check if the file is in a skipped directory
        parts = Path(file_path_str).parts
        if any(p in SKIP_DIRS for p in parts):
            continue

        ext = os.path.splitext(file_path_str)[1].lower()
        category = EXT_MAP.get(ext)
        if category is None:
            continue
            
        if category == "data" and Path(file_path_str).name.lower() in SKIP_DATA_FILES:
            continue

        if status in (" M", "M ", " A", "A ", "??"):
            modified.append(file_path_str)
        elif status in (" D", "D "):
            deleted.append(file_path_str)

    return {
        "modified": modified,
        "deleted": deleted
    }


def incremental_update_graph(
    existing_graph: dict,
    changes: dict[str, list[str]],
    workspace_path: Path
) -> dict:
    """Incrementally updates an existing knowledge graph by replacing dirty files' subgraphs.
    
    Args:
        existing_graph: Dict serialization of the current DiGraph (nodes, links).
        changes: Dict from get_git_changes containing 'modified' and 'deleted' lists.
        workspace_path: The project root directory.
        
    Returns:
        Updated graph serialization.
    """
    from smart_llm.extract import extract_files
    
    modified_files = changes.get("modified", [])
    deleted_files = changes.get("deleted", [])
    
    dirty_source_paths = {str(workspace_path / f) for f in modified_files + deleted_files}
    
    # 1. Filter out all nodes and edges originating from the dirty/deleted files
    clean_nodes = []
    for node in existing_graph.get("nodes", []):
        src_file = node.get("source_file", "")
        if src_file not in dirty_source_paths:
            clean_nodes.append(node)
            
    clean_links = []
    for link in existing_graph.get("links", []):
        src_file = link.get("source_file", "")
        if src_file not in dirty_source_paths:
            clean_links.append(link)

    # 2. Extract new nodes and edges for the modified files
    modified_absolute_paths = [workspace_path / f for f in modified_files if (workspace_path / f).exists()]
    
    new_extraction = extract_files(modified_absolute_paths, index_root=workspace_path)
    
    # 3. Merge clean parts with newly extracted parts
    merged_nodes = clean_nodes + new_extraction.get("nodes", [])
    
    # Format edges to match build serialization structure
    new_links = []
    for edge in new_extraction.get("edges", []):
        link_dict = {"source": edge["source"], "target": edge["target"]}
        link_dict.update({k: v for k, v in edge.items() if k not in ("source", "target")})
        new_links.append(link_dict)
        
    merged_links = clean_links + new_links

    return {
        "nodes": merged_nodes,
        "links": merged_links
    }
