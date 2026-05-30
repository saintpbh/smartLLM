"""Debounced background filesystem event watcher (Zero-CPU Watcher)."""

from __future__ import annotations

import time
import os
import sys
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from smart_llm.detect import EXT_MAP, SKIP_DIRS, SKIP_DATA_FILES
from smart_llm.sqlite_ledger import raise_alert

class DebouncedIndexScheduler:
    """Schedules indexing operations with a debounced delay of 3 seconds to conserve CPU."""
    
    def __init__(self, workspace_path: Path, delay: float = 3.0):
        self.workspace_path = Path(workspace_path).resolve()
        self.delay = delay
        self.timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def trigger_update(self, filepath: str) -> None:
        """Schedules/reschedules the background compilation process."""
        with self._lock:
            if self.timer:
                self.timer.cancel()
                
            self.timer = threading.Timer(self.delay, self._run_compilation, args=[filepath])
            self.timer.daemon = True
            self.timer.start()

    def _run_compilation(self, filepath: str) -> None:
        """Executes incremental ingest and agents sync in the background thread."""
        print(f"\n💤 [Zero-CPU Watcher] Idle delay elapsed. Compiling memory incrementally...")
        
        # Save change info to SQLite alerts
        try:
            raise_alert(
                self.workspace_path,
                "file_modified",
                {"file": str(Path(filepath).relative_to(self.workspace_path))}
            )
        except Exception:
            pass

        # Trigger internal CLI handlers in-process rather than spinning heavy sub-shells
        from smart_llm.cli import handle_ingest, handle_sync_agents
        
        class MockArgs:
            def __init__(self, path=".", git=True, workspace="."):
                self.path = path
                self.git = git
                self.workspace = workspace
                
        try:
            ingest_args = MockArgs(path=str(self.workspace_path), git=True)
            handle_ingest(ingest_args)
            
            sync_args = MockArgs(workspace=str(self.workspace_path))
            handle_sync_agents(sync_args)
            
            # Widget 데이터 자동 동기화 (App Group 컨테이너)
            try:
                from smart_llm.widget_sync import sync_widget_data
                sync_widget_data(str(self.workspace_path))
                print("📡 [Zero-CPU Watcher] Widget data synced to App Group container.")
            except Exception as widget_err:
                print(f"⚠️ [Zero-CPU Watcher] Widget sync skipped: {widget_err}")
            
            print("🚀 [Zero-CPU Watcher] Background Sync Complete. Memory rules updated.\n")
        except Exception as e:
            print(f"❌ [Zero-CPU Watcher] Background compile error: {e}", file=sys.stderr)


class CognitiveFileEventHandler(FileSystemEventHandler):
    """Watches for code/doc modifications and forwards them to the debounced scheduler."""
    
    def __init__(self, scheduler: DebouncedIndexScheduler):
        self.scheduler = scheduler
        super().__init__()

    def _should_process(self, filepath_str: str) -> bool:
        # Check skipped directories
        parts = Path(filepath_str).parts
        if any(p in SKIP_DIRS for p in parts):
            return False
            
        ext = os.path.splitext(filepath_str)[1].lower()
        category = EXT_MAP.get(ext)
        if category is None:
            return False
            
        if category == "data" and Path(filepath_str).name.lower() in SKIP_DATA_FILES:
            return False
            
        return True

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            self.scheduler.trigger_update(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            self.scheduler.trigger_update(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            self.scheduler.trigger_update(event.src_path)


def start_live_watcher(workspace_path: Path) -> None:
    """Start the live watchdog daemon."""
    workspace_path = Path(workspace_path).resolve()
    print(f"🧠 [SMART LLM] Initiating Zero-CPU Watcher Daemon on: {workspace_path}")
    print(f"   Listening silently... Incremental compilation debounced by 3 seconds of idle time.")
    
    # Initialize DB ledger
    from smart_llm.sqlite_ledger import init_ledger
    init_ledger(workspace_path)
    
    scheduler = DebouncedIndexScheduler(workspace_path)
    event_handler = CognitiveFileEventHandler(scheduler)
    
    observer = Observer()
    observer.schedule(event_handler, str(workspace_path), recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n💤 Stopping Watcher Daemon...")
        observer.stop()
    observer.join()
