"""Export a frozen batch for direct Codex authoring, never an API request."""
import argparse
import json
from prepare_full_suite import OUT,prepare

parser=argparse.ArgumentParser()
parser.add_argument('--category',required=True)
parser.add_argument('--name',required=True)
parser.add_argument('--limit',type=int,default=100)
args=parser.parse_args()
assert args.name and all(c.isalnum() or c in '_-' for c in args.name)
prepare()
rows=[json.loads(l) for l in (OUT/'query_ledger.jsonl').read_text(encoding='utf-8').splitlines()]
selected=[{'key':r['key'],'source':r['source']} for r in rows if not r['translation'] and any(u['category']==args.category for u in r['uses'])][:args.limit]
directory=OUT/'authored_batches'
directory.mkdir(exist_ok=True)
path=directory/f'{args.name}_source.json'
if path.exists():
    selected=json.loads(path.read_text(encoding='utf-8'))
else:
    path.write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Batch {args.name}: {len(selected)} unique user messages')
for i,row in enumerate(selected):
    print(f'{i}\t'+json.dumps(row['source'],ensure_ascii=False))
