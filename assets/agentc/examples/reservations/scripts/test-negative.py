import importlib.util,subprocess,tempfile,json,os
from pathlib import Path
driver=Path(__file__).resolve().parents[3]/'state_machine.py'
sp=importlib.util.spec_from_file_location('driver',driver);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
raw=Path('proofs/Inventory.dfy').read_text();results=[]
changes={
 'overwrite_held_seat':('if seat.status!=0 {result:=1;}','if false {result:=1;}'),
 'skip_owner_check':('if seat.status!=1 || seat.owner!=c.owner || seat.token!=c.token','if seat.status!=1 || seat.token!=c.token'),
 'skip_token_check':('if seat.status!=1 || seat.owner!=c.owner || seat.token!=c.token','if seat.status!=1 || seat.owner!=c.owner'),
 'late_expiration':('ys:=[if xs[0].status==1 && xs[0].expires<=now','ys:=[if xs[0].status==1 && xs[0].expires<now'),
 'ignore_stale_version':('if c.expected!=s.version {result:=5;','if false {result:=5;'),
 'duplicate_changes_version':('if c.id in s.seen {result:=','if c.id in s.seen {t:=t.(version:=s.version+1);result:=')}
for name,(old,new) in changes.items():
 assert raw.count(old)==1;candidate=raw.replace(old,new);assert m.specification(candidate)==m.specification(raw)
 with tempfile.TemporaryDirectory() as d:
  p=Path(d)/'Inventory.dfy';p.write_text(candidate);out=Path(d)/'out'
  r=subprocess.run(['python3',str(driver),'--source',str(p),'--contract','proofs/contract.json','--adapter','proofs/adapter.mjs','--out',str(out)],capture_output=True,text=True,timeout=180)
  assert r.returncode!=0 and 'Error:' in r.stdout+r.stderr and not out.exists(),(name,r.stdout,r.stderr)
  results.append({'mutation':name,'rejected':True,'executable_emitted':False,'diagnostics':r.stdout+r.stderr});print(name+': rejected',flush=True)
# Pin and bypass gates fail before translation.
for name,candidate in [('changed_contract',raw.replace('Count(xs,1)+Count(xs,2)<=|xs|','Count(xs,1)+Count(xs,2)<=|xs|+1')),('assumption',raw.replace('t:=s;result:=0;','assume false; t:=s;result:=0;'))]:
 with tempfile.TemporaryDirectory() as d:
  p=Path(d)/'Inventory.dfy';p.write_text(candidate);out=Path(d)/'out'
  r=subprocess.run(['python3',str(driver),'--source',str(p),'--contract','proofs/contract.json','--adapter','proofs/adapter.mjs','--out',str(out)],capture_output=True,text=True)
  assert r.returncode!=0 and not out.exists();results.append({'mutation':name,'rejected':True,'executable_emitted':False});print(name+': rejected',flush=True)
Path('proofs/negative-evidence.json').write_text(json.dumps(results,indent=2)+'\n')
