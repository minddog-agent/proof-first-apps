import os,subprocess,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root.parent.parent))
from state_machine import specification
source=(root/'proofs/Lease.dfy').read_text()
mutant=source.replace('ok := s.holder == holder && s.token == token;', 'ok := s.holder == holder;')
assert mutant != source and specification(mutant)==specification(source)
path=root/'proofs/Lease-mutant.dfy';path.write_text(mutant)
out=root/'lib/rejected-mutant'
r=subprocess.run([sys.executable,str(root.parent.parent/'state_machine.py'),'--source',str(path),'--contract',str(root/'proofs/contract.json'),'--adapter',str(root/'proofs/adapter.mjs'),'--out',str(out)],capture_output=True,text=True)
assert r.returncode != 0 and not out.exists(), r.stdout+r.stderr
assert 'could not be proved' in r.stdout+r.stderr,r.stdout+r.stderr
(root/'tests/negative-result.json').write_text(json.dumps({'mutation':'Release ignores token','rejected':True,'executable_emitted':False,'diagnostics':r.stdout+r.stderr},indent=2)+'\n')
print('Token-check mutant rejected under unchanged specification; no executable emitted.')
