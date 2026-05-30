"""Command Line Interface for SMART LLM."""

from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from smart_llm.detect import detect_files
from smart_llm.extract import extract_files
from smart_llm.build import build_graph, serialize_graph
from smart_llm.cluster import cluster_graph, calculate_cohesion
from smart_llm.query import query_codebase
from smart_llm.git_diff import get_git_changes, incremental_update_graph
from smart_llm.sync import sync_agents_file
from smart_llm.consolidate import run_sleep_consolidation

def make_wiki_document(
    cid: int,
    members: list[str],
    cohesion: float,
    graph_data: dict
) -> str:
    """Generate a clean, structured Markdown wiki page for a community."""
    lines = [
        f"# Community Memory {cid}",
        f"**Cohesion Score**: {cohesion:.3f}",
        "",
        "## Component Members",
    ]
    for member in members:
        # Simplify IDs to short labels
        label = member.split("::")[-1] or member
        kind = member.split("::")[1] if "::" in member else "module"
        lines.append(f"- **{label}** ({kind}) — `[[{member}]]`")
        
    lines.append("")
    lines.append("## Structural Connections")
    
    # Identify inside-outside connections
    member_set = set(members)
    connections_found = False
    
    for link in graph_data.get("links", []):
        src = link.get("source", "")
        tgt = link.get("target", "")
        rel = link.get("relation", "relates")
        
        src_label = src.split("::")[-1] or src
        tgt_label = tgt.split("::")[-1] or tgt
        
        if src in member_set and tgt not in member_set:
            lines.append(f"- `[[{src_label}]]` --[{rel}]--> `[[{tgt_label}]]` (External Dependency)")
            connections_found = True
        elif tgt in member_set and src not in member_set:
            lines.append(f"- `[[{src_label}]]` --[{rel}]--> `[[{tgt_label}]]` (Required By External)")
            connections_found = True

    if not connections_found:
        lines.append("*This community is self-contained. No external call boundaries found.*")
        
    return "\n".join(lines) + "\n"


def handle_ingest(args):
    """Command handler for 'ingest'."""
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"Error: Path '{path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    out_dir = path / "smart-llm-out"
    graph_file = out_dir / "graph.json"
    
    is_incremental = args.git
    
    if is_incremental and not graph_file.exists():
        print("⚠️  Warning: Existing graph.json not found. Falling back to full ingestion.")
        is_incremental = False

    if is_incremental:
        print(f"🧠 [SMART LLM] Initializing Incremental Ingestion via Git diff for: {path}")
        print("⚡ Step 1: Evaluating workspace file changes...")
        changes = get_git_changes(path)
        
        mod_count = len(changes["modified"])
        del_count = len(changes["deleted"])
        print(f"   Changes detected: {mod_count} files modified/added, {del_count} files deleted.")
        
        if mod_count == 0 and del_count == 0:
            print("🚀 Workspace is already fully synchronized. No updates needed.")
            return

        with open(graph_file, "r", encoding="utf-8") as f:
            existing_graph = json.load(f)

        print("⚡ Step 2: Extracting incremental AST changes...")
        merged_serialization = incremental_update_graph(existing_graph, changes, path)
        
        print("⚡ Step 3: Recompiling Knowledge Graph...")
        G = build_graph(merged_serialization)
        graph_data = serialize_graph(G)
        
    else:
        print(f"🧠 [SMART LLM] Initializing Full Ingestion for project at: {path}")
        
        # 1. Detect Files
        print("⚡ Step 1: Scanning directory structure...")
        scan_res = detect_files(path)
        code_files = [path / f for f in scan_res["files"]["code"]]
        doc_files = [path / f for f in scan_res["files"]["document"]]
        all_files = code_files + doc_files
        print(f"   Found {len(code_files)} code files and {len(doc_files)} markdown files.")

        # 2. Extract AST and Document Structure
        print("⚡ Step 2: Parsing AST and Markdown documents...")
        extraction = extract_files(all_files, index_root=path)

        # 3. Build Graph
        print("⚡ Step 3: Compiling Hierarchical Knowledge Graph...")
        G = build_graph(extraction)
        graph_data = serialize_graph(G)
        
    # Create Output Directory
    out_dir.mkdir(exist_ok=True)
    
    with open(graph_file, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)
    print(f"   Serialized Knowledge Graph to: {graph_file}")

    # 4. Modularity Community Detection
    print("⚡ Step 4: Resolving System Architecture (Modularity Clustering)...")
    communities = cluster_graph(G)
    cohesions = calculate_cohesion(G, communities)
    
    # 5. Wiki Generation
    print("⚡ Step 5: Generating Semantic Wiki...")
    wiki_dir = out_dir / "wiki"
    wiki_dir.mkdir(exist_ok=True)
    
    doc_map: dict[str, str] = {}
    
    for cid, members in communities.items():
        doc_content = make_wiki_document(cid, members, cohesions[cid], graph_data)
        wiki_file = wiki_dir / f"community_{cid}.md"
        wiki_file.write_text(doc_content, encoding="utf-8")
        
        rel_wiki_path = f"wiki/community_{cid}.md"
        doc_map[rel_wiki_path] = doc_content
        
    print(f"   Compiled {len(communities)} modular community wiki articles under: {wiki_dir}")

    # 6. Index Generation (FAISS / TF-IDF Vector Index)
    print("⚡ Step 6: Compiling Dense & Sparse Search Index...")
    index_file = out_dir / "index.json"
    
    # Save the doc_map for indexing, preserving register_map if exists
    existing_index = {}
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                existing_index = json.load(f)
        except Exception:
            pass
            
    index_data = {
        "doc_map": doc_map,
        "scan_metadata": {
            "total_files": len(doc_map),
        }
    }
    if "register_map" in existing_index:
        index_data["register_map"] = existing_index["register_map"]
        
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
        
    print(f"🚀 Ingestion successful! Workspace is mapped and memorized.")
    print(f"   Use `smart-llm query \"your question\"` to retrieve context.")


