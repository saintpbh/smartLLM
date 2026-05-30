"""Stage 2: Post-Mortem Lesson Recorder & Consolidation."""

from __future__ import annotations

import re
import time
from pathlib import Path

def record_lesson(
    workspace_path: Path,
    error_summary: str,
    resolution_details: str,
    context_tags: str
) -> dict:
    """Record a debug lesson as a persistent markdown rule inside the lessons database."""
    workspace_path = Path(workspace_path).resolve()
    lessons_dir = workspace_path / "lessons"
    lessons_dir.mkdir(exist_ok=True)
    
    timestamp = int(time.time())
    lesson_file = lessons_dir / f"lesson_{timestamp}.md"
    
    tags_list = [t.strip() for t in context_tags.split(",") if t.strip()]
    formatted_tags = ", ".join(f"`{t}`" for t in tags_list)
    
    content = f"""# Lesson Learned: {error_summary[:60]}
- **Context/Tags**: {formatted_tags}
- **Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}

## 🛑 Resolved Error
{error_summary}

## 💡 Successful Resolution
{resolution_details}

---
*안티그라비티 에이전트 가이드: 관련 작업 진행 시 이 실수를 참조하여 동일한 토큰 낭비 및 오작동 문제를 절대 반복하지 마십시오.*
"""
    
    lesson_file.write_text(content, encoding="utf-8")
    
    return {
        "status": "success",
        "lesson_file": str(lesson_file.relative_to(workspace_path)),
        "timestamp": timestamp
    }


def compile_lessons_widget(workspace_path: Path) -> str:
    """Read all persistent lessons and format them into a premium rule block for AGENTS.md."""
    workspace_path = Path(workspace_path).resolve()
    lessons_dir = workspace_path / "lessons"
    
    if not lessons_dir.exists():
        return ""
        
    lesson_files = sorted(lessons_dir.glob("lesson_*.md"), reverse=True)
    if not lesson_files:
        return ""
        
    lines = [
        "## 📝 PERSISTENT HARD-LEARNED LESSONS (실패 방지 지식 원장) 📝",
        "*경고: 과거 동일 작업 도메인에서 발생했던 결함 및 해결 노하우입니다. 에이전트들은 다음 해결 전략을 코딩 시작 전에 반드시 복기하십시오.*",
        ""
    ]
    
    for f in lesson_files[:5]:  # Capture latest 5 lessons to maintain strict token discipline
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
            
        # Parse components from the markdown file
        title_match = re.search(r"^# Lesson Learned:\s*(.*?)$", text, re.MULTILINE)
        tags_match = re.search(r"-\s*\*\*Context/Tags\*\*:\s*(.*?)$", text, re.MULTILINE)
        error_match = re.search(r"## 🛑 Resolved Error\n(.*?)(?=\n\n##|$)", text, re.DOTALL)
        res_match = re.search(r"## 💡 Successful Resolution\n(.*?)(?=\n\n---|$)", text, re.DOTALL)
        
        title = title_match.group(1).strip() if title_match else "Hardware Debug Lesson"
        tags = tags_match.group(1).strip() if tags_match else "`general`"
        error = error_match.group(1).strip() if error_match else ""
        res = res_match.group(1).strip() if res_match else ""
        
        lines.append(f"### 🛡️ Lesson: {title}")
        lines.append(f"- **영향 영역**: {tags}")
        if error:
            lines.append(f"- **과거 오류**: *\"{error[:150]}...\"*")
        if res:
            lines.append(f"- **해결 전략**: **{res}**")
        lines.append("")
        
    return "\n".join(lines)
