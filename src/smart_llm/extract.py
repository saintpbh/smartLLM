"""AST (tree-sitter) & document structural extraction engine."""

from __future__ import annotations

import re
import json
from pathlib import Path
from tree_sitter import Language, Parser

# --- Tree-sitter Language Loader ---
def _get_language(ext: str) -> Language | None:
    """Return tree-sitter Language for a file extension, or None."""
    try:
        if ext == ".py":
            import tree_sitter_python
            return Language(tree_sitter_python.language())
        elif ext in (".ts",):
            import tree_sitter_typescript
            return Language(tree_sitter_typescript.language_typescript())
        elif ext in (".tsx",):
            import tree_sitter_typescript
            return Language(tree_sitter_typescript.language_tsx())
        elif ext in (".js", ".jsx", ".mjs"):
            import tree_sitter_javascript
            return Language(tree_sitter_javascript.language())
        elif ext == ".go":
            import tree_sitter_go
            return Language(tree_sitter_go.language())
        elif ext == ".rs":
            import tree_sitter_rust
            return Language(tree_sitter_rust.language())
        elif ext == ".java":
            import tree_sitter_java
            return Language(tree_sitter_java.language())
    except (ImportError, Exception):
        return None
    return None

def _sanitize_id(name: str) -> str:
    """Convert a name to a valid node ID component: lowercase, special chars to underscore."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower())

def _rel_path_slug(source_file: str | Path, index_root: str | Path | None) -> str:
    """Compute a relative path-based slug for a source file."""
    p = Path(source_file)
    rel: Path | None = None
    if index_root is not None:
        try:
            rel = p.resolve().relative_to(Path(index_root).resolve())
        except (ValueError, OSError):
            rel = None
    if rel is None:
        rel = p
    parts = tuple(part for part in rel.parts if part not in ("", "/", "\\"))
    if not parts:
        return _sanitize_id(p.stem) or "root"
    return "__".join(_sanitize_id(part) for part in parts)

def _make_canonical_id(
    source_file: str | Path,
    kind: str,
    entity_name: str = "",
    index_root: str | Path | None = None,
) -> str:
    """Build a path-based canonical node ID: {rel_path_slug}::{kind}::{local_slug}"""
    prefix = _rel_path_slug(source_file, index_root)
    kind_clean = _sanitize_id(kind) or "entity"
    local = _sanitize_id(entity_name) if entity_name else ""
    return f"{prefix}::{kind_clean}::{local}"

def _make_ref_id(target_name: str) -> str:
    """Build an unresolved cross-file reference ID."""
    return f"__unresolved__::ref::{_sanitize_id(target_name)}"

def _extract_text(node) -> str:
    """Get text content of a tree-sitter node."""
    return node.text.decode("utf-8", errors="ignore") if node.text else ""

def _find_identifier(node) -> str | None:
    """Find the first identifier child's text."""
    for c in node.children:
        if c.type in ("identifier", "name", "type_identifier"):
            return _extract_text(c)
    return None

# --- Node Categories ---
_FUNC_TYPES = {
    "function_definition", "function_declaration", "method_definition",
    "method_declaration", "arrow_function", "function_item", "impl_item",
    "function", "method"
}

_CLASS_TYPES = {
    "class_definition", "class_declaration", "struct_item", "class_specifier",
    "struct_specifier", "interface_declaration", "protocol_declaration"
}

_IMPORT_TYPES = {
    "import_statement", "import_from_statement", "import_declaration",
    "use_declaration", "require", "using_directive"
}

def _extract_imports(node) -> list[str]:
    """Extract imported module/symbol names."""
    targets = []
    for child in node.children:
        if child.type in ("dotted_name", "identifier", "scoped_identifier",
                          "qualified_name", "string", "name"):
            text = _extract_text(child)
            if text and text not in ("import", "from", "use", "require", "using"):
                targets.append(text)
    if node.type == "import_from_statement":
        for child in node.children:
            if child.type == "dotted_name":
                targets = [_extract_text(child)]
                break
    return targets

def _extract_calls(node) -> list[str]:
    """Recursively find all function call names in a subtree."""
    calls = []
    if node.type in ("call", "call_expression"):
        func = node.child_by_field_name("function")
        if func is None and node.children:
            func = node.children[0]
        if func:
            text = _extract_text(func)
            if "." in text:
                text = text.rsplit(".", 1)[-1]
            if text:
                calls.append(text)
    for child in node.children:
        calls.extend(_extract_calls(child))
    return calls

