#!/usr/bin/env python3
"""Contract-driven Lean verification for agent-proposed source files. Python 3.10+."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
VERSION = '0.11.0-experimental'
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
IDENTIFIER = re.compile(r'Candidate\.[A-Za-z_][A-Za-z0-9_]*$')
MAX_SOURCE_BYTES = 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_contract(value):
    path = Path(value)
    if not path.exists():
        path = ROOT/'contracts'/value/'contract.json'
    if path.is_dir(): path = path/'contract.json'
    raw = path.read_bytes()
    m = json.loads(raw)
    if not isinstance(m, dict) or set(m) != {'schema_version','name','lean_version','spec_sha256','exports','obligations','notes'}:
        raise ValueError('invalid contract manifest fields')
    if type(m['schema_version']) is not int or m['schema_version'] != 1 or m['lean_version'] != '4.19.0':
        raise ValueError('unsupported manifest schema or Lean version')
    if not isinstance(m['name'], str) or not isinstance(m['notes'], list):
        raise ValueError('invalid contract metadata')
    spec = (path.parent/'ContractSpec.lean').read_bytes()
    if len(spec) > MAX_SOURCE_BYTES or sha(spec) != m['spec_sha256']:
        raise ValueError('contract specification hash mismatch or source too large')
    for group in ('exports','obligations'):
        if not isinstance(m[group],list) or not 1 <= len(m[group]) <= 64:
            raise ValueError(group+' must contain 1 to 64 entries')
    names, ids = set(), set()
    for e in m['exports']:
        if not isinstance(e,dict) or set(e) != {'name','type'} or not isinstance(e['name'],str) or not IDENTIFIER.fullmatch(e['name']):
            raise ValueError('invalid export declaration')
        if e['name'] in names: raise ValueError('duplicate export')
        names.add(e['name'])
        if not isinstance(e['type'],str) or not e['type'].strip(): raise ValueError('empty export type')
    for o in m['obligations']:
        if not isinstance(o,dict) or set(o) != {'id','proof','type','required'}:
            raise ValueError('invalid obligation fields')
        if not isinstance(o['id'],str) or not re.fullmatch(r'[a-z][a-z0-9_]*',o['id']) or o['id'] in ids:
            raise ValueError('invalid or duplicate obligation ID')
        ids.add(o['id'])
        if not isinstance(o['proof'],str) or not IDENTIFIER.fullmatch(o['proof']) or o['proof'] in names:
            raise ValueError('invalid or duplicate proof name')
        names.add(o['proof'])
        if type(o['required']) is not bool or not isinstance(o['type'],str) or not o['type'].strip():
            raise ValueError('invalid obligation type or required flag')
    if not any(o['required'] for o in m['obligations']):
        raise ValueError('at least one required obligation is necessary')
    fingerprint = sha(raw + b'\0' + spec)
    return {'manifest':m,'raw':raw,'spec':spec,'fingerprint':fingerprint,'path':str(path.resolve())}


def diagnostics(stdout, stderr):
    items=[]
    for line in stdout.splitlines():
        try:
            item=json.loads(line)
            if isinstance(item,dict): items.append(item)
            else: items.append({'severity':'info','data':line})
        except json.JSONDecodeError:
            if line.strip():items.append({'severity':'info','data':line})
    if stderr.strip():items.append({'severity':'stderr','data':stderr.strip()})
    return items


def invoke(lean, work, args, timeout):
    env=os.environ.copy()
    env['LEAN_PATH']=str(work)
    started=time.monotonic()
    try:
        p=subprocess.run([lean,*args],cwd=work,env=env,capture_output=True,text=True,timeout=timeout)
        return {'code':p.returncode,'timeout':False,'diagnostics':diagnostics(p.stdout,p.stderr),
                'elapsed_ms':round((time.monotonic()-started)*1000,2)}
    except subprocess.TimeoutExpired:
        return {'code':None,'timeout':True,'diagnostics':[{'severity':'error','data':'Lean checking exceeded the per-process time budget.'}],
                'elapsed_ms':round((time.monotonic()-started)*1000,2)}


def lean_check(lean,work,filename,timeout,output=None):
    args=['--json','-DmaxHeartbeats=2000000']
    if output:args+=['-o',output]
    return invoke(lean,work,[*args,filename],timeout)


def audit(output, expected):
    text='\n'.join(str(d.get('data','')) for d in output['diagnostics'])
    pattern=r"'([^']+)' (?:depends on axioms:\s*\[([^\]]*)\]|does not depend on any axioms)"
    matches=re.findall(pattern,text)
    if len(matches)!=1 or matches[0][0]!=expected:
        return {'status':'rejected','reason':'invalid_axiom_report'}
    axioms=[s.strip() for s in matches[0][1].split(',') if s.strip()]
    unsupported=set(axioms)-ALLOWED_AXIOMS
    if unsupported=={'sorryAx'}:
        return {'status':'unproved','reason':'proof_placeholder','axioms':axioms}
    if unsupported:
        return {'status':'rejected','reason':'unsupported_axioms','axioms':axioms,'unsupported_axioms':sorted(unsupported)}
    return {'status':'proved','axioms':axioms}


def obligation_result(lean,work,o,index,timeout):
    theorem=f'AgentcCheck.obligation{index}'
    source=(f'import Candidate\n'
            f'theorem {theorem} : {o["type"]} := {o["proof"]}\n'
            f'#print axioms {theorem}\n')
    (work/'Check.lean').write_text(source)
    out=lean_check(lean,work,'Check.lean',timeout)
    result={'id':o['id'],'required':o['required'],'proof':o['proof'],'claim':o['type'],
            'diagnostics':out['diagnostics']}
    if out['timeout']:
        result.update(status='unknown',reason='timeout')
    elif out['code']!=0:
        errors='\n'.join(str(d.get('data','')) for d in out['diagnostics'] if d.get('severity')=='error')
        missing=any(s in errors for s in [f"unknown constant '{o['proof']}'",f"unknown identifier '{o['proof']}'"])
        result.update(status='missing' if missing else 'rejected',reason='proof_not_found' if missing else 'proof_does_not_check')
    else:result.update(audit(out,theorem))
    return result


def verify(contract,candidate,timeout=20,expected=None):
    started=time.monotonic()
    bundle=load_contract(contract)
    if expected and expected!=bundle['fingerprint']:
        raise ValueError('contract fingerprint differs from --expect-contract')
    candidate=Path(candidate)
    data=candidate.read_bytes()
    if len(data)>MAX_SOURCE_BYTES:raise ValueError('candidate exceeds 1 MiB')
    source=data.decode('utf-8')
    lean=shutil.which('lean')
    if not lean:raise ValueError('Lean not found. Install elan and Lean 4.19.0; put lean on PATH.')
    report={'schema_version':1,'tool_version':VERSION,'contract':bundle['manifest']['name'],
            'contract_fingerprint':bundle['fingerprint'],'candidate':str(candidate.resolve()),
            'candidate_sha256':sha(data),'candidate_bytes':len(data),'status':'rejected',
            'allowed_axioms':sorted(ALLOWED_AXIOMS),'obligations':[],
            'scope':'Only the listed contract obligations; no runtime performance or hostile-code sandbox guarantee.'}
    with tempfile.TemporaryDirectory(prefix='agentc-check-') as directory:
        work=Path(directory)
        (work/'lean-toolchain').write_text('leanprover/lean4:v4.19.0\n')
        (work/'ContractSpec.lean').write_bytes(bundle['spec'])
        (work/'Candidate.lean').write_text(source)
        v=invoke(lean,work,['--version'],timeout)
        version='\n'.join(str(d.get('data','')) for d in v['diagnostics'])
        if v['code']!=0 or not version.startswith('Lean (version 4.19.0,'):
            raise ValueError('Lean 4.19.0 required; observed: '+version)
        report['lean_version']=version
        spec=lean_check(lean,work,'ContractSpec.lean',timeout,'ContractSpec.olean')
        if spec['code']!=0:
            report.update(status='unknown' if spec['timeout'] else 'error',stage='contract',diagnostics=spec['diagnostics'])
        else:
            compiled=lean_check(lean,work,'Candidate.lean',timeout,'Candidate.olean')
            report['candidate_diagnostics']=compiled['diagnostics']
            if compiled['code']!=0:
                report.update(status='unknown' if compiled['timeout'] else 'rejected',stage='candidate',reason='timeout' if compiled['timeout'] else 'candidate_compile_error')
            else:
                exports=[]
                for i,e in enumerate(bundle['manifest']['exports']):
                    (work/'Export.lean').write_text(f'import Candidate\nexample : {e["type"]} := {e["name"]}\n#print axioms {e["name"]}\n')
                    out=lean_check(lean,work,'Export.lean',timeout)
                    row={'name':e['name'],'diagnostics':out['diagnostics']}
                    if out['code']==0:row.update(audit(out,e['name']))
                    else:row.update(status='unknown' if out['timeout'] else 'rejected',reason='timeout' if out['timeout'] else 'invalid_export')
                    exports.append(row)
                report['exports']=exports
                report['obligations']=[obligation_result(lean,work,o,i,timeout) for i,o in enumerate(bundle['manifest']['obligations'])]
                required=[r for r in report['obligations'] if r['required']]+exports
                if all(r['status']=='proved' for r in required):report['status']='verified'
                elif any(r['status']=='rejected' for r in required):report['status']='rejected'
                else:report['status']='incomplete'
    if not report['obligations']:
        report['obligations']=[{'id':o['id'],'required':o['required'],'proof':o['proof'],'claim':o['type'],
                                'status':'not_checked','reason':'blocked_by_'+report.get('stage','setup')} for o in bundle['manifest']['obligations']]
    report['summary']={s:sum(r['status']==s for r in report['obligations']) for s in ['proved','missing','unproved','rejected','unknown','not_checked']}
    report['verification_ms']=round((time.monotonic()-started)*1000,2)
    return report,bundle,data


def scaffold(bundle,path):
    path=Path(path)
    if path.exists():raise ValueError('scaffold destination already exists')
    m=bundle['manifest']
    lines=['import ContractSpec','','-- Replace each placeholder, then submit with agentc verify.']
    for e in m['exports']:lines += [f'def {e["name"]} : {e["type"]} := by', '  sorry','']
    for o in m['obligations']:lines += [f'-- obligation: {o["id"]}',f'theorem {o["proof"]} : {o["type"]} := by','  sorry','']
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('\n'.join(lines))
    return {'status':'scaffolded','path':str(path.resolve()),'contract_fingerprint':bundle['fingerprint'],'note':'Placeholders are not proofs; verification will report them as unproved.'}


def emit(report,bundle,data,destination):
    if report['status']!='verified':raise ValueError('emission requires every required obligation and export to be proved')
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('output directory already exists; choose a fresh destination')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.agentc-emit-',dir=destination.parent) as tmp:
        folder=Path(tmp)/'bundle';folder.mkdir()
        (folder/'ContractSpec.lean').write_bytes(bundle['spec'])
        (folder/'Candidate.lean').write_bytes(data)
        (folder/'contract.json').write_bytes(bundle['raw'])
        (folder/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
        (folder/'lean-toolchain').write_text('leanprover/lean4:v4.19.0\n')
        (folder/'README.txt').write_text('Verified Lean source bundle. ContractSpec.lean and Candidate.lean are the exact checked sources.\nRecheck with: agentc verify --contract contract.json --candidate Candidate.lean\nThe receipt is evidence, not a signature. This bundle contains no translated executable.\n')
        folder.rename(destination)
    return {'status':'emitted','path':str(destination),'contract_fingerprint':bundle['fingerprint'],'candidate_sha256':report['candidate_sha256']}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "timeline":
        from timeline import main as timeline_main
        return timeline_main(argv[1:])
    if argv and argv[0] == "coverage":
        from coverage_gate import main as coverage_main
        return coverage_main(argv[1:])
    if argv and argv[0] == "translate-float":
        from floating import main as float_main
        return float_main(argv[1:])
    if argv and argv[0] == "translate":
        from translation import main as translate_main
        return translate_main(argv[1:])
    p=argparse.ArgumentParser(description=__doc__ + " Use translate --help for Python/JavaScript/Rust generation.")
    p.add_argument('--version',action='version',version=VERSION)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    for name in ('describe','scaffold','verify','compare','emit'):
        cmd=sub.add_parser(name)
        cmd.add_argument('--contract',required=True,help='built-in name or path to contract.json/bundle directory')
        if name=='scaffold':cmd.add_argument('--out',required=True)
        if name in ('verify','compare','emit'):
            cmd.add_argument('--candidate',required=True,action='append' if name=='compare' else 'store')
            cmd.add_argument('--expect-contract')
            cmd.add_argument('--timeout',type=float,default=20,help='seconds per Lean process')
            if name=='emit':cmd.add_argument('--out',required=True)
            else:cmd.add_argument('--out',help='optional JSON report path')
    args=p.parse_args(argv)
    try:
        code=0
        if args.command=='list':
            result={'contracts':[load_contract(path)['manifest']['name'] for path in sorted((ROOT/'contracts').glob('*/contract.json'))]}
        elif args.command in ('describe','scaffold'):
            b=load_contract(args.contract)
            result=scaffold(b,args.out) if args.command=='scaffold' else {'contract_fingerprint':b['fingerprint'],**b['manifest']}
        else:
            if not 0<args.timeout<=300:raise ValueError('timeout must be greater than zero and at most 300 seconds')
            if args.command=='compare':
                reports=[verify(args.contract,path,args.timeout,args.expect_contract)[0] for path in args.candidate]
                fingerprints={r['contract_fingerprint'] for r in reports}
                if len(fingerprints)!=1:raise ValueError('contract changed during comparison')
                result={'contract_fingerprint':reports[0]['contract_fingerprint'],
                        'verified_candidates':[r['candidate'] for r in reports if r['status']=='verified'],
                        'candidates':reports,'note':'Verification time is tool overhead, not runtime performance; no automatic ranking.'}
                code=0 if result['verified_candidates'] else 1
            else:
                report,b,data=verify(args.contract,args.candidate,args.timeout,args.expect_contract)
                result=emit(report,b,data,args.out) if args.command=='emit' and report['status']=='verified' else report
                code=0 if report['status']=='verified' else (2 if report['status']=='error' else 1)
            if args.command!='emit' and args.out:
                dest=Path(args.out).resolve()
                inputs=[Path(v).resolve() for v in (args.candidate if isinstance(args.candidate,list) else [args.candidate])]
                b=load_contract(args.contract)
                inputs += [Path(b['path']),Path(b['path']).parent/'ContractSpec.lean']
                if dest in inputs:raise ValueError('report output cannot overwrite an input')
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
        return code
    except (OSError,ValueError,KeyError,UnicodeError) as e:
        print(json.dumps({'status':'error','message':str(e)}))
        return 2

if __name__=='__main__':sys.exit(main())
