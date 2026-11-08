"""Audit declared app proof coverage; never infer full-app correctness from receipts."""
import argparse, hashlib, json, re
from pathlib import Path
from translation import read_json

STATUSES={'proved','model_only','tested_only','trusted','unproved','not_run'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def local(root,value):
    if not isinstance(value,str)or not value:raise ValueError('path must be a nonempty string')
    p=(root/value).resolve()
    if not p.is_relative_to(root):raise ValueError('evidence path escapes project')
    return p

def audit(path,root):
    _,m=read_json(path)
    if not isinstance(m,dict)or set(m)!={'schema_version','scope','requirements','components'}or type(m['schema_version'])is not int or m['schema_version']!=1:raise ValueError('invalid coverage schema')
    if not isinstance(m['scope'],str)or not m['scope'].strip():raise ValueError('scope required')
    req=m['requirements'];cs=m['components']
    if not isinstance(req,list)or not req or any(not isinstance(x,str)or not x for x in req)or len(set(req))!=len(req):raise ValueError('unique requirements required')
    if not isinstance(cs,list)or not cs:raise ValueError('components required')
    ids=set();covered=set();gaps=[]
    for c in cs:
        if not isinstance(c,dict)or set(c)!={'id','requirements','depends_on','status','sources','receipt','integrated'}:raise ValueError('invalid component fields')
        if not isinstance(c['id'],str)or not re.fullmatch('[a-z][a-z0-9_]*',c['id'])or c['id']in ids:raise ValueError('invalid/duplicate component ID')
        ids.add(c['id'])
        if c['status']not in STATUSES or type(c['integrated'])is not bool:raise ValueError('invalid status/integrated')
        for key in ('requirements','depends_on'):
            if not isinstance(c[key],list)or any(not isinstance(x,str)for x in c[key]):raise ValueError('invalid component links')
        if not set(c['requirements'])<=set(req):raise ValueError('unknown requirement')
        covered.update(c['requirements'])
        if not isinstance(c['sources'],dict)or not c['sources']:raise ValueError('source hashes required')
        for filename,digest in c['sources'].items():
            if not isinstance(digest,str)or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('invalid source hash')
            p=local(root,filename)
            if not p.is_file()or sha(p)!=digest:gaps.append({'component':c['id'],'reason':'source_missing_or_changed','path':filename})
        if c['status']!='proved':gaps.append({'component':c['id'],'reason':c['status']})
        if not c['integrated']:gaps.append({'component':c['id'],'reason':'not_integrated'})
        if c['status']=='proved':
            if not c['receipt']:gaps.append({'component':c['id'],'reason':'missing_receipt'});continue
            p=local(root,c['receipt']);_,r=read_json(p)
            if r.get('status')!='verified':gaps.append({'component':c['id'],'reason':'receipt_not_verified'})
            if r.get('translation_assurance')not in {'source_verified_renderer_trusted','source_verified_compiler_trusted'}:gaps.append({'component':c['id'],'reason':'receipt_not_executable_proof'})
            # Experimental binary64 receipts bind the precise emitted module and proof inputs.
            if r.get('backend')=='dafny-sequence':
                if r.get('source_sha256')not in c['sources'].values():gaps.append({'component':c['id'],'reason':'production_source_not_bound_to_proof'})
                for field,file in [('contract_fingerprint','Timeline.dfy'),('compiler_sha256','compiler.js')]:
                    q=p.parent/file
                    if not q.is_file()or sha(q)!=r.get(field):gaps.append({'component':c['id'],'reason':'proof_input_missing_or_changed','path':file})
                continue
            if r.get('backend')!='z3-smtlib-fp':
                gaps.append({'component':c['id'],'reason':'receipt_backend_requires_manual_audit'});continue
            if r.get('source_sha256')not in c['sources'].values():gaps.append({'component':c['id'],'reason':'production_source_not_bound_to_proof'})
            for field,file in [('contract_fingerprint','contract.json'),('candidate_sha256','candidate.json'),('smt_sha256','verification.smt2')]:
                q=p.parent/file
                if not q.is_file()or sha(q)!=r.get(field):gaps.append({'component':c['id'],'reason':'proof_input_missing_or_changed','path':file})
    for r in set(req)-covered:gaps.append({'requirement':r,'reason':'unmapped_requirement'})
    graph={c['id']:c['depends_on']for c in cs}
    for c in cs:
        if not set(c['depends_on'])<=ids:raise ValueError('unknown dependency')
    visiting=set();visited=set()
    def visit(n):
        if n in visiting:raise ValueError('cyclic component dependencies')
        if n in visited:return
        visiting.add(n)
        for d in graph[n]:visit(d)
        visiting.remove(n);visited.add(n)
    for n in graph:visit(n)
    return {'status':'gaps'if gaps else 'declared_coverage_complete','scope':m['scope'],'gaps':gaps,'full_app_verified':False,'limitations':['Inventory completeness is reviewed by humans/agents, not proved','Receipts are unsigned metadata; re-run the verifier before any scoped proof claim','Dependency wiring and runtime/compiler correctness remain trusted or separately checked']}

def main(argv):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True);p.add_argument('--project',required=True);p.add_argument('--out');a=p.parse_args(argv)
    try:
        root=Path(a.project).resolve();report=audit(a.manifest,root)
        if a.out:Path(a.out).write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2));return 0 if report['status']=='declared_coverage_complete'else 1
    except (ValueError,OSError,TypeError)as e:print(json.dumps({'status':'error','message':str(e)}));return 2
