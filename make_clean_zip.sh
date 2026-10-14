#!/usr/bin/env bash
# ==============================================================================
# StudyMind - Clean Zip Archive Generator
# Creates SMA_clean.zip excluding secrets, caches, and local databases
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OUTPUT_ZIP="SMA_clean.zip"

echo "Creating clean archive: ${OUTPUT_ZIP}..."

# Remove previous archive if present
if [ -f "$OUTPUT_ZIP" ]; then
    rm -f "$OUTPUT_ZIP"
fi

# Use zip command if available, otherwise fall back to Python zipfile
if command -v zip >/dev/null 2>&1; then
    zip -r "$OUTPUT_ZIP" . \
        -x ".env" \
        -x "*.env.local" \
        -x "*/__pycache__/*" \
        -x "__pycache__/*" \
        -x "*.pyc" \
        -x "*.pyo" \
        -x "*/.pytest_cache/*" \
        -x ".pytest_cache/*" \
        -x ".git/*" \
        -x "*/.git/*" \
        -x "data/studymind.db" \
        -x "$OUTPUT_ZIP"
else
    # Cross-platform fallback using Python
    PYTHON_CMD="python"
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    fi

    $PYTHON_CMD -c "
import os, zipfile

output_zip = '$OUTPUT_ZIP'
exclude_dirs = {'__pycache__', '.pytest_cache', '.git', '.venv', 'venv'}
exclude_exact_files = {'.env', 'SMA_clean.zip'}

def is_excluded(path_str):
    normalized = path_str.replace('\\\\', '/').strip('/')
    parts = normalized.split('/')
    for part in parts:
        if part in exclude_dirs:
            return True
        if part.endswith('.pyc') or part.endswith('.pyo'):
            return True
    filename = parts[-1]
    if filename in exclude_exact_files:
        return True
    if normalized == 'data/studymind.db':
        return True
    if filename.startswith('.env') and filename != '.env.example':
        return True
    return False

added_count = 0
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, '.')
            if not is_excluded(rel_path):
                zf.write(full_path, rel_path)
                added_count += 1

print(f'Packaged {added_count} files into {output_zip}')
"
fi

echo "Successfully built ${OUTPUT_ZIP}"
