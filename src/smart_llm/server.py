"""Stage 4: Real-Time Dynamic Cognitive Dashboard Server."""

from __future__ import annotations

import sys
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

class DashboardHandler(BaseHTTPRequestHandler):
    """Base request handler serving HTML and API endpoints for the SMART LLM dashboard."""
    
    workspace_path = Path(".")
    
    def log_message(self, format, *args):
        # Override to suppress default HTTP console logging to keep console neat
        pass

    def _send_json(self, data: dict, status_code: int = 200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # 1. API: Retrieve real-time compiled knowledge graph
        if path == "/api/graph":
            graph_file = self.workspace_path / "smart-llm-out" / "graph.json"
            if graph_file.exists():
                try:
                    with open(graph_file, "r", encoding="utf-8") as f:
                        graph_data = json.load(f)
                    self._send_json(graph_data)
                except Exception as e:
                    self._send_json({"error": f"Failed to load graph: {e}"}, 500)
            else:
                self._send_json({"error": "Graph not indexed yet. Please run 'smart-llm ingest'."}, 404)
            return

        # 2. API: Retrieve active SQLite ledger state and alerts
        elif path == "/api/ledger":
            try:
                from smart_llm.sqlite_ledger import get_active_alerts, get_state
                alerts = get_active_alerts(self.workspace_path, limit=10)
                sync_state = get_state(self.workspace_path, "agents_rules_sync")
                
                self._send_json({
                    "alerts": alerts,
                    "sync_state": sync_state or {}
                })
            except Exception as e:
                self._send_json({"error": f"Failed to query SQLite ledger: {e}"}, 500)
            return

        # 3. API: Retrieve hard-learned debug lessons catalog
        elif path == "/api/lessons":
            lessons_dir = self.workspace_path / "lessons"
            lessons = []
            if lessons_dir.exists():
                for f in sorted(lessons_dir.glob("lesson_*.md"), reverse=True):
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        lessons.append({
                            "filename": f.name,
                            "content": content
                        })
                    except OSError:
                        pass
            self._send_json({"lessons": lessons})
            return

        # 3b. API: Widget Stats Consolidated Endpoint for WidgetKit
        elif path == "/api/widget_stats":
            try:
                # Count files
                total_files = 0
                index_file = self.workspace_path / "smart-llm-out" / "index.json"
                if index_file.exists():
                    try:
                        with open(index_file, "r", encoding="utf-8") as f:
                            index_data = json.load(f)
                            total_files = len(index_data.get("doc_map", {}))
                    except Exception:
                        pass
                
                # Fetch alerts
                from smart_llm.sqlite_ledger import get_active_alerts
                alerts = get_active_alerts(self.workspace_path, limit=1)
                alerts_count = len(get_active_alerts(self.workspace_path, limit=100)) # Count total recent alerts
                
                active_alert = "None"
                if alerts:
                    alert = alerts[0]
                    # Format standard alert details
                    details = alert.get("details", {})
                    symbol = details.get("symbol", "")
                    error_type = alert.get("alert_type", "Warning")
                    active_alert = f"[{error_type}] {symbol}: {details.get('guideline', 'Violation detected')}"
                
                self._send_json({
                    "total_files": total_files,
                    "alerts_count": alerts_count,
                    "active_alert": active_alert
                })
            except Exception as e:
                self._send_json({"error": f"Failed to load widget stats: {e}"}, 500)
            return


        # 4. GUI: Serve Embedded Premium Dashboard HTML/CSS/JS page
        elif path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            dashboard_html = get_dashboard_html()
            self.wfile.write(dashboard_html.encode("utf-8"))
            return

        # 5. GUI: Serve Embedded Native macOS-style Widget HTML
        elif path == "/widget":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            widget_html = get_widget_html()
            self.wfile.write(widget_html.encode("utf-8"))
            return

        # Catch-all
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")


def get_dashboard_html() -> str:
    """Return the complete embedded single-page premium HTML/CSS/JS dashboard source."""
    return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMART LLM - Real-Time Cognitive Dashboard</title>
    
    <!-- Premium Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    
    <!-- D3.js CDN for force-directed graph visualization -->
    <script src="https://d3js.org/d3.v7.min.js"></script>

    <style>
        :root {
            --bg-color: #08090f;
            --panel-bg: rgba(14, 16, 26, 0.65);
            --border-color: rgba(255, 255, 255, 0.08);
            --glow-blue: #00d2ff;
            --glow-green: #39ff14;
            --glow-amber: #ffaa00;
            --glow-violet: #bd00ff;
            --text-primary: #f0f3fa;
            --text-secondary: #8f9bb3;
            --font-main: 'Inter', sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
            --font-outfit: 'Outfit', sans-serif;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: var(--font-main);
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Ambient glowing background */
        body::before {
            content: '';
            position: absolute;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(0, 210, 255, 0.05) 0%, rgba(0,0,0,0) 70%);
            top: -200px;
            left: -200px;
            z-index: -1;
            pointer-events: none;
        }

        body::after {
            content: '';
            position: absolute;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(189, 0, 255, 0.05) 0%, rgba(0,0,0,0) 70%);
            bottom: -200px;
            right: -200px;
            z-index: -1;
            pointer-events: none;
        }

        /* Header Navigation */
        header {
            height: 70px;
            border-bottom: 1px solid var(--border-color);
            background: rgba(8, 9, 15, 0.8);
            backdrop-filter: blur(12px);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 30px;
            z-index: 10;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-circle {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--glow-blue), var(--glow-violet));
            box-shadow: 0 0 15px rgba(0, 210, 255, 0.4);
            animation: pulse 2s infinite alternate;
        }

        .logo h1 {
            font-family: var(--font-outfit);
            font-weight: 800;
            font-size: 22px;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #ffffff, var(--glow-blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo span {
            font-size: 10px;
            font-family: var(--font-mono);
            color: var(--glow-blue);
            border: 1px solid rgba(0, 210, 255, 0.3);
            padding: 2px 6px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }

        /* Stats Grid */
        .stats-container {
            display: flex;
            gap: 20px;
        }

        .stat-badge {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            padding: 6px 14px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }

        .stat-val {
            font-family: var(--font-mono);
            font-weight: 700;
            color: var(--glow-blue);
        }

        /* Main Workspace Layout */
        .workspace {
            flex: 1;
            display: grid;
            grid-template-columns: 320px 1fr 360px;
            height: calc(100vh - 70px);
            position: relative;
        }

        /* Panels Shared Styling */
        .side-panel {
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
            z-index: 5;
        }

        .side-panel.right {
            border-right: none;
            border-left: 1px solid var(--border-color);
        }

        .panel-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .panel-header h2 {
            font-family: var(--font-outfit);
            font-size: 16px;
            font-weight: 600;
            letter-spacing: 0.2px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }

        /* Left Panel Log & Active Alerts */
        .led-active {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--glow-green);
            box-shadow: 0 0 8px var(--glow-green);
            display: inline-block;
        }

        .led-active.idle {
            background-color: var(--glow-amber);
            box-shadow: 0 0 8px var(--glow-amber);
        }

        .alert-item {
            background: rgba(255,255,255,0.02);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
            font-size: 13px;
            transition: all 0.2s ease;
        }

        .alert-item:hover {
            border-color: rgba(0, 210, 255, 0.2);
            background: rgba(0, 210, 255, 0.02);
        }

        .alert-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }

        .alert-type {
            font-family: var(--font-mono);
            font-weight: 700;
            color: var(--glow-amber);
        }

        .alert-time {
            font-size: 11px;
            color: var(--text-secondary);
        }

        .alert-file {
            font-family: var(--font-mono);
            color: var(--text-primary);
            word-break: break-all;
        }

        /* Central Visualization Screen */
        .graph-screen {
            position: relative;
            background: radial-gradient(circle at center, #0e101a 0%, #06070b 100%);
            height: 100%;
            width: 100%;
        }

        #knowledge-svg {
            width: 100%;
            height: 100%;
            cursor: grab;
        }

        #knowledge-svg:active {
            cursor: grabbing;
        }

        /* Graph Elements Tooltips and Styling */
        .node {
            stroke: rgba(0,0,0,0.4);
            stroke-width: 1.5px;
            transition: r 0.2s ease;
        }

        .link {
            stroke: rgba(255, 255, 255, 0.12);
            stroke-opacity: 0.6;
            stroke-width: 1.5px;
            transition: stroke 0.2s ease, stroke-opacity 0.2s ease;
        }

        .node-label {
            font-family: var(--font-mono);
            font-size: 10px;
            fill: var(--text-secondary);
            pointer-events: none;
            transition: opacity 0.2s ease, fill 0.2s ease;
        }

        /* Controls Floating Box */
        .graph-controls {
            position: absolute;
            bottom: 24px;
            left: 24px;
            background: rgba(14, 16, 26, 0.85);
            border: 1px solid var(--border-color);
            backdrop-filter: blur(12px);
            border-radius: 8px;
            padding: 10px;
            display: flex;
            gap: 8px;
        }

        .btn-control {
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            width: 32px;
            height: 32px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            transition: all 0.2s;
        }

        .btn-control:hover {
            background: var(--glow-blue);
            color: #000;
            border-color: var(--glow-blue);
        }

        /* Right Panel Inspector & Lessons Wiki */
        .inspector-placeholder {
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: var(--text-secondary);
            padding: 40px;
        }

        .inspector-placeholder svg {
            color: rgba(255,255,255,0.1);
            margin-bottom: 16px;
        }

        .detail-card {
            background: rgba(255,255,255,0.02);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .detail-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }

        .detail-val {
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 12px;
            word-break: break-all;
        }

        .detail-val.mono {
            font-family: var(--font-mono);
            font-size: 13px;
        }

        .drawer-section {
            border-top: 1px solid var(--border-color);
            padding-top: 16px;
            margin-top: 16px;
        }

        .section-title {
            font-family: var(--font-outfit);
            font-size: 14px;
            font-weight: 600;
            color: var(--glow-blue);
            margin-bottom: 10px;
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 10px rgba(0, 210, 255, 0.3); }
            100% { box-shadow: 0 0 22px rgba(0, 210, 255, 0.6); }
        }
        
        .lesson-bubble {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .lesson-bubble:hover {
            border-color: var(--glow-violet);
            background: rgba(189, 0, 255, 0.03);
        }
        .lesson-title {
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
        }
    </style>
</head>
<body>

    <header>
        <div class="logo">
            <div class="logo-circle"></div>
            <div>
                <h1>SMART LLM</h1>
            </div>
            <span>COGNITIVE OS v0.1.0</span>
        </div>
        <div class="stats-container">
            <div class="stat-badge">
                <span>Code Nodes:</span>
                <span class="stat-val" id="stat-code">0</span>
            </div>
            <div class="stat-badge">
                <span>Relations:</span>
                <span class="stat-val" id="stat-rels">0</span>
            </div>
            <div class="stat-badge">
                <span>Modularity Communities:</span>
                <span class="stat-val" id="stat-comms" style="color: var(--glow-violet);">0</span>
            </div>
        </div>
    </header>

    <div class="workspace">
        <!-- Left Side: Live Log and SQLite Memory Alerts -->
        <div class="side-panel">
            <div class="panel-header">
                <h2><span class="led-active"></span> Live State Alerts</h2>
                <span style="font-size: 11px; font-family: var(--font-mono); color: var(--text-secondary);">WATCHING</span>
            </div>
            <div class="panel-content" id="alerts-list">
                <div style="color: var(--text-secondary); text-align: center; margin-top: 40px; font-size: 13px;">
                    대기 중... 파일 수정 감시 활성화
                </div>
            </div>
        </div>

        <!-- Center Area: Force-Directed Knowledge Graph Visualizer -->
        <div class="graph-screen">
            <svg id="knowledge-svg"></svg>
            
            <div class="graph-controls">
                <button class="btn-control" onclick="zoomIn()">+</button>
                <button class="btn-control" onclick="zoomOut()">-</button>
                <button class="btn-control" onclick="resetZoom()">⟲</button>
            </div>
        </div>

        <!-- Right Side: Node Inspector and Lessons Catalog -->
        <div class="side-panel right">
            <div class="panel-header">
                <h2 id="right-panel-title">📚 Lessons Wiki</h2>
            </div>
            <div class="panel-content" id="right-panel-content">
                <!-- Fallback Lessons Catalog view -->
                <div class="inspector-placeholder" id="lessons-placeholder">
                    <svg width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"></path>
                    </svg>
                    <p style="font-size: 14px; font-weight: 500; margin-bottom: 8px;">Persistent Lessons</p>
                    <p style="font-size: 12px; color: var(--text-secondary);">노드를 선택하여 상세 명세를 보거나 아래 실패 방지 지식을 확인하십시오.</p>
                </div>
                <div id="lessons-list"></div>
            </div>
        </div>
    </div>

    <script>
        let graphData = null;
        let svg = d3.select("#knowledge-svg");
        let width = document.querySelector(".graph-screen").clientWidth;
        let height = document.querySelector(".graph-screen").clientHeight;
        
        let simulation = null;
        let gContainer = svg.append("g");
        let zoom = d3.zoom().on("zoom", (e) => gContainer.attr("transform", e.transform));
        
        svg.call(zoom);

        // Load all data
        async function loadData() {
            try {
                const [graphRes, ledgerRes, lessonsRes] = await Promise.all([
                    fetch('/api/graph'),
                    fetch('/api/ledger'),
                    fetch('/api/lessons')
                ]);

                const graph = await graphRes.json();
                const ledger = await ledgerRes.json();
                const lessons = await lessonsRes.json();

                graphData = graph;
                updateStats(graph);
                renderGraph(graph);
                renderAlerts(ledger.alerts);
                renderLessons(lessons.lessons);
            } catch (err) {
                console.error("데이터 로딩 실패:", err);
            }
        }

        function updateStats(graph) {
            const nodes = graph.nodes || [];
            const links = graph.links || [];
            
            const codeNodes = nodes.filter(n => n.file_type === 'code').length;
            document.getElementById("stat-code").textContent = codeNodes;
            document.getElementById("stat-rels").textContent = links.length;
            
            // Unique community count
            const comms = new Set(nodes.map(n => n.community).filter(c => c !== undefined));
            document.getElementById("stat-comms").textContent = comms.size;
        }

        function renderAlerts(alerts) {
            const alertsList = document.getElementById("alerts-list");
            alertsList.innerHTML = "";
            
            if (!alerts || alerts.length === 0) {
                alertsList.innerHTML = `<div style="color: var(--text-secondary); text-align: center; margin-top: 40px; font-size: 13px;">수신 대기 중...</div>`;
                return;
            }

            alerts.forEach(alert => {
                const item = document.createElement("div");
                item.className = "alert-item";
                
                const time = new Date(alert.created_at).toLocaleTimeString();
                
                item.innerHTML = `
                    <div class="alert-header">
                        <span class="alert-type">${alert.alert_type}</span>
                        <span class="alert-time">${time}</span>
                    </div>
                    <div class="alert-file">${alert.details.file || JSON.stringify(alert.details)}</div>
                `;
                alertsList.appendChild(item);
            });
        }

        function renderLessons(lessons) {
            const lessonsList = document.getElementById("lessons-list");
            lessonsList.innerHTML = "";
            
            if (!lessons || lessons.length === 0) {
                return;
            }

            lessons.forEach(l => {
                const card = document.createElement("div");
                card.className = "lesson-bubble";
                card.onclick = () => showLessonDetail(l);
                
                const shortTitle = l.content.split('\\n')[0].replace('#', '').trim();
                
                card.innerHTML = `
                    <div class="lesson-title">${shortTitle}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">영역: ${l.filename}</div>
                `;
                lessonsList.appendChild(card);
            });
        }

        function showLessonDetail(lesson) {
            const titleEl = document.getElementById("right-panel-title");
            const contentEl = document.getElementById("right-panel-content");
            
            titleEl.innerHTML = `🛡️ Lesson Details`;
            contentEl.innerHTML = `
                <button class="btn-control" onclick="restoreLessonsList()" style="width:auto; padding: 0 12px; margin-bottom:16px;">← Back to List</button>
                <div class="detail-card">
                    <pre style="white-space: pre-wrap; font-family: var(--font-main); font-size: 13px; line-height: 1.5; color: var(--text-primary);">${lesson.content}</pre>
                </div>
            `;
        }

        function restoreLessonsList() {
            loadData();
            document.getElementById("right-panel-title").innerHTML = "📚 Lessons Wiki";
        }

        // Color mapping for modularity communities
        const colors = [
            "#00d2ff", "#bd00ff", "#39ff14", "#ffaa00", 
            "#ff0055", "#00ffcc", "#ffea00", "#ff00aa"
        ];
        function getNodeColor(d) {
            if (d.file_type === 'placeholder') return "#333745";
            if (d.file_type === 'document') return "#a0a5b5";
            const commId = d.community || 0;
            return colors[commId % colors.length];
        }

        function renderGraph(graph) {
            gContainer.selectAll("*").remove();

            const nodes = graph.nodes.map(d => ({...d}));
            const links = graph.links.map(d => ({...d}));

            // Force Simulation
            simulation = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(links).id(d => d.id).distance(80))
                .force("charge", d3.forceManyBody().strength(-120))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collision", d3.forceCollide().radius(22));

            // Render Links
            const link = gContainer.append("g")
                .attr("class", "links")
                .selectAll("line")
                .data(links)
                .join("line")
                .attr("class", "link");

            // Render Nodes
            const node = gContainer.append("g")
                .attr("class", "nodes")
                .selectAll("circle")
                .data(nodes)
                .join("circle")
                .attr("class", "node")
                .attr("r", d => d.file_type === 'code' ? 12 : 8)
                .attr("fill", getNodeColor)
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended))
                .on("click", (event, d) => inspectNode(d))
                .on("mouseover", function(e, d) {
                    d3.select(this).attr("r", d => d.file_type === 'code' ? 16 : 11);
                })
                .on("mouseout", function(e, d) {
                    d3.select(this).attr("r", d => d.file_type === 'code' ? 12 : 8);
                });

            // Node Labels
            const label = gContainer.append("g")
                .attr("class", "labels")
                .selectAll("text")
                .data(nodes)
                .join("text")
                .attr("class", "node-label")
                .attr("dy", 4)
                .attr("dx", 16)
                .text(d => d.label || d.id.split('::').pop());

            simulation.on("tick", () => {
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);

                label
                    .attr("x", d => d.x)
                    .attr("y", d => d.y);
            });

            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }

            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }

            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }
        }

        // Node detail inspector
        function inspectNode(node) {
            const titleEl = document.getElementById("right-panel-title");
            const contentEl = document.getElementById("right-panel-content");
            
            titleEl.innerHTML = `🔍 Node Inspector`;
            
            const relPath = node.source_file || node.id.split('::')[0].replace('__', '/');
            const cohesion = node.cohesion ? node.cohesion.toFixed(3) : "N/A";
            
            let contents = `
                <button class="btn-control" onclick="restoreLessonsList()" style="width:auto; padding: 0 12px; margin-bottom:16px;">← Back to Lessons</button>
                
                <div class="detail-card">
                    <div class="detail-label">Entity Label</div>
                    <div class="detail-val" style="font-weight: 700; color: var(--glow-blue);">${node.label || node.id.split('::').pop()}</div>
                    
                    <div class="detail-label">File Type</div>
                    <div class="detail-val"><span style="text-transform: capitalize; color: var(--glow-green);">${node.file_type}</span></div>
                    
                    <div class="detail-label">Relative Path</div>
                    <div class="detail-val mono">${relPath}</div>
                    
                    <div class="detail-label">Modularity Community</div>
                    <div class="detail-val">ID: ${node.community !== undefined ? node.community : 'None'} (Cohesion: ${cohesion})</div>
                </div>
            `;
            
            // Add contract / API checks if applicable
            if (node.file_type === 'code') {
                contents += `
                    <div class="drawer-section">
                        <div class="section-title">🔮 Proactive Prediction</div>
                        <p style="font-size:12px; color:var(--text-secondary); line-height:1.4;">
                            이 파일 수정 시 가중 다익스트라 최단 경로 연산에 의거하여 결합도가 가장 높은 다음 파일들이 선제적으로 프롬프트 캐시에 장전됩니다.
                        </p>
                    </div>
                `;
            }
            
            contentEl.innerHTML = contents;
        }

        // Zoom Functions
        function zoomIn() { svg.transition().call(zoom.scaleBy, 1.3); }
        function zoomOut() { svg.transition().call(zoom.scaleBy, 0.7); }
        function resetZoom() { svg.transition().call(zoom.transform, d3.zoomIdentity); }

        // Start loading and set interval to keep updated in real-time
        loadData();
        setInterval(loadData, 3000); // Dynamic real-time query every 3 seconds!

        window.onresize = () => {
            width = document.querySelector(".graph-screen").clientWidth;
            height = document.querySelector(".graph-screen").clientHeight;
            if (simulation) {
                simulation.force("center", d3.forceCenter(width / 2, height / 2)).restart();
            }
        };
    </script>
