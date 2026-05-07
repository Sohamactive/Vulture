import os
import logging

try:
    from app.logger import get_logger
except ImportError:
    # Fallback when run directly as a script (sys.path lacks the backend/ root)
    def get_logger(name: str) -> logging.Logger:  # type: ignore[misc]
        return logging.getLogger(name)

# Configure logging - using getLogger without basicConfig for library compatibility
logger = get_logger(__name__)

# Constants for filtering
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv',
    'dist', 'build', '.next', 'coverage', 'qdrant_storage'
}

SOURCE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.java', '.rs', '.rb', '.php', '.c', '.cpp', '.h'
}

# Config files (root level only)
CONFIG_NAMES = {'Dockerfile', '.env'}
CONFIG_EXTENSIONS = {'.yaml', '.yml', '.toml', '.json'}

# Dependency files
DEP_FILES = {
    'requirements.txt', 'package.json', 'go.mod', 'Cargo.toml', 'pom.xml'
}

EXTENSION_TO_LANGUAGE = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.go': 'go',
    '.java': 'java',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.c': 'c',
    '.cpp': 'cpp',
    '.h': 'cpp'
}

MAX_FILE_SIZE = 500 * 1024  # 500KB

def read_codebase(repo_path: str) -> dict:
    """
    Reads the codebase at the given path and returns a dictionary with the files, 
    directory structure, and metadata.
    """
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        logger.error(f"Provided path is not a directory: {repo_path}")
        raise ValueError(f"Invalid repository path: {repo_path}")

    logger.info(f"Scanning repository: {repo_path}")

    files_content = {}
    structure = {}
    languages_detected = set()
    skipped_dirs = set()
    skipped_large_files = []
    total_files = 0

    for root, dirs, filenames in os.walk(repo_path):
        # Determine relative path from repo root
        rel_root = os.path.relpath(root, repo_path)
        if rel_root == '.':
            rel_root = ''

        # Skip specified directories and filter them in-place for os.walk
        original_dirs = list(dirs)
        for d in original_dirs:
            if d in SKIP_DIRS:
                rel_skip_path = os.path.join(rel_root, d) if rel_root else d
                skipped_dirs.add(rel_skip_path.replace(os.sep, '/') + '/')
                dirs.remove(d)

        valid_files_in_dir = []

        for filename in filenames:
            file_path = os.path.join(root, filename)
            # Use forward slashes for relative paths as per requirements
            rel_file_path = os.path.join(rel_root, filename) if rel_root else filename
            rel_file_path = rel_file_path.replace(os.sep, '/')
            
            _, ext = os.path.splitext(filename)
            ext_lower = ext.lower()

            is_valid = False
            
            # 1. Source files
            if ext_lower in SOURCE_EXTENSIONS:
                is_valid = True
            # 2. Config files (root level only)
            elif rel_root == '' and (filename in CONFIG_NAMES or ext_lower in CONFIG_EXTENSIONS):
                is_valid = True
            # 3. Dependency files
            elif filename in DEP_FILES:
                is_valid = True

            if not is_valid:
                continue

            # Max file size guard
            try:
                if os.path.getsize(file_path) > MAX_FILE_SIZE:
                    logger.warning(f"Skipping large file: {rel_file_path}")
                    skipped_large_files.append(rel_file_path)
                    continue
            except OSError as e:
                logger.error(f"Could not get size for {rel_file_path}: {e}")
                continue

            # Read file raw content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    files_content[rel_file_path] = content
                    valid_files_in_dir.append(filename)
                    total_files += 1
                    
                    # Detect language
                    lang = EXTENSION_TO_LANGUAGE.get(ext_lower)
                    if lang:
                        languages_detected.add(lang)
                    elif filename == 'Dockerfile':
                        languages_detected.add('dockerfile')
                    
            except UnicodeDecodeError:
                logger.debug(f"Skipping binary file: {rel_file_path}")
                continue
            except PermissionError:
                logger.error(f"Permission denied: {rel_file_path}")
                continue
            except Exception as e:
                logger.error(f"Error reading {rel_file_path}: {e}")
                continue

        if valid_files_in_dir:
            # Format structure key as "dir/" as requested, using forward slashes
            if rel_root == '':
                structure_key = './'
            else:
                structure_key = rel_root.replace(os.sep, '/') + '/'
            structure[structure_key] = valid_files_in_dir

    output = {
        "files": files_content,
        "structure": structure,
        "metadata": {
            "total_files": total_files,
            "languages_detected": sorted(list(languages_detected)),
            "skipped_dirs": sorted(list(skipped_dirs)),
            "skipped_large_files": skipped_large_files,
            "repo_root": repo_path
        }
    }

    logger.info(f"Scan complete. Found {total_files} files.")
    return output

if __name__ == "__main__":
    # Setup logging for the test run
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    import json
    import sys
    
    test_path = sys.argv[1] if len(sys.argv) > 1 else "."
    try:
        result = read_codebase(test_path)
        # Print a summary instead of full content for the test
        print(json.dumps({
            "file content summary" : {k: f"{len(v)} chars" for k, v in result["files"].items()},
            "metadata": result["metadata"],
            "structure": result["structure"],
            "files_count": len(result["files"])
        }, indent=2))
        
    except Exception as e:
        logger.exception("Failed to read codebase")
