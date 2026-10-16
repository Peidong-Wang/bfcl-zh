"""Dependency-free CLI for the frozen benchmark and offline scorer."""
import argparse
import json
from pathlib import Path
from .datasets import benchmark_path,load_jsonl,full_suite_path
from .eval_runner import run_evaluation

def main():
    parser=argparse.ArgumentParser(description='Chinese BFCL frozen multiple benchmark')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('full-data-path',help='Print the native full Chinese BFCL v4 data directory')
    sub.add_parser('full-validate',help='Verify packaged full-suite coverage and checksums offline')
    for name in ('data-path','validate','score','evaluate'):
        cmd=sub.add_parser(name)
        cmd.add_argument('--category',default='bfcl_multiple')
        cmd.add_argument('--locale',default='zh-CN')
        cmd.add_argument('--benchmark',default='zh-CN_translatable_full')
        if name=='score':
            cmd.add_argument('--predictions',type=Path,required=True)
            cmd.add_argument('--output-dir',type=Path,required=True)
            cmd.add_argument('--name-style',choices=['canonical','api'],default='canonical')
            cmd.add_argument('--model',default='unspecified')
        if name=='evaluate':
            cmd.add_argument('--model',required=True)
            cmd.add_argument('--model-type',choices=['standard','reasoning','responses','claude'],default='standard')
            cmd.add_argument('--env-file',type=Path)
            cmd.add_argument('--output-dir',type=Path,required=True)
            cmd.add_argument('--limit',type=int,default=1)
            cmd.add_argument('--max-tokens',type=int,default=2048)
            cmd.add_argument('--timeout',type=int,default=120)
            cmd.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if args.command in ('full-data-path','full-validate'):
        root=full_suite_path()
        if args.command=='full-data-path':
            print(root)
            return
        import hashlib
        status=json.loads((root.parent/'build_status.json').read_text(encoding='utf-8'))
        inventory=json.loads((root.parent/'inventory.json').read_text(encoding='utf-8'))
        if not status['complete'] or len(status['completed_physical_categories'])!=19:
            raise ValueError('Full-suite coverage is incomplete')
        total=0
        for item in status['completed_physical_categories']:
            path=root/item['file']
            rows=load_jsonl(path)
            if len(rows)!=item['records'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
                raise ValueError(f'Dataset checksum/count mismatch: {path.name}')
            total+=len(rows)
        for item in status['copied_reference_resources']:
            if hashlib.sha256((root/item['file']).read_bytes()).hexdigest()!=item['sha256']:
                raise ValueError(f'Reference checksum mismatch: {item["file"]}')
        if hashlib.sha256((root/'BFCL_v4_format_sensitivity.json').read_bytes()).hexdigest()!=status['format_selector_sha256']:
            raise ValueError('Format selection checksum mismatch')
        if total!=inventory['physical_source_records'] or total!=4696:
            raise ValueError('Full-suite record count mismatch')
        print(json.dumps({'valid':True,'physical_categories':19,'records':total,'model_evaluation_run':False}))
        return
    path=benchmark_path(args.category,args.locale,args.benchmark)
    if args.command=='data-path': print(path)
    elif args.command=='validate':
        rows=load_jsonl(path)
        for r in rows:
            if not all(k in r for k in ('messages','function','ground_truth')):
                raise ValueError(f'Missing benchmark fields: {r["id"]}')
        print(json.dumps({'file':str(path),'records':len(rows),'valid':True}))
    elif args.command=='evaluate':
        if args.limit<0 or args.max_tokens<1 or args.timeout<1: parser.error('Invalid numeric limit')
        from .inference import run
        print(json.dumps(run(args),ensure_ascii=False,indent=2))
    else:
        report=run_evaluation(args.model,args.category,args.locale,args.predictions,
                              benchmark=args.benchmark,output_dir=args.output_dir,name_style=args.name_style)
        print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
