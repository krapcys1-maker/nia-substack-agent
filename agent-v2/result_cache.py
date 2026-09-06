"""Content-addressed cache. Old, malformed or expired entries are never reused."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    default=str).encode('utf-8')).hexdigest()


def read(path: Path, max_age: float):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        age = time.time() - data['at']
        return data['value'] if 0 <= age <= max_age else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write(path: Path, value):
    write_json(path, {'at': time.time(), 'value': value})


def write_json(path: Path, value):
    """Replace a JSON document atomically, keeping the prior file on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def code_fingerprint(root: Path):
    paths = sorted([*root.glob('*.py'), *root.glob('prompts/*.md')])
    return digest([(str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths])
