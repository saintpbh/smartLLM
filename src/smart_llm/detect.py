"""Workspace file scanner and category mapping."""

from __future__ import annotations

import os
from pathlib import Path

SKIP_DIRS = {
    "node_modules", ".git", "dist", "out", "__pycache__", "build",
    ".next", ".venv", "venv", ".tox", "egg-info",
    ".github", "smart-llm-out", "mindvault-out", "worktrees",
    "coverage", ".nyc_output", ".cache", ".turbo",
    "ios", "android", "Pods", ".expo", ".dart_tool",
    "macos", "windows", "linux", "web",
    ".obsidian", ".trash", ".stfolder", ".stversions",
}

EXT_MAP: dict[str, str] = {}

_CODE_EXTS = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs",
    ".go", ".rs", ".java", ".swift", ".kt", ".kts",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".rb", ".cs", ".scala", ".php", ".lua",
)
for _e in _CODE_EXTS:
    EXT_MAP[_e] = "code"

for _e in (".md", ".txt", ".rst", ".docx", ".xlsx", ".pptx"):
    EXT_MAP[_e] = "document"

for _e in (".json", ".yaml", ".yml"):
    EXT_MAP[_e] = "data"

SKIP_DATA_FILES = {
    "package.json", "package-lock.json", "tsconfig.json", "tsconfig.node.json",
    "jsconfig.json", "tslint.json", "eslint.json", ".eslintrc.json",
    ".prettierrc.json", ".prettierrc.yaml", ".prettierrc.yml",
    "babel.config.json", "jest.config.json", "vitest.config.json",
    "postcss.config.json", "tailwind.config.json",
    "composer.json", "composer.lock", "Pipfile.lock", "poetry.lock",
    "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    ".swcrc", ".babelrc", "nx.json", "turbo.json",
    "launch.json", "settings.json", "extensions.json",
    "pubspec.lock", "Podfile.lock", "Gemfile.lock",
    "app.json", "eas.json", "expo.json",
    "renovate.json", "dependabot.yml",
}

BINARY_DOCUMENT_EXTS = frozenset({".docx", ".xlsx", ".pptx", ".pdf"})

for _e in (".pdf",):
    EXT_MAP[_e] = "paper"

for _e in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
    EXT_MAP[_e] = "image"


def detect_files(path: Path) -> dict:
    """Scan workspace and classify files into categories while skipping irrelevant files/folders."""
    files: dict[str, list[str]] = {
        "code": [],
        "document": [],
        "paper": [],
        "image": [],
        "data": []
    }
    total_words = 0
    skipped_dirs = 0

    for dirpath, dirnames, filenames in os.walk(path):
        # Filter directories in-place to prevent walking down skipped folders
        original_count = len(dirnames)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        skipped_dirs += original_count - len(dirnames)

        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            category = EXT_MAP.get(ext)
            if category is None:
                continue

            if category == "data" and fname.lower() in SKIP_DATA_FILES:
                continue

            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, path)
            files[category].append(rel_path)

            if category in ("code", "document") and ext not in BINARY_DOCUMENT_EXTS:
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    total_words += len(content.split())
                except (OSError, IOError):
                    pass

    total_files = sum(len(v) for v in files.values())
    return {
        "files": files,
        "total_files": total_files,
        "total_words": total_words,
        "skipped_dirs": skipped_dirs,
    }
# File scan category identifier

