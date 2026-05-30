"""
Widget Data Sync — App Group 컨테이너에 widget_data.json 동기화
메인 앱을 열지 않아도, launchd 와처 데몬이 이 함수를 호출하여 자동 갱신
"""
import json
import os
from pathlib import Path

GROUP_ID = "group.com.bongpark.SmartLLM"
DATA_FILE = "widget_data.json"


def sync_widget_data(workspace: str = None):
    """lessons/ 와 index.json을 읽어 App Group 컨테이너에 JSON으로 씀"""
    if workspace is None:
        workspace = str(Path.home() / ".gemini" / "antigravity" / "scratch" / "smart-llm")

    lessons_dir = os.path.join(workspace, "lessons")
    index_path = os.path.join(workspace, "smart-llm-out", "index.json")
    last_seen_path = os.path.join(workspace, ".widget_last_seen")

    # 1. Total files
    total_files = 0
    try:
        with open(index_path, "r") as f:
            index = json.load(f)
            total_files = len(index.get("doc_map", {}))
    except Exception:
        pass

    # 2. Lessons
    lessons = []
    try:
        for fname in os.listdir(lessons_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(lessons_dir, fname)
            mtime = os.path.getmtime(fpath)
            with open(fpath, "r") as f:
                content = f.read()

            # Parse title
            first_line = content.split("\n", 1)[0] if content else ""
            title = first_line.replace("# Lesson Learned: ", "").replace("# ", "").strip()

            # Parse tags
            tags = []
            for line in content.split("\n"):
                if "Context/Tags" in line:
                    parts = line.split("`")
                    tags = [parts[i] for i in range(1, len(parts), 2)]
                    break

            lessons.append({
                "filename": fname,
                "title": title,
                "timestamp": mtime,
                "tags": tags,
            })
    except Exception:
        pass

    lessons.sort(key=lambda x: x["timestamp"], reverse=True)

    # 3. Last seen
    last_seen = 0.0
    try:
        with open(last_seen_path, "r") as f:
            last_seen = float(f.read().strip())
    except Exception:
        pass

    new_count = sum(1 for l in lessons if l["timestamp"] > last_seen)

    # 4. Write to App Group container
    payload = {
        "totalFiles": total_files,
        "totalLessons": len(lessons),
        "newLessonsCount": new_count,
        "lessons": lessons,
        "lastUpdated": __import__("time").time(),
    }

    group_dir = os.path.join(Path.home(), "Library", "Group Containers", GROUP_ID)
    os.makedirs(group_dir, exist_ok=True)
    data_path = os.path.join(group_dir, DATA_FILE)

    with open(data_path, "w") as f:
        json.dump(payload, f, ensure_ascii=False)

    # /tmp fallback (샌드박스 위젯이 Group Containers를 못 읽을 경우 대비)
    tmp_dir = "/tmp/smartllm"
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, DATA_FILE)
    with open(tmp_path, "w") as f:
        json.dump(payload, f, ensure_ascii=False)

    return data_path
