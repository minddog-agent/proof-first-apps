#!/usr/bin/env python3
"""Copy the bundled verifier into a project without overwriting modified files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import re


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',required=True)
    p.add_argument('--tool-dir',default='.agentc/tool',help='Relative project destination; use a fresh path for upgrades')
    args=p.parse_args()
    project=Path(args.project).expanduser().resolve()
    source=Path(__file__).resolve().parents[1]/'assets/agentc'
    target=(project/args.tool_dir).resolve()
    if not target.is_relative_to(project):raise SystemExit('Tool directory must stay inside project')
    files=[x for x in sorted(source.rglob('*')) if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc']
    for path in files:
        dest=target/path.relative_to(source)
        if dest.exists() and (not dest.is_file() or dest.read_bytes()!=path.read_bytes()):
            raise SystemExit('Refusing to overwrite a modified verifier file: '+str(dest))
    copied=0
    for path in files:
        dest=target/path.relative_to(source)
        if not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,dest);copied+=1
    print(json.dumps({'tool':str(target/'agentc.py'),'contracts':str(target/'contracts'),
                      'files_copied':copied,'version':re.search(r"VERSION = '([^']+)'",(target/'agentc.py').read_text()).group(1),
                      'tool_sha256':hashlib.sha256((target/'agentc.py').read_bytes()).hexdigest()},indent=2))

if __name__=='__main__':main()
