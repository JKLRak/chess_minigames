#!/usr/bin/env python3
"""
Bundle the Chess Puzzles project for LLM ingestion (Gemini, Claude, GPT) and distribution.
Generates:
  1. chess_project_bundle.md - Single structured markdown file with project tree and all code.
  2. chess_project.zip       - Clean zip archive containing only relevant project files.
"""

import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BUNDLE_MD_PATH = ROOT_DIR / "chess_project_bundle.md"
ZIP_PATH = ROOT_DIR / "chess_project.zip"

EXCLUDE_DIRS = {
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".git",
    ".system_generated",
    ".vite",
    ".vite-temp",
    ".idea",
    ".vscode",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".log",
    ".zip",
    ".tar",
    ".gz",
}

EXCLUDE_FILES = {
    "chess_project_bundle.md",
    "chess_project.zip",
    "package-lock.json",
    "uv.lock",
}

# Text extensions included in the Markdown bundle
CODE_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".css": "css",
    ".html": "html",
    ".json": "json",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".md": "markdown",
}

# Special filenames included in Markdown bundle
SPECIAL_TEXT_FILES = {
    "Dockerfile": "dockerfile",
    "docker-compose.yml": "yaml",
}


def should_skip_dir(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def should_include_in_zip(path: Path) -> bool:
    if should_skip_dir(path):
        return False
    if path.name in EXCLUDE_FILES:
        return False
    if path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return False
    return True


def should_include_in_bundle(path: Path) -> bool:
    if not should_include_in_zip(path):
        return False
    if path.name in SPECIAL_TEXT_FILES:
        return True
    ext = path.suffix.lower()
    if ext in CODE_EXTENSIONS:
        # Skip piece SVG files and binary assets in markdown text dump
        return True
    return False


def get_language(path: Path) -> str:
    if path.name in SPECIAL_TEXT_FILES:
        return SPECIAL_TEXT_FILES[path.name]
    return CODE_EXTENSIONS.get(path.suffix.lower(), "text")


def build_ascii_tree(dir_path: Path, prefix: str = "") -> list[str]:
    """Recursively generate an ASCII tree of the project files included in the bundle."""
    lines = []
    
    entries = []
    try:
        raw_entries = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return lines

    for entry in raw_entries:
        if entry.is_dir():
            if entry.name not in EXCLUDE_DIRS:
                # Only include directory if it has included contents
                sub_tree = build_ascii_tree(entry)
                if sub_tree:
                    entries.append(entry)
        else:
            if should_include_in_zip(entry):
                entries.append(entry)

    count = len(entries)
    for idx, entry in enumerate(entries):
        is_last = (idx == count - 1)
        connector = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            lines.extend(build_ascii_tree(entry, prefix + child_prefix))
        else:
            lines.append(f"{prefix}{connector}{entry.name}")

    return lines


def create_markdown_bundle(bundle_files: list[Path], tree_lines: list[str]) -> int:
    """Generate the full markdown codebase bundle."""
    lines = [
        "# Chess Puzzles Codebase Export\n",
        "A full-stack chess web application featuring:\n",
        "- **Daily Gauntlet**: 4 progressive levels of missing piece deduction from active master games.\n",
        "- **Guess the Move**: Fast-paced streak challenge picking the move played in 2000+ Elo games.\n",
        "- **Backend**: FastAPI, SQLAlchemy async, asyncpg, PostgreSQL, python-chess, httpx.\n",
        "- **Frontend**: React 19, TypeScript, Vite, custom SVG piece rendering, zero bloated dependencies.\n\n",
        "## Project Structure\n\n",
        "```text\n",
        "chess-project/\n",
    ]
    for tree_line in tree_lines:
        lines.append(f"{tree_line}\n")
    lines.append("```\n\n---\n\n")

    for file_path in bundle_files:
        rel_path = file_path.relative_to(ROOT_DIR)
        lang = get_language(file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            content = f"// Error reading file: {e}"

        lines.append(f"## File: `{rel_path}`\n\n")
        lines.append(f"```{lang}\n{content}\n```\n\n---\n\n")

    full_text = "".join(lines)
    BUNDLE_MD_PATH.write_text(full_text, encoding="utf-8")
    return len(full_text.encode("utf-8"))


def create_zip_archive(zip_files: list[Path]) -> int:
    """Generate the clean zip archive."""
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in zip_files:
            rel_path = file_path.relative_to(ROOT_DIR)
            zf.write(file_path, arcname=rel_path)
    return ZIP_PATH.stat().st_size


def collect_all_files(dir_path: Path) -> list[Path]:
    """Recursively collect all files, skipping excluded directories."""
    files: list[Path] = []
    try:
        entries = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return files

    for entry in entries:
        if entry.is_dir():
            if entry.name not in EXCLUDE_DIRS:
                files.extend(collect_all_files(entry))
        elif entry.is_file():
            files.append(entry)
    return files


def main():
    print(f"Scanning codebase in: {ROOT_DIR}")

    all_files = collect_all_files(ROOT_DIR)
    all_files.sort(key=lambda p: str(p.relative_to(ROOT_DIR)))

    zip_files = [p for p in all_files if should_include_in_zip(p)]
    bundle_files = [p for p in all_files if should_include_in_bundle(p)]

    # Generate tree
    tree_lines = build_ascii_tree(ROOT_DIR)

    # 1. Markdown bundle
    bundle_bytes = create_markdown_bundle(bundle_files, tree_lines)
    print(f"✓ Created {BUNDLE_MD_PATH.name} ({len(bundle_files)} files, {bundle_bytes:,} bytes)")

    # 2. Zip archive
    zip_bytes = create_zip_archive(zip_files)
    print(f"✓ Created {ZIP_PATH.name} ({len(zip_files)} files, {zip_bytes:,} bytes)")


if __name__ == "__main__":
    main()