def handle_query(args):
    """Command handler for 'query'."""
    path = Path(args.workspace).resolve()
    out_dir = path / "smart-llm-out"
    index_file = out_dir / "index.json"
    graph_file = out_dir / "graph.json"
    
    if not index_file.exists():
        print(f"Error: Search index not found at '{index_file}'. Please run 'smart-llm ingest' first.", file=sys.stderr)
        sys.exit(1)
        
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)
        
    doc_map = index_data.get("doc_map", {})
    
    graph_data = None
    if graph_file.exists():
        with open(graph_file, "r", encoding="utf-8") as f:
            graph_data = json.load(f)

    print(f"🔎 [SMART LLM] Processing Query: \"{args.question}\"")
    result = query_codebase(args.question, doc_map, graph=graph_data)
    
    print("-" * 50)
    print(f"Gate Status   : {result['gateway_status']}")
    print(f"Matches Found : {len(result.get('search_results', []))}")
    for doc_id, score in result.get('search_results', []):
        print(f"  - {doc_id} (RRF Score: {score:.4f})")
    print("-" * 50)
    
    if result["context"]:
        print("💡 [Context Injected into AI Workspace]")
        print(result["context"])
    else:
        print("💤 [No Context Injected (No matches or classified as general)]")


def handle_sync_agents(args):
    """Command handler for 'sync-agents'."""
    path = Path(args.workspace).resolve()
    print(f"🧠 [SMART LLM] Syncing Workspace Memory into Antigravity Rule system...")
    try:
        agents_file = sync_agents_file(path)
        print(f"🚀 Successfully compiled and synchronized memory into Antigravity: {agents_file}")
    except Exception as e:
        print(f"❌ Error during sync: {e}", file=sys.stderr)
        sys.exit(1)


