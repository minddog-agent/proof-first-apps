"""Verify and compile nonnegative integer phase schedules with Dafny 4.11.0."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path

def digest(b):return hashlib.sha256(b).hexdigest()
def main(argv):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--describe',action='store_true');p.add_argument('--expect-contract');p.add_argument('--out');p.add_argument('--dafny',default=os.environ.get('AGENTC_DAFNY','dafny'));a=p.parse_args(argv)
 try:
  source=Path(__file__).parent/'timelines/Timeline.dfy';raw=source.read_bytes();fingerprint=digest(raw)
  if a.describe:print(json.dumps({'contract_fingerprint':fingerprint,'scope':'nonnegative integer phase sequence; exact prefix sums, ordered contiguous boundaries, total conservation'}));return 0
  if a.expect_contract!=fingerprint:raise ValueError('contract fingerprint mismatch')
  if not a.out:raise ValueError('fresh output required')
  out=Path(a.out).resolve()
  if out.exists():raise ValueError('output already exists')
  dafny=shutil.which(a.dafny)
  if not dafny:raise ValueError('Dafny missing')
  version=subprocess.run([dafny,'--version'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
  if not version.startswith('4.11.0'):raise ValueError('Dafny 4.11.0 required')
  out.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(dir=out.parent)as tmp:
   root=Path(tmp);(root/'Timeline.dfy').write_bytes(raw)
   result=subprocess.run([dafny,'translate','js','Timeline.dfy','--include-runtime','--verification-time-limit','30','-o','compiler.js'],cwd=root,capture_output=True,text=True,timeout=90)
   if result.returncode:print(json.dumps({'status':'rejected','diagnostics':result.stdout+result.stderr}));return 1
   compiled=(root/'compiler.js').read_text();needle="const BigNumber = require('bignumber.js');"
   if compiled.count(needle)!=1:raise ValueError('unrecognized compiler module format')
   esm=compiled.replace(needle,"import BigNumber from 'bignumber.js';")+ADAPTER
   receipt={'status':'verified','backend':'dafny-sequence','contract_fingerprint':fingerprint,'source_sha256':digest(esm.encode()),'compiler_sha256':digest(compiled.encode()),'translation_assurance':'source_verified_compiler_trusted','compiler_version':version,'scope':'Build: exact prefix sums, monotonic endpoints, zero origin and conserved total for arbitrary nonnegative integer sequences','trusted_components':['Dafny verifier and compiler','solver','bignumber.js 9.1.2','CommonJS-to-ESM import shim','input/output adapter'],'integration_tests':'not_run'}
   (root/'core.mjs').write_text(esm);(root/'evidence.json').write_text(json.dumps(receipt,indent=2));(root/'verification.log').write_text(result.stdout+result.stderr)
   shutil.copytree(root,out)
  print(json.dumps(receipt,indent=2));return 0
 except (ValueError,OSError,subprocess.SubprocessError)as e:print(json.dumps({'status':'error','message':str(e)}));return 2

ADAPTER = r"""
// Tested adapter. The Dafny-generated Build above is the verified computation.
export function buildTimeline(values) {
  if (!Array.isArray(values) || values.length > 256 || Array.from(values).some(v => typeof v !== 'string' || v.length > 4096 || v.trim() !== v || !/^(0|[1-9][0-9]*)$/.test(v))) throw new TypeError('expected up to 256 nonnegative decimal integer strings');
  const input = _dafny.Seq.of(...values.map(v => new BigNumber(v)));
  return Array.from(_module.__default.Build(input), x => x.toFixed());
}
"""
