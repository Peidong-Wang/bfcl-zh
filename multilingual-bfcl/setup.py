"""Include the curated dataset snapshot in wheels, without historical logs."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py

ROOT=Path(__file__).parent

class BuildWithData(build_py):
    def run(self):
        import json
        release=ROOT/'data/benchmarks/bfcl_full/validation.json'
        if not release.exists() or not json.loads(release.read_text(encoding='utf-8'))['publishable']:
            raise RuntimeError('Full-suite validation must pass before building a release')
        # Remove only generated resources inside this build output, so an older
        # build cannot accidentally carry excluded locales into a new wheel.
        build_root=Path(self.build_lib).resolve()
        generated=(build_root/'multilingual_bfcl/data').resolve()
        if not generated.is_relative_to(build_root):
            raise RuntimeError('Generated data escaped build directory')
        if generated.is_dir(): shutil.rmtree(generated)
        super().run()
        target=Path(self.build_lib)/'multilingual_bfcl'
        source=ROOT/'data/benchmarks/bfcl_multiple'
        for locale in ('en','zh-CN'):
            for path in (source/locale).iterdir():
                if path.is_file() and path.suffix in {'.jsonl','.json','.tsv','.txt'}:
                    out=target/'data/benchmarks/bfcl_multiple'/locale/path.name
                    out.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(path,out)
        for name in ('README.md','FULL_SUITE_USAGE.md','BFCL_CATEGORIES.md','SOURCES.md','RELEASE_READINESS.md','CHINESE_REVIEW.md','PROVENANCE.json','CHINESE_REVIEW.json'):
            path=ROOT/name
            if path.exists():
                out=target/'docs'/name
                out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,out)
        full=ROOT/'data/benchmarks/bfcl_full'
        for path in (full/'zh-CN').rglob('*'):
            if path.is_file():
                out=target/'data/benchmarks/bfcl_full/zh-CN'/path.relative_to(full/'zh-CN')
                out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,out)
        for name in ('inventory.json','build_status.json','validation.json','invariant_queries.json'):
            out=target/'data/benchmarks/bfcl_full'/name
            out.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(full/name,out)

setup(cmdclass={'build_py':BuildWithData})