def handle_consolidate(args):
    """Command handler for 'consolidate' (Sleep-Phase Consolidation)."""
    path = Path(args.workspace).resolve()
    print(f"💤 [SMART LLM] Initiating Sleep-Phase Memory Consolidation...")
    res = run_sleep_consolidation(path)
    
    if res["status"] == "success":
        print("-" * 50)
        print(f"Nodes Pruned      : {res['nodes_pruned']}")
        print(f"Edges Pruned      : {res['edges_pruned']}")
        print(f"Total Communities : {res['total_communities']}")
        print("-" * 50)
        print(f"🚀 Sleep-Phase consolidation succeeded! Memory is now clean and optimized.")
    else:
        print(f"❌ Consolidation failed: {res.get('message')}", file=sys.stderr)
        sys.exit(1)


def handle_watch(args):
    """Command handler for 'watch' (Zero-CPU filesystem watcher daemon)."""
    path = Path(args.workspace).resolve()
    from smart_llm.watcher import start_live_watcher
    try:
        start_live_watcher(path)
    except Exception as e:
        print(f"❌ Error starting watcher daemon: {e}", file=sys.stderr)
        sys.exit(1)


def handle_bootstrap(args):
    """Command handler for 'bootstrap'."""
    workspace = Path(args.workspace).resolve()
    ref_path = Path(args.ref_path).resolve()
    print(f"🔌 [SMART LLM] Bootstrapping reference materials from: {ref_path}")
    from smart_llm.bootstrap import ingest_reference_material
    try:
        res = ingest_reference_material(workspace, ref_path)
        print(f"🚀 Bootstrap complete! Ingested {res['ingested_files']} reference files, parsed {res['registers_count']} registers.")
    except Exception as e:
        print(f"❌ Error during bootstrap: {e}", file=sys.stderr)
        sys.exit(1)


def handle_learn(args):
    """Command handler for 'learn'."""
    workspace = Path(args.workspace).resolve()
    print(f"📝 [SMART LLM] Recording hard-learned debug lesson...")
    from smart_llm.learn import record_lesson
    try:
        res = record_lesson(workspace, args.error, args.resolution, args.context)
        print(f"🚀 Success! Lesson recorded and saved into: {res['lesson_file']}")
        
        # Trigger dynamic sync to update AGENTS.md immediately
        from smart_llm.sync import sync_agents_file
        sync_agents_file(workspace)
        print(f"⚡ Synchronized new lessons to AGENTS.md.")
    except Exception as e:
        print(f"❌ Error during learn: {e}", file=sys.stderr)
        sys.exit(1)


def handle_verify(args):
    """Command handler for 'verify'."""
    workspace = Path(args.workspace).resolve()
    print(f"🛡️ [SMART LLM] Running pre-emptive hardware & register constraint verification...")
    from smart_llm.verify import scan_hardware_constraints
    try:
        violations = scan_hardware_constraints(workspace)
        if violations:
            print("-" * 50)
            print(f"⚠️  {len(violations)} Hardware Constraint Violations Detected:")
            for v in violations:
                print(f"  - [{v['error_type']}] in {v['file']}:{v['line']} -> {v['symbol']}")
                print(f"    Guide: {v['guideline']}")
            print("-" * 50)
            sys.exit(1)
        else:
            print("🚀 Success! All hardware static AST constraint validations passed.")
    except Exception as e:
        print(f"❌ Error during verification: {e}", file=sys.stderr)
        sys.exit(1)


def handle_dashboard(args):
    """Command handler for 'dashboard' (Starts the HTTP server and opens GUI)."""
    workspace = Path(args.workspace).resolve()
    port = int(args.port)
    
    from http.server import HTTPServer
    import webbrowser
    from smart_llm.server import DashboardHandler
    
    DashboardHandler.workspace_path = workspace
    
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardHandler)
    
    url = f"http://localhost:{port}"
    print(f"🧠 [SMART LLM] Starting Cognitive Dashboard Server on: {url}")
    print(f"🚀 Opening web browser dashboard...")
    
    # Automatically open default browser in background
    try:
        webbrowser.open_new_tab(url)
    except Exception:
        pass
        
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n💤 Stopping Dashboard Server...")
        httpd.server_close()


