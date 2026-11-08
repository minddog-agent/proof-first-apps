"""Verify a pinned, self-contained Dafny state machine and emit its compiled JS.
Restricted source convention: single-line datatype/function/predicate definitions;
method/lemma headers end immediately before a line beginning with '{'.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,tempfile
from pathlib import Path

def digest(data):return hashlib.sha256(data).hexdigest()
def specification(raw):
 for line in raw.splitlines():
  if re.match(r'^(datatype|function|predicate) ',line) and line.count('{')!=line.count('}'):
   raise ValueError('Definitions must be single-line for specification extraction')
 return '\n'.join(re.findall(r'(?m)^(?:datatype|function|predicate) .+$',raw)+re.findall(r'(?ms)^(?:method|lemma) .*?(?=^\{)',raw))
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--contract',required=True);p.add_argument('--adapter',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 out=Path(a.out).resolve()
 if out.exists():raise ValueError('Use a fresh output directory')
 raw=Path(a.source).read_text();pin=json.loads(Path(a.contract).read_text());spec=specification(raw)
 if digest(spec.encode())!=pin['specification_sha256']:raise ValueError('Pinned specification changed; explicit review required')
 if re.search(r'\b(assume|axiom|extern|include)\b|\{\:|decreases\s+\*',raw):raise ValueError('Proof bypasses, attributes and includes are unsupported')
 dafny=os.environ.get('AGENTC_DAFNY','dafny');version=subprocess.check_output([dafny,'--version'],text=True).strip()
 if not version.startswith('4.11.0'):raise ValueError('Dafny 4.11.0 required')
 with tempfile.TemporaryDirectory() as tmp:
  t=Path(tmp);(t/'StateMachine.dfy').write_text(raw)
  r=subprocess.run([dafny,'translate','js','StateMachine.dfy','--include-runtime','--verification-time-limit','30','-o','compiler.js'],cwd=t,capture_output=True,text=True,timeout=180)
  print(r.stdout+r.stderr)
  if r.returncode:raise SystemExit(r.returncode)
  compiled=(t/'compiler.js').read_text();needle="const BigNumber = require('bignumber.js');"
  if compiled.count(needle)!=1:raise ValueError('Unexpected compiler import')
  adapter=Path(a.adapter).read_text();esm=compiled.replace(needle,"import BigNumber from 'bignumber.js';")+adapter
  (t/'core.mjs').write_text(esm);(t/'adapter.mjs').write_text(adapter);shutil.copy(a.contract,t/'contract.json')
  (t/'evidence.json').write_text(json.dumps({'status':'verified','backend':'dafny-state-machine','specification_sha256':pin['specification_sha256'],'candidate_sha256':digest(raw.encode()),'compiler_sha256':digest(compiled.encode()),'source_sha256':digest(esm.encode()),'adapter_sha256':digest(adapter.encode()),'compiler_version':version,'translation_assurance':'source_verified_compiler_trusted','adapter_assurance':'tested_only','whole_app_verified':False,'diagnostics':r.stdout+r.stderr},indent=2)+'\n')
  out.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(t,out)
if __name__=='__main__':main()
