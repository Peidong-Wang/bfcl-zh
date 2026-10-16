"""Read-only resources for either a source checkout or an installed wheel."""
from __future__ import annotations
import json
from importlib.resources import files
from pathlib import Path

def data_root() -> Path:
    packaged=Path(str(files('multilingual_bfcl').joinpath('data','benchmarks')))
    if packaged.is_dir(): return packaged
    checkout=Path(__file__).resolve().parents[2]/'data/benchmarks'
    if checkout.is_dir(): return checkout
    raise FileNotFoundError('Benchmark resources are missing; reinstall the wheel')

def benchmark_path(category: str,locale: str,benchmark: str) -> Path:
    if category!='bfcl_multiple':
        raise ValueError('Packaged release supports only bfcl_multiple')
    for part in (locale,benchmark):
        if not part or '/' in part or '\\' in part or part in {'.','..'}:
            raise ValueError('Dataset identifiers must be simple names')
    path=data_root()/category/locale/f'{benchmark}.jsonl'
    if not path.is_file(): raise FileNotFoundError(path)
    return path

def load_jsonl(path: Path) -> list[dict]:
    rows=[]
    for n,line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip(): continue
        record=json.loads(line)
        if not isinstance(record,dict): raise ValueError(f'{path}:{n}: expected an object')
        rows.append(record)
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError(f'{path}: missing/duplicate string IDs')
    return rows


def full_suite_path() -> Path:
    """Native BFCL v4 layout; scoring answers and prerequisite resources included."""
    path=data_root()/'bfcl_full'/'zh-CN'
    if not path.is_dir(): raise FileNotFoundError('Full-suite data is missing')
    return path


def full_category_path(category: str) -> Path:
    if not category or any(c not in 'abcdefghijklmnopqrstuvwxyz_' for c in category):
        raise ValueError('Category must be a lowercase BFCL category name')
    path=full_suite_path()/f'BFCL_v4_{category}.json'
    if not path.is_file(): raise FileNotFoundError(path)
    return path
