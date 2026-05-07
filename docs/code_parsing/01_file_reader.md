# 📄 file_reader.py — Codebase Scanner

> **Location**: `backend/app/code_parsing/file_reader.py`
> **Purpose**: Walk a repository directory, filter relevant files, and read their raw content into memory.

---

## What Does It Do?

This is the **first module** in the pipeline. It takes a path to a repository on disk and returns a dictionary containing:
- The raw text content of every relevant source file
- The directory structure
- Metadata (languages detected, skipped files, etc.)

Think of it as a smart `find + cat` — it knows which files matter and which to skip.

---

## Public API

### `read_codebase(repo_path: str) → dict`

The only function you call from this module.

**Input**:
- `repo_path` — Absolute path to the repository root (e.g., `"/home/user/my-project"`)

**Output**: A dictionary with three keys:
```python
{
    "files": {
        "src/main.py": "import os\n...",       # filepath → raw content
        "src/auth.py": "class AuthService:\n...",
        "package.json": "{\"name\": ...}",
    },
    "structure": {
        "./":     ["main.py", "package.json"],  # root-level files
        "src/":   ["main.py", "auth.py"],       # files in src/
        "tests/": ["test_auth.py"],
    },
    "metadata": {
        "total_files": 42,
        "languages_detected": ["python", "javascript", "typescript"],
        "skipped_dirs": ["node_modules/", ".git/", "__pycache__/"],
        "skipped_large_files": ["data/big_dump.py"],
        "repo_root": "/absolute/path/to/repo"
    }
}
```

---

## How File Filtering Works

The module applies **three layers of filtering** to decide what to read:

### 1. Directory Filtering (Skip These Entirely)

These directories are **pruned** from the walk — `os.walk` won't even enter them:

```python
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv',
    'dist', 'build', '.next', 'coverage', 'qdrant_storage'
}
```

> **Why?** These contain generated code, dependencies, or binary artifacts — analyzing them would be noisy and slow.

### 2. File Type Filtering (Keep These)

A file is kept if it matches **any** of these criteria:

| Category | Rule | Examples |
|----------|------|----------|
| **Source files** | Extension is in `SOURCE_EXTENSIONS` | `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.go`, `.java`, `.rs`, `.rb`, `.php`, `.c`, `.cpp`, `.h` |
| **Config files** | At repo root AND (name in `CONFIG_NAMES` OR extension in `CONFIG_EXTENSIONS`) | `Dockerfile`, `.env`, `config.yaml`, `settings.toml` |
| **Dependency files** | Name exactly matches `DEP_FILES` | `requirements.txt`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml` |

> **Key detail**: Config files are only included if they're at the **root level** of the repo. A `config.yaml` inside `src/` would be skipped.

### 3. Size Guard

Files larger than **500KB** (`MAX_FILE_SIZE = 500 * 1024`) are skipped and logged in `skipped_large_files`.

---

## Language Detection

The module detects languages by mapping file extensions:

```python
EXTENSION_TO_LANGUAGE = {
    '.py': 'python',     '.js': 'javascript',   '.jsx': 'javascript',
    '.ts': 'typescript', '.tsx': 'typescript',   '.go': 'go',
    '.java': 'java',     '.rs': 'rust',          '.rb': 'ruby',
    '.php': 'php',       '.c': 'c',              '.cpp': 'cpp',
    '.h': 'cpp'
}
```

The `languages_detected` set in metadata tells downstream modules which parsers are needed.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `repo_path` is not a directory | Raises `ValueError` |
| File can't be decoded as UTF-8 | Skipped silently (logged as debug) |
| Permission denied on a file | Skipped, logged as error |
| File size can't be read | Skipped, logged as error |
| Any other read error | Skipped, logged as error |

The function **never crashes** on individual file errors — it logs them and moves on.

---

## Path Conventions

- All file paths in the output use **forward slashes** (`/`), even on Windows
- Paths are **relative** to `repo_path` (e.g., `"src/auth.py"`, not `"/home/user/project/src/auth.py"`)
- Structure keys end with `/` (e.g., `"src/"`, `"./"`)

---

## Internal Flow

```
read_codebase(repo_path)
    │
    ├── Validate repo_path is a directory
    │
    ├── os.walk(repo_path)
    │     │
    │     ├── For each directory:
    │     │     └── Remove SKIP_DIRS from dirs[] (prunes os.walk in-place)
    │     │
    │     └── For each file:
    │           ├── Check if source file / config file / dep file
    │           ├── Check file size < 500KB
    │           ├── Read content as UTF-8
    │           ├── Detect language from extension
    │           └── Add to files_content dict
    │
    └── Return {files, structure, metadata}
```

---

## Usage Example

```python
from app.code_parsing.file_reader import read_codebase

result = read_codebase("/path/to/my-project")

# How many files?
print(result["metadata"]["total_files"])  # 42

# What languages?
print(result["metadata"]["languages_detected"])  # ["python", "javascript"]

# Get a specific file's content
source = result["files"]["src/main.py"]
print(source[:100])  # First 100 chars
```
