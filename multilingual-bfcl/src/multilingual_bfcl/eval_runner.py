"""Strict scoring against selected inline answers, using a pinned BFCL checker."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from .datasets import benchmark_path, load_jsonl
from ._vendor.bfcl.constants.enums import Language
from ._vendor.bfcl.eval_checker.ast_eval.ast_checker import ast_checker

def decode_calls(record: dict) -> list[dict]:
    """Accept decoded calls or OpenAI tool_calls. Never execute model expressions."""
    raw = record.get('calls', record.get('tool_calls', record.get('result')))
    if not isinstance(raw,list):
        raise ValueError('Expected calls/tool_calls/result as a list')
    decoded=[]
    for call in raw:
        if not isinstance(call,dict):
            raise ValueError('Each call must be an object')
        if 'function' in call:
            function=call['function']
            name=function['name']
            args=function['arguments']
            args=json.loads(args) if isinstance(args,str) else args
        elif len(call)==1:
            name,args=next(iter(call.items()))
        else:
            raise ValueError('Decoded calls must contain exactly one function')
        if not isinstance(name,str) or not isinstance(args,dict):
            raise ValueError('Function name must be a string; arguments an object')
        decoded.append({name:args})
    return decoded

def score_entry(entry: dict, calls: list[dict], name_style: str = 'canonical') -> dict:
    if name_style not in {'canonical','api'}:
        raise ValueError('name_style must be canonical or api')
    if len(entry['ground_truth']) != 1:
        raise ValueError('This release supports only single-call multiple cases')
    return ast_checker(entry['function'],calls,entry['ground_truth'],Language.PYTHON,'multiple',name_style)

def score_predictions(benchmark: Path, result_file: Path, *, name_style='canonical') -> dict[str,Any]:
    entries=load_jsonl(benchmark)
    predictions=load_jsonl(result_file)
    by_id={p['id']:p for p in predictions}
    unknown=set(by_id)-{e['id'] for e in entries}
    if unknown:
        raise ValueError(f'Unknown prediction IDs: {sorted(unknown)}')
    results=[]
    for entry in entries:
        p=by_id.get(entry['id'])
        if p is None:
            check={'valid':False,'error_type':'missing_prediction'}
        elif p.get('api_error'):
            check={'valid':False,'error_type':'api_error'}
        else:
            try:
                check=score_entry(entry,decode_calls(p),name_style)
            except (ValueError,KeyError,TypeError) as exc:
                check={'valid':False,'error_type':'invalid_prediction','error':[str(exc)]}
        results.append({'id':entry['id'],**check})
    correct=sum(bool(r['valid']) for r in results)
    return {'protocol':'bfcl-multiple-strict-single-turn-v1','name_style':name_style,
            'benchmark_sha256':hashlib.sha256(benchmark.read_bytes()).hexdigest(),
            'predictions_sha256':hashlib.sha256(result_file.read_bytes()).hexdigest(),
            'total':len(entries),'correct':correct,'incorrect':len(entries)-correct,
            'missing':sum(r.get('error_type')=='missing_prediction' for r in results),
            'api_errors':sum(r.get('error_type')=='api_error' for r in results),
            'accuracy':correct/len(entries) if entries else 0.0,'results':results}

def run_evaluation(model: str, category: str, locale_code: str, result_file: Path,
                   *, benchmark: str | None = None, output_dir: Path | None = None,
                   name_style: str = 'canonical') -> dict[str,Any]:
    """Select a condition explicitly; never fall back to English ground truth."""
    if not benchmark:
        raise ValueError('benchmark condition is required (e.g. zh-CN_translatable_full)')
    path=benchmark_path(category,locale_code,benchmark)
    report=score_predictions(path,Path(result_file),name_style=name_style)
    report['model']=model
    if output_dir is not None:
        output_dir=Path(output_dir)
        output_dir.mkdir(parents=True,exist_ok=True)
        (output_dir/'scores.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report
