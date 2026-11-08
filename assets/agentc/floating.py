"""Experimental IEEE-754 binary64 contracts -> Z3 -> JavaScript (renderer trusted)."""
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile
from pathlib import Path
from translation import read_json

# Module: (func (export "sqrt") (param f64) (result f64) local.get 0 f64.sqrt)
WASM_SQRT = """let sqrtInstance;
function wasmSqrt(x) {
  if (!sqrtInstance) sqrtInstance = new WebAssembly.Instance(new WebAssembly.Module(new Uint8Array([0,97,115,109,1,0,0,0,1,6,1,96,1,124,1,124,3,2,1,0,7,8,1,4,115,113,114,116,0,0,10,7,1,5,0,32,0,159,11])));
  return sqrtInstance.exports.sqrt(x);
}
"""

FP='(_ FloatingPoint 11 53)'
def sha(b): return hashlib.sha256(b).hexdigest()

def expr(n, names, allow_result=False, depth=0):
    if depth>48: raise ValueError('expression nesting exceeds 48')
    if type(n) is bool: return ('true' if n else 'false', 'true' if n else 'false','bool')
    if isinstance(n,str):
        if n=='result' and allow_result:return ('result','result','fp')
        if n not in names:raise ValueError('unknown variable')
        p='p'+str(names.index(n));return p,p,'fp'
    if not isinstance(n,list) or not n or not isinstance(n[0],str):raise ValueError('expected expression; use [bits, hex] for numeric constants')
    op=n[0]
    if op=='bits':
        if len(n)!=2 or not isinstance(n[1],str) or not re.fullmatch('[0-9a-fA-F]{16}',n[1]):raise ValueError('expected 16 hexadecimal digits')
        return f'((_ to_fp 11 53) #x{n[1]})',f'fromBits("{n[1]}")','fp'
    arity={'+':2,'-':2,'*':2,'/':2,'neg':1,'abs':1,'sqrt':1,'floor':1,'<':2,'<=':2,'>':2,'>=':2,'==':2,'same':2,'and':2,'or':2,'not':1,'implies':2,'if':3,'finite':1,'nan':1,'infinite':1}
    if op not in arity or len(n)!=arity[op]+1:raise ValueError('unsupported operator or arity: '+op)
    args=[expr(a,names,allow_result,depth+1)for a in n[1:]];s,j,t=zip(*args)
    if op=='if':
        if t[0]!='bool' or t[1]!=t[2]:raise ValueError('conditional type mismatch')
        return f'(ite {s[0]} {s[1]} {s[2]})',f'({j[0]} ? {j[1]} : {j[2]})',t[1]
    if op in ('and','or','not','implies'):
        if any(x!='bool'for x in t):raise ValueError('expected boolean')
        if op=='not':return f'(not {s[0]})',f'(!{j[0]})','bool'
        if op=='implies':return f'(=> {s[0]} {s[1]})',f'(!{j[0]} || {j[1]})','bool'
        return f'({op} {s[0]} {s[1]})',f'({j[0]} {"&&" if op=="and" else "||"} {j[1]})','bool'
    if any(x!='fp'for x in t):raise ValueError('expected binary64')
    if op in ('+','-','*','/'):
        symbol={'+':'add','-':'sub','*':'mul','/':'div'}[op]
        return f'(fp.{symbol} RNE {s[0]} {s[1]})',f'({j[0]} {op} {j[1]})','fp'
    if op=='floor':
        return f'(fp.roundToIntegral RTN {s[0]})',f'Math.floor({j[0]})','fp'
    if op=='sqrt':
        return f'(fp.sqrt RNE {s[0]})',f'wasmSqrt({j[0]})','fp'
    if op in ('neg','abs'):
        return f'(fp.{op} {s[0]})',f'(-{j[0]})'if op=='neg'else f'Math.abs({j[0]})','fp'
    if op in ('finite','nan','infinite'):
        sm={'finite':f'(and (not (fp.isNaN {s[0]})) (not (fp.isInfinite {s[0]})))','nan':f'(fp.isNaN {s[0]})','infinite':f'(fp.isInfinite {s[0]})'}[op]
        js={'finite':f'Number.isFinite({j[0]})','nan':f'Number.isNaN({j[0]})','infinite':f'(!Number.isNaN({j[0]}) && !Number.isFinite({j[0]}))'}[op]
        return sm,js,'bool'
    sm={'<':'fp.lt','<=':'fp.leq','>':'fp.gt','>=':'fp.geq','==':'fp.eq','same':'='}[op]
    js=f'Object.is({j[0]}, {j[1]})'if op=='same'else f'({j[0]} {"===" if op=="==" else op} {j[1]})'
    return f'({sm} {s[0]} {s[1]})',js,'bool'

def contains_sqrt(node):
    return isinstance(node,list) and (bool(node) and node[0]=='sqrt' or any(contains_sqrt(x) for x in node[1:]))

def contract(path):
    raw,c=read_json(path)
    if not isinstance(c,dict) or set(c)!={'schema_version','name','format','rounding','parameters','requires','ensures'}:raise ValueError('invalid float contract fields')
    if type(c['schema_version'])is not int or c['schema_version']!=1 or c['format']!='binary64' or c['rounding']!='RNE':raise ValueError('only binary64 with RNE is supported')
    ps=c['parameters']
    if not isinstance(c['name'],str) or not isinstance(ps,list) or not 1<=len(ps)<=8 or any(not isinstance(p,str)or not re.fullmatch('[A-Za-z][A-Za-z0-9_]*',p)or p=='result'for p in ps)or len(set(ps))!=len(ps):raise ValueError('invalid parameters')
    for field,lo in [('requires',0),('ensures',1)]:
        if not isinstance(c[field],list)or not lo<=len(c[field])<=16:raise ValueError('invalid claims')
        for x in c[field]:
            if expr(x,ps,field=='ensures')[2]!='bool':raise ValueError('claim must be boolean')
    return raw,c