def handle_widget(args):
    """Command handler for 'widget' (Starts the native macOS floating desktop widget)."""
    workspace = Path(args.workspace).resolve()
    print(f"🧠 [SMART LLM] Initializing Native macOS Desktop Widget...")
    
    swift_bin = workspace / "smart-llm-out" / "SMART_LLM_Widget"
    if swift_bin.exists():
        import subprocess
        print(f"🍏 Starting Apple-recommended Native Cocoa Widget App...")
        try:
            # Run the compiled native Swift app in background
            subprocess.Popen([str(swift_bin)])
            print("🚀 Native macOS Widget is now running on your desktop. Drag it anywhere!")
            return
        except Exception as e:
            print(f"⚠️ Failed to launch native Swift binary: {e}. Falling back to Tkinter...")
            
    print(f"💡 Double-click the widget to close it safely. Drag it anywhere!")
    from smart_llm.widget_app import start_widget_app
    try:
        start_widget_app(workspace)
    except Exception as e:
        print(f"❌ Error starting native widget app: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="SMART LLM: Semantic Memory & Architecture Retrieval Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest workspace and build memory index")
    ingest_parser.add_argument("path", nargs="?", default=".", help="Root path of the project to scan")
    ingest_parser.add_argument("--git", action="store_true", help="Perform incremental indexing using Git diff")

    # Query command
    query_parser = subparsers.add_parser("query", help="Retrieve smart memory context for a query")
    query_parser.add_argument("question", help="Question to retrieve relevant memory for")
    query_parser.add_argument("--workspace", default=".", help="Path to indexed project workspace")

    # Sync-agents command
    sync_parser = subparsers.add_parser("sync-agents", help="Synchronize memory rules into AGENTS.md / GEMINI.md")
    sync_parser.add_argument("--workspace", default=".", help="Path to indexed project workspace")

    # Consolidate command
    consolidate_parser = subparsers.add_parser("consolidate", help="Perform Sleep-Phase memory consolidation")
    consolidate_parser.add_argument("--workspace", default=".", help="Path to indexed project workspace")

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Start the background filesystem watcher daemon")
    watch_parser.add_argument("--workspace", default=".", help="Path to watch")

    # Bootstrap command
    bootstrap_parser = subparsers.add_parser("bootstrap", help="Ingest custom hardware headers and datasheets")
    bootstrap_parser.add_argument("ref_path", help="Path to reference headers or datasheets")
    bootstrap_parser.add_argument("--workspace", default=".", help="Path to project workspace")

    # Learn command
    learn_parser = subparsers.add_parser("learn", help="Record a post-mortem lesson to prevent repeating mistakes")
    learn_parser.add_argument("--error", required=True, help="Description of the error or bug resolved")
    learn_parser.add_argument("--resolution", required=True, help="Detailed resolution strategy or correct code")
    learn_parser.add_argument("--context", default="general", help="Comma-separated tags (e.g. gpio, stm32, spi)")
    learn_parser.add_argument("--workspace", default=".", help="Path to project workspace")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Run pre-emptive static hardware constraint checks")
    verify_parser.add_argument("--workspace", default=".", help="Path to project workspace")

    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Start the interactive real-time cognitive web dashboard")
    dashboard_parser.add_argument("--port", default="8000", help="Port to run the dashboard server on")
    dashboard_parser.add_argument("--workspace", default=".", help="Path to project workspace")

    # Widget command
    widget_parser = subparsers.add_parser("widget", help="Start the native macOS floating desktop widget")
    widget_parser.add_argument("--workspace", default=".", help="Path to project workspace")

    args = parser.parse_args()

    if args.command == "ingest":
        handle_ingest(args)
    elif args.command == "query":
        handle_query(args)
    elif args.command == "sync-agents":
        handle_sync_agents(args)
    elif args.command == "consolidate":
        handle_consolidate(args)
    elif args.command == "watch":
        handle_watch(args)
    elif args.command == "bootstrap":
        handle_bootstrap(args)
    elif args.command == "learn":
        handle_learn(args)
    elif args.command == "verify":
        handle_verify(args)
    elif args.command == "dashboard":
        handle_dashboard(args)
    elif args.command == "widget":
        handle_widget(args)

if __name__ == "__main__":
    main()