def _process_code_file(
    file_path: Path, lang: Language, index_root: Path | None = None
) -> tuple[list[dict], list[dict]]:
    """Process a single code file, extracting structural nodes and edges."""
    nodes: list[dict] = []
    edges: list[dict] = []

    try:
        code = file_path.read_bytes()
    except (OSError, IOError):
        return nodes, edges

    parser = Parser(lang)
    tree = parser.parse(code)
    root = tree.root_node
    source_file = str(file_path)

    def _cid(kind: str, name: str = "") -> str:
        return _make_canonical_id(source_file, kind, name, index_root)

    # Module node (file itself)
    module_id = _cid("module", file_path.stem)
    nodes.append({
        "id": module_id,
        "label": file_path.stem,
        "file_type": "code",
        "entity_type": "module",
        "source_file": source_file,
        "source_location": None,
    })

    defined_names: dict[str, str] = {}

    def visit_definitions(node, parent_class_id=None):
        for child in node.children:
            if child.type in _FUNC_TYPES:
                name = _find_identifier(child)
                if not name:
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        name = _extract_text(name_node)
                if not name:
                    continue

                kind = "method" if parent_class_id else "function"
                nid = _cid(kind, name)
                loc = f"L{child.start_point[0] + 1}"
                nodes.append({
                    "id": nid,
                    "label": name,
                    "file_type": "code",
                    "entity_type": kind,
                    "source_file": source_file,
                    "source_location": loc,
                })
                defined_names[name] = nid

                # contains relationship
                container = parent_class_id if parent_class_id else module_id
                edges.append({
                    "source": container,
                    "target": nid,
                    "relation": "contains",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": source_file,
                })

                # Function calls
                calls = _extract_calls(child)
                for call_name in calls:
                    edges.append({
                        "source": nid,
                        "target": _make_ref_id(call_name),
                        "relation": "calls",
                        "confidence": "EXTRACTED",
                        "confidence_score": 1.0,
                        "source_file": source_file,
                    })

            elif child.type in _CLASS_TYPES:
                name = _find_identifier(child)
                if not name:
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        name = _extract_text(name_node)
                if not name:
                    continue

                nid = _cid("class", name)
                loc = f"L{child.start_point[0] + 1}"
                nodes.append({
                    "id": nid,
                    "label": name,
                    "file_type": "code",
                    "entity_type": "class",
                    "source_file": source_file,
                    "source_location": loc,
                })
                defined_names[name] = nid

                edges.append({
                    "source": module_id,
                    "target": nid,
                    "relation": "contains",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": source_file,
                })

                # Recurse for class methods
                for body_child in child.children:
                    if body_child.type in ("block", "class_body", "declaration_list", "field_declaration_list"):
                        visit_definitions(body_child, parent_class_id=nid)

    visit_definitions(root)

    # Imports pass
    def visit_imports(node):
        for child in node.children:
            if child.type in _IMPORT_TYPES:
                targets = _extract_imports(child)
                for target in targets:
                    edges.append({
                        "source": module_id,
                        "target": _make_ref_id(target.split(".")[-1]),
                        "relation": "imports",
                        "confidence": "EXTRACTED",
                        "confidence_score": 1.0,
                        "source_file": source_file,
                    })
    visit_imports(root)

    return nodes, edges

# --- Markdown Structural Parsing ---
def _parse_markdown(
    file_path: Path, source_file: str, index_root: Path | None = None
) -> tuple[list[dict], list[dict]]:
    """Parse Markdown headers, links, and tags."""
    nodes: list[dict] = []
    edges: list[dict] = []
    
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, IOError):
        return nodes, edges

    def _cid(kind: str, name: str = "") -> str:
        return _make_canonical_id(source_file, kind, name, index_root)

    # Simple frontmatter strip
    meta = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
            # Simple frontmatter parsing
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")

    # Module node (File node)
    file_node_id = _cid("file", file_path.stem)
    nodes.append({
        "id": file_node_id,
        "label": file_path.stem,
        "file_type": "document",
        "entity_type": "file",
        "source_file": source_file,
        "source_location": None,
        "meta": meta
    })

    header_stack: list[tuple[int, str]] = []
    current_header_id = file_node_id

    for idx, line in enumerate(text.splitlines()):
        header_match = re.match(r"^(#{1,6})\s+(.+)", line)
        if header_match:
            depth = len(header_match.group(1))
            title = header_match.group(2).strip()
            slug = re.sub(r"[^a-z0-9_]", "_", title.lower()).strip("_")
            if not slug:
                continue
            
            node_id = _cid("header", slug)
            nodes.append({
                "id": node_id,
                "label": title,
                "file_type": "document",
                "entity_type": "header",
                "source_file": source_file,
                "source_location": f"L{idx + 1}",
            })

            # Contains relationship
            while header_stack and header_stack[-1][0] >= depth:
                header_stack.pop()
            
            parent_id = header_stack[-1][1] if header_stack else file_node_id
            edges.append({
                "source": parent_id,
                "target": node_id,
                "relation": "contains",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": source_file,
            })
            header_stack.append((depth, node_id))
            current_header_id = node_id
            continue

        # Wikilinks: [[link]]
        for m in re.finditer(r"\[\[([^\]]+)\]\]", line):
            target = m.group(1)
            edges.append({
                "source": current_header_id,
                "target": _make_ref_id(target),
                "relation": "references",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": source_file,
            })

    return nodes, edges

# --- Interface ---
def extract_files(
    files: list[Path], index_root: Path | None = None
) -> dict:
    """Interface to scan both code files and markdown files for structural graphs."""
    all_nodes: list[dict] = []
    all_edges: list[dict] = []

    for file_path in files:
        if not file_path.exists():
            continue
        ext = file_path.suffix.lower()

        # Try code parsing first
        lang = _get_language(ext)
        if lang is not None:
            nodes, edges = _process_code_file(file_path, lang, index_root=index_root)
            all_nodes.extend(nodes)
            all_edges.extend(edges)
        # Try document parsing
        elif ext == ".md":
            nodes, edges = _parse_markdown(file_path, str(file_path), index_root=index_root)
            all_nodes.extend(nodes)
            all_edges.extend(edges)

    return {
        "nodes": all_nodes,
        "edges": all_edges,
    }