def solve(z3,script,timeout):
    try:
        p=subprocess.run([z3,'-in','-smt2'],input=script,text=True,capture_output=True,timeout=timeout+2)
    except subprocess.TimeoutExpired:return 'unknown','process timeout'
    lines=p.stdout.strip().splitlines()
    if p.returncode or not lines or lines[0]not in ('sat','unsat','unknown')or '(error' in p.stdout:return 'error',p.stdout+p.stderr
    return lines[0],p.stdout+p.stderr

def main(argv):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract',required=True);p.add_argument('--candidate');p.add_argument('--expect-contract');p.add_argument('--describe',action='store_true');p.add_argument('--out');p.add_argument('--check-only',action='store_true');p.add_argument('--sqrt-runtime',choices=['wasm']);p.add_argument('--timeout',type=int,default=20);p.add_argument('--z3',default=os.environ.get('AGENTC_Z3','z3'))
    a=p.parse_args(argv)
    try:
        raw,c=contract(a.contract);fingerprint=sha(raw)
        if a.describe:print(json.dumps({'contract_fingerprint':fingerprint,'contract':c},indent=2));return 0
        if a.expect_contract!=fingerprint:raise ValueError('contract fingerprint mismatch')
        if not 1<=a.timeout<=120:raise ValueError('timeout must be 1..120 seconds')
        if not a.candidate or not a.out:raise ValueError('candidate and out required')
        out=Path(a.out)
        if out.exists():raise ValueError('output already exists')
        candraw,cand=read_json(a.candidate)
        if not isinstance(cand,dict)or set(cand)!={'expression'}:raise ValueError('invalid candidate')
        sm,js,typ=expr(cand['expression'],c['parameters'])
        if typ!='fp':raise ValueError('candidate must return binary64')
        has_sqrt = contains_sqrt(cand['expression']) or any(contains_sqrt(x) for x in c['requires']+c['ensures'])
        if has_sqrt and not a.check_only and a.sqrt_runtime!='wasm':raise ValueError('sqrt requires --check-only or --sqrt-runtime wasm; Math.sqrt rounding is not assumed')
        z3=shutil.which(a.z3)
        if not z3:raise ValueError('Z3 unavailable; set AGENTC_Z3')
        version=subprocess.run([z3,'-version'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
        base=f'(set-option :timeout {a.timeout*1000})\n(set-logic QF_FP)\n'+''.join(f'(declare-fun p{i} () {FP})\n'for i in range(len(c['parameters'])))
        base+=''.join(f'(assert {expr(r,c["parameters"])[0]})\n'for r in c['requires'])
        domain,diag=solve(z3,base+'(check-sat)\n',a.timeout)
        receipt={'backend':'z3-smtlib-fp','solver':version,'contract_fingerprint':fingerprint,'candidate_sha256':sha(candraw),'semantics':'IEEE-754 binary64 RNE; NaN payloads ignored','trusted_components':['Z3 solver','IR renderer','JavaScript engine','input/output adapters']}
        if domain!='sat':
            receipt.update(status='invalid_contract'if domain=='unsat'else 'unknown',phase='domain_nonempty',diagnostics=diag);print(json.dumps(receipt,indent=2));return 1
        claims=[expr(x,c['parameters'],True)[0]for x in c['ensures']]
        script=base+f'(define-fun result () {FP} {sm})\n(assert (not (and '+ ' '.join(claims)+')))\n(check-sat)\n'
        status,diag=solve(z3,script,a.timeout)
        if status!='unsat':
            if status=='sat':_,diag=solve(z3,script+'(get-model)\n',a.timeout)
            receipt.update(status='rejected'if status=='sat'else 'unknown',diagnostics=diag);print(json.dumps(receipt,indent=2));return 1
        params=', '.join('p'+str(i)for i in range(len(c['parameters'])))
        checks=' && '.join(expr(x,c['parameters'])[1]for x in c['requires'])or'true'
        source='''// Generated only after a successful floating-point contract check.
function fromBits(hex) { const b = new ArrayBuffer(8); const d = new DataView(b); d.setBigUint64(0, BigInt('0x'+hex), false); return d.getFloat64(0, false); }
export function run(...args) {
'''+f"  if (args.length !== {len(c['parameters'])} || args.some(x => typeof x !== 'number')) throw new TypeError('expected binary64 Number arguments');\n  const [{params}] = args;\n  if (!({checks})) throw new RangeError('contract precondition failed');\n  return {js};\n}}\n"
        if has_sqrt and not a.check_only:
            source = WASM_SQRT + source
            receipt['sqrt_runtime']='wasm-f64.sqrt'
            receipt['trusted_components'].append('WebAssembly engine implementing f64.sqrt RNE; fixed opcode wrapper')
        receipt.update(status='verified',translation_assurance='model_only' if a.check_only else 'source_verified_renderer_trusted',integration_tests='not_run',smt_sha256=sha(script.encode()))
        if not a.check_only:receipt['source_sha256']=sha(source.encode())
        out.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=out.parent)as tmp:
            staging=Path(tmp)/'emitted';staging.mkdir()
            for name,data in ([('core.mjs',source)] if not a.check_only else []) + [('verification.smt2',script),('contract.json',raw.decode()),('candidate.json',candraw.decode()),('evidence.json',json.dumps(receipt,indent=2))]:(staging/name).write_text(data)
            staging.rename(out)
        print(json.dumps(receipt,indent=2));return 0
    except (ValueError,OSError,subprocess.SubprocessError,TypeError,RecursionError)as e:
        print(json.dumps({'status':'error','message':str(e)}));return 2
