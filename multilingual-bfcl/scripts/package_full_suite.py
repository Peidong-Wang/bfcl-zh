"""Create a minimal portable native-data archive, only after release checks pass."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FULL=ROOT/'data/benchmarks/bfcl_full'

def package():
    validation=json.loads((FULL/'validation.json').read_text(encoding='utf-8'))
    if not validation['publishable']:
        raise RuntimeError('Refusing to package incomplete or invalid full-suite data')
    output=ROOT/'dist/bfcl-v4-zh-CN-dataset.zip'
    output.parent.mkdir(exist_ok=True)
    paths=[p for p in (FULL/'zh-CN').rglob('*') if p.is_file()]
    documents=['LICENSE','NOTICE','FULL_SUITE_USAGE.md','SOURCES.md','BFCL_CATEGORIES.md','CHINESE_REVIEW.md']
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths): archive.write(path,'zh-CN/'+path.relative_to(FULL/'zh-CN').as_posix())
        for name in documents: archive.write(ROOT/name,name)
        for name in ['inventory.json','build_status.json','validation.json','invariant_queries.json']:
            archive.write(FULL/name,name)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for path in paths:
            assert archive.read('zh-CN/'+path.relative_to(FULL/'zh-CN').as_posix())==path.read_bytes()
    report={'archive':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'dataset_files':len(paths),'source_records':4696,'model_evaluation_run':False,
            'translation_api_used':False,'crc_and_byte_equality':'passed'}
    (ROOT/'DATASET_PACKAGING.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': package()