</body>
</html>
"""

def get_widget_html() -> str:
    """Return the macOS-style semi-transparent glassmorphic desktop widget HTML page."""
    return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMART LLM Widget</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&family=Outfit:wght@600;800&display=swap" rel="stylesheet">

    <style>
        :root {
            --glow-green: #39ff14;
            --glow-blue: #00d2ff;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background: transparent;
            font-family: 'Inter', sans-serif;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            width: 100vw;
        }

        /* Glassmorphic Widget Container */
        .widget {
            width: 170px;
            height: 170px;
            background: rgba(30, 35, 55, 0.45);
            backdrop-filter: blur(25px) saturate(180%);
            -webkit-backdrop-filter: blur(25px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 28px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            color: #ffffff;
            position: relative;
        }

        /* Ambient subtle inner glow */
        .widget::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%);
            pointer-events: none;
            z-index: 1;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 2;
        }

        .title {
            font-family: 'Outfit', sans-serif;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.8px;
            color: rgba(255, 255, 255, 0.5);
            text-transform: uppercase;
        }

        /* Pulsing green status LED */
        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: var(--glow-green);
            box-shadow: 0 0 6px var(--glow-green);
            animation: pulse 2s infinite alternate;
        }

        .main {
            display: flex;
            flex-direction: column;
            justify-content: center;
            z-index: 2;
            margin-top: -6px;
        }

        .count {
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            font-size: 38px;
            line-height: 1.0;
            letter-spacing: -1px;
            background: linear-gradient(to right, #ffffff, var(--glow-blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(0, 210, 255, 0.15);
        }

        .label {
            font-size: 10px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.6);
            margin-top: 2px;
        }

        .footer {
            z-index: 2;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .sync-label {
            font-size: 8px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            color: rgba(255, 255, 255, 0.3);
        }

        .sync-file {
            font-family: 'JetBrains Mono', monospace;
            font-size: 8px;
            color: rgba(0, 210, 255, 0.7);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            width: 100%;
        }

        @keyframes pulse {
            0% { opacity: 0.4; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>

    <div class="widget">
        <div class="header">
            <div class="title">SMART LLM</div>
            <div class="status-dot" id="led"></div>
        </div>
        <div class="main">
            <div class="count" id="stat-count">0</div>
            <div class="label">지식 모듈 축적됨</div>
        </div>
        <div class="footer">
            <div class="sync-label">LATEST ACTIVE EVENT</div>
            <div class="sync-file" id="stat-file">WAITING</div>
        </div>
    </div>

    <script>
        async function fetchWidgetData() {
            try {
                const [graphRes, ledgerRes] = await Promise.all([
                    fetch('/api/graph'),
                    fetch('/api/ledger')
                ]);

                const graph = await graphRes.json();
                const ledger = await ledgerRes.json();

                // Calculate code nodes count
                const nodes = graph.nodes || [];
                const codeNodes = nodes.filter(n => n.file_type === 'code').length;
                document.getElementById("stat-count").textContent = codeNodes;

                // Set latest file from alerts
                const alerts = ledger.alerts || [];
                if (alerts.length > 0) {
                    const latest = alerts[0];
                    const filename = latest.details.file || "UPDATED";
                    const shortName = filename.split('/').pop();
                    document.getElementById("stat-file").textContent = shortName.toUpperCase();
                    
                    // Brief flash animation on LED when sync happens
                    const led = document.getElementById("led");
                    led.style.boxShadow = "0 0 12px #39ff14";
                    setTimeout(() => {
                        led.style.boxShadow = "0 0 6px #39ff14";
                    }, 500);
                } else {
                    document.getElementById("stat-file").textContent = "STABLE";
                }
            } catch (err) {
                console.error("Widget data fetch failed:", err);
            }
        }

        fetchWidgetData();
        setInterval(fetchWidgetData, 2000); // Poll every 2 seconds for high responsiveness!
    </script>
</body>
</html>
"""
