"""Restricted integer IR -> verified Dafny -> Python/JavaScript/Rust (compiler trusted)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

VERSION = '4.11.0'

def digest(b): return hashlib.sha256(b).hexdigest()

def read_json(path):
    raw = Path(path).read_bytes()
    if len(raw) > 65536: raise ValueError('IR file exceeds 64 KiB')
    def unique(pairs):
        d = {}
        for k,v in pairs:
            if k in d: raise ValueError('duplicate JSON key: '+k)
            d[k]=v
        return d
    return raw, json.loads(raw, object_pairs_hook=unique)

def expression(node, names, result=None, depth=0):
    if depth > 64: raise ValueError('expression nesting exceeds 64')
    if type(node) is bool: return ('true' if node else 'false'), 'bool'
    if type(node) is int:
        if abs(node).bit_length() > 1024: raise ValueError('integer literal exceeds 1024 bits')
        return '('+str(node)+')', 'int'
    if type(node) is str:
        if node == 'result' and result is not None: return result, 'int'
        if node in names: return 'p'+str(names.index(node)), 'int'
        raise ValueError('unknown variable: '+node)
    if not isinstance(node, list) or not node or not isinstance(node[0], str):
        raise ValueError('expected typed expression')
    op = node[0]
    arities = {'if':3,'+':2,'-':2,'*':2,'<':2,'<=':2,'>':2,'>=':2,'==':2,'!=':2,'and':2,'or':2,'implies':2,'not':1}
    if op not in arities or len(node) != arities[op]+1: raise ValueError('unsupported operator or arity: '+op)
    args = [expression(x,names,result,depth+1) for x in node[1:]]
    terms, types = zip(*args)
    if op == 'if':
        if types[0]!='bool' or types[1]!=types[2]: raise ValueError('ill-typed conditional')
        return f'(if {terms[0]} then {terms[1]} else {terms[2]})',types[1]
    if op in ('and','or','implies','not'):
        if any(t!='bool' for t in types): raise ValueError('expected boolean operands')
        if op=='not': return f'(!{terms[0]})','bool'
        symbol={'and':'&&','or':'||','implies':'==>'}[op]
        return f'({terms[0]} {symbol} {terms[1]})','bool'
    if any(t!='int' for t in types): raise ValueError('expected integer operands')
    return f'({terms[0]} {op} {terms[1]})', 'int' if op in ('+','-','*') else 'bool'

def contract(path):
    raw,c=read_json(path)
    if not isinstance(c,dict) or set(c)!={'schema_version','name','parameters','ensures'} or c['schema_version']!=1 or type(c['schema_version'])!=int:
        raise ValueError('invalid translation contract schema')
    ps=c['parameters']
    if not isinstance(c['name'],str) or not isinstance(ps,list) or not 1<=len(ps)<=16 or any(not isinstance(p,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]*',p) or p=='result' for p in ps) or len(set(ps))!=len(ps):
        raise ValueError('invalid parameters or name')
    if not isinstance(c['ensures'],list) or not 1<=len(c['ensures'])<=32: raise ValueError('require 1..32 postconditions')
    call='Run('+', '.join('p'+str(i) for i in range(len(ps)))+')'
    claims=[]
    for e in c['ensures']:
        s,t=expression(e,ps,call)
        if t!='bool': raise ValueError('postcondition must be boolean')
        claims.append(s)
    return raw,c,claims

def main(argv):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract',required=True)
    p.add_argument('--candidate')
    p.add_argument('--target',choices=['python','javascript','rust'])
    p.add_argument('--out')
    p.add_argument('--expect-contract')
    p.add_argument('--describe',action='store_true')
    p.add_argument('--timeout',type=int,default=60)
    a=p.parse_args(argv)
    try:
        raw,c,claims=contract(a.contract)
        fingerprint=digest(raw)
        if a.expect_contract and a.expect_contract!=fingerprint: raise ValueError('contract fingerprint mismatch')
        if a.describe:
            print(json.dumps({'contract_fingerprint':fingerprint,**c},indent=2));return 0
        if not a.candidate or not a.target or not a.out: raise ValueError('candidate, target and out are required')
        if not 1<=a.timeout<=300: raise ValueError('timeout must be 1..300 seconds')
        candidate_bytes,candidate=read_json(a.candidate)
        if not isinstance(candidate,dict) or set(candidate)!={'expression'}: raise ValueError('candidate must contain only expression')
        body,t=expression(candidate['expression'],c['parameters'])
        if t!='int': raise ValueError('candidate result must be integer')
        params=', '.join(f'p{i}: int' for i in range(len(c['parameters'])))
        source=f'function Run({params}): int\n'+''.join('  ensures '+x+'\n' for x in claims)+'{ '+body+' }\n'
        destination=Path(a.out).resolve()
        if destination.exists(): raise ValueError('output exists; choose a fresh directory')
        dafny=shutil.which(os.environ.get('AGENTC_DAFNY','dafny'))
        if not dafny: raise ValueError('Dafny 4.11.0 is required; set AGENTC_DAFNY or PATH')
        version=subprocess.run([dafny,'--version'],capture_output=True,text=True,timeout=10)
        if version.returncode or version.stdout.strip().split('+')[0]!=VERSION: raise ValueError('expected Dafny 4.11.0')
        report={'schema_version':1,'backend':'dafny','dafny_version':version.stdout.strip(),
                'target':a.target,'contract_fingerprint':fingerprint,'candidate_sha256':digest(candidate_bytes),
                'source_sha256':digest(source.encode()),'translation_assurance':'source_verified_compiler_trusted',
                'adapter_assurance':'tested_only','integration_tests':'not_run',
                'scope':'Total pure integer function; no parsing, UI, I/O or general Lean translation',
                'trusted_components':['IR to Dafny renderer','Dafny verifier and SMT solver','Dafny compiler and target runtime','decimal-string adapter']}
        destination.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.agentc-translate-',dir=destination.parent) as tmp:
            work=Path(tmp)/'bundle';work.mkdir()
            (work/'Core.dfy').write_text(source)
            target={'python':'py','javascript':'js','rust':'rs'}[a.target]
            command=[dafny,'translate',target,'Core.dfy','--include-runtime','--verification-time-limit',str(a.timeout),'-o','core.'+target]
            if target=='rs': command += ['--enforce-determinism']
            run=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=a.timeout+15)
            report.update(command=command[1:],diagnostics=run.stdout+run.stderr)
            if run.returncode!=0:
                report.update(status='rejected',translation_assurance='not_emitted')
                print(json.dumps(report,indent=2));return 1
            report['status']='verified'
            n=len(c['parameters'])
            if target=='py':
                adapter='''import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'core-py'))
from module_ import default__
def run(values):
    if not isinstance(values, list) or len(values) != COUNT or any(type(v) is not str or len(v) > 4096 or re.fullmatch(r'-?(0|[1-9][0-9]*)', v) is None for v in values):
        raise ValueError('expected COUNT decimal integer strings (max 4096 characters each)')
    return str(default__.Run(*map(int, values)))
if __name__ == '__main__':
    try: print(json.dumps({'value': run(json.load(sys.stdin))}))
    except (ValueError, TypeError) as e:
        print(json.dumps({'error': str(e)})); sys.exit(1)
'''.replace('COUNT',str(n))
                (work/'adapter.py').write_text(adapter)
            elif target=='rs':
                from rust_support import package
                package(work,n)
                report['backend_maturity']='experimental'
                report['target_build']='not_run'
            else:
                # Separate loader exposes lexical declarations without modifying generated source.
                (work/'adapter.cjs').write_text('''const fs = require('fs');
const vm = require('vm');
const path = require('path');
const context = {require, console};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'core.js'), 'utf8') + '\\nthis.agentcRun = (xs) => _module.__default.Run(...xs.map(x => new BigNumber(x))).toFixed();', context);
function run(values) {
  if (!Array.isArray(values) || values.length !== COUNT || values.some(v => typeof v !== 'string' || v.length > 4096 || v.trim() !== v || !/^-?(0|[1-9][0-9]*)$/.test(v))) throw Error('expected COUNT decimal integer strings (max 4096 characters each)');
  return context.agentcRun(values);
}
module.exports = {run};
if (require.main === module) {
  try { console.log(JSON.stringify({value: run(JSON.parse(fs.readFileSync(0, 'utf8')))})); }
  catch (e) { console.log(JSON.stringify({error: e.message})); process.exitCode = 1; }
}
'''.replace('COUNT',str(n)))
                (work/'package.json').write_text(json.dumps({'private':True,'dependencies':{'bignumber.js':'9.1.2'}},indent=2)+'\n')
            (work/'contract.json').write_bytes(raw)
            (work/'candidate.json').write_bytes(candidate_bytes)
            report['files']={str(f.relative_to(work)):digest(f.read_bytes()) for f in sorted(work.rglob('*')) if f.is_file()}
            (work/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
            work.rename(destination)
        print(json.dumps({'status':'emitted','path':str(destination),**{k:report[k] for k in ('contract_fingerprint','candidate_sha256','translation_assurance')}},indent=2));return 0
    except subprocess.TimeoutExpired:
        print(json.dumps({'status':'unknown','message':'toolchain timeout; no output emitted'}));return 1
    except (OSError,ValueError,RecursionError) as e:
        print(json.dumps({'status':'error','message':str(e)}));return 2
