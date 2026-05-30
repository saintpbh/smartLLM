"""Stage 1: Reference Ingestion & Context Bootstrapper."""

from __future__ import annotations

import re
import json
from pathlib import Path

def parse_c_header_defines(file_path: Path) -> dict[str, str]:
    """Parse `#define REGISTER_NAME 0xADDRESS` definitions from C/C++ headers."""
    register_map = {}
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}

    # Regex to capture #define REG_NAME 0xVAL or standard decimal value
    pattern = re.compile(r"#\s*define\s+([\w_]+)\s+((?:0x[0-9a-fA-F]+)|(?:\d+))")
    for line in content.splitlines():
        match = pattern.search(line)
        if match:
            reg_name = match.group(1)
            reg_val = match.group(2)
            register_map[reg_name] = reg_val
            
    return register_map


def ingest_reference_material(workspace_path: Path, ref_path: Path) -> dict:
    """Ingest reference headers or datasheets and merge them into the search index."""
    workspace_path = Path(workspace_path).resolve()
    ref_path = Path(ref_path).resolve()
    
    out_dir = workspace_path / "smart-llm-out"
    out_dir.mkdir(exist_ok=True)
    index_file = out_dir / "index.json"
    
    # Load existing search index
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        except Exception:
            index_data = {"doc_map": {}}
    else:
        index_data = {"doc_map": {}}
        
    doc_map = index_data.setdefault("doc_map", {})
    
    ingested_files = 0
    registers_found = {}
    
    # Resolve target files (single file or directory scan)
    targets = []
    if ref_path.is_file():
        targets.append(ref_path)
    elif ref_path.is_dir():
        # Scan recursively for headers, txt, md
        for ext in ("*.h", "*.hpp", "*.txt", "*.md"):
            targets.extend(ref_path.rglob(ext))
            
    for target in targets:
        rel_key = f"reference/{target.name}"
        ext = target.suffix.lower()
        
        # 1. Parse C-header defines as structured hardware map
        if ext in (".h", ".hpp"):
            reg_map = parse_c_header_defines(target)
            if reg_map:
                registers_found.update(reg_map)
                # Save as structured text inside doc_map
                header_text = f"# Reference Header: {target.name}\n"
                header_text += "## Parsed Register Maps\n"
                for r_name, r_val in sorted(reg_map.items()):
                    header_text += f"- **{r_name}**: `{r_val}`\n"
                doc_map[rel_key] = header_text
                ingested_files += 1
                
        # 2. General reference datasheets
        elif ext in (".txt", ".md"):
            try:
                text = target.read_text(encoding="utf-8", errors="ignore")
                doc_map[rel_key] = f"# Reference Datasheet: {target.name}\n\n{text}"
                ingested_files += 1
            except OSError:
                pass
                
    # Save the updated register map as metadata inside the ledger or separate index section
    if registers_found:
        index_data["register_map"] = registers_found
        
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
        
    return {
        "status": "success",
        "ingested_files": ingested_files,
        "registers_count": len(registers_found)
    }
