import contextlib,hashlib,io,json,os,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import floating
Z3=os.environ.get('AGENTC_Z3','z3')
b=lambda h:['bits',h]
def bits(v):return b(struct.pack('>d',v).hex())
class FloatingTests(unittest.TestCase):
 def attempt(self,requires,ensures,candidate,ps=['x'],expect=0,override=None,check_only=False,wasm=False):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);p=Path(temp.name)
  c={'schema_version':1,'name':'test','format':'binary64','rounding':'RNE','parameters':ps,'requires':requires,'ensures':ensures}
  raw=json.dumps(c).encode();(p/'contract.json').write_bytes(raw);(p/'candidate.json').write_text(json.dumps({'expression':candidate}))
  args=['--contract',str(p/'contract.json'),'--candidate',str(p/'candidate.json'),'--expect-contract',hashlib.sha256(raw).hexdigest(),'--out',str(p/'out'),'--z3',Z3,'--timeout','5']
  if check_only:args.append("--check-only")
  if wasm:args.extend(["--sqrt-runtime","wasm"])
  stream=io.StringIO()
  with contextlib.redirect_stdout(stream):
   if override:
    with patch.object(floating,'solve',side_effect=override):rc=floating.main(args)
   else:rc=floating.main(args)
  self.assertEqual(rc,expect,stream.getvalue());self.assertEqual((p/'out').exists(),rc==0)
  return p, json.loads(stream.getvalue())
 def test_clamp_total_and_signed_zero(self):
  c=json.loads((ROOT/'floating/clamp/contract.json').read_text());candidate=json.loads((ROOT/'floating/clamp/candidate.json').read_text())['expression']
  p,_=self.attempt(c['requires'],c['ensures'],candidate)
  js=f'''import{{run}}from{json.dumps((p/'out/core.mjs').as_uri())};
  const samples=[NaN,Infinity,-Infinity,-0,0,Number.MIN_VALUE,-Number.MIN_VALUE,1,99.9,100,100.1,Number.MAX_VALUE];
  for(const x of samples){{const want=Number.isNaN(x)||x<0?0:x>100?100:x;if(!Object.is(run(x),want))throw Error('clamp mismatch');}}
  for(const args of [[],['4'],[1,2]]){{let failed=false;try{{run(...args)}}catch{{failed=true}}if(!failed)throw Error('adapter accepted');}}
  '''
  subprocess.run(['node','--input-type=module','-e',js],check=True,capture_output=True)
 def test_rounding_special_values_and_codegen(self):
  cases=[('+','3ff0000000000000','3ca0000000000000','3ff0000000000000'), # tie, even
         ('+','3ff0000000000001','3ca0000000000000','3ff0000000000002'), # tie, odd
         ('+','7fefffffffffffff','7fefffffffffffff','7ff0000000000000'),
         ('*','0000000000000001','3fe0000000000000','0000000000000000'),
         ('*','8000000000000001','3fe0000000000000','8000000000000000'),
         ('/','3ff0000000000000','0000000000000000','7ff0000000000000'),
         ('/','3ff0000000000000','8000000000000000','fff0000000000000'),
         ('/','0000000000000000','0000000000000000','7ff8000000000000'),
         ('-','7ff0000000000000','7ff0000000000000','7ff8000000000000'),
         ('+','8000000000000000','8000000000000000','8000000000000000')]
  for op,x,y,want in cases:
   with self.subTest(op=op,x=x,y=y):
    p,_=self.attempt([['same','x',b(x)],['same','y',b(y)]],[['same','result',b(want)]],[op,'x','y'],['x','y'])
    js=f'''import{{run}}from{json.dumps((p/'out/core.mjs').as_uri())}; const f=h=>{{const d=new DataView(new ArrayBuffer(8));d.setBigUint64(0,BigInt('0x'+h));return d.getFloat64(0)}};if(!Object.is(run(f('{x}'),f('{y}')),f('{want}')))throw Error('IEEE mismatch');'''
    subprocess.run(['node','--input-type=module','-e',js],check=True,capture_output=True)
 def test_real_arithmetic_identity_rejected(self):
  # (1e16 + 1) - 1e16 != 1 in binary64.
  self.attempt([['same','x',bits(1e16)]],[['same','result',bits(1.0)]],['-',['+','x',bits(1.0)],'x'],expect=1)
 def test_signed_zero_is_observable(self):
  self.attempt([['same','x',b('8000000000000000')]],[['same','result','x']],['+','x',bits(0.)],expect=1)
 def test_nan_is_not_equal_to_itself(self):
  self.attempt([['nan','x']],[['==','result','x']],'x',expect=1)
 def test_unsatisfiable_contract_rejected(self):
  _,r=self.attempt([['and',['nan','x'],['finite','x']]],[True],'x',expect=1)
  self.assertEqual(r['status'],'invalid_contract')
 def test_unknown_and_timeout_never_emit(self):
  for responses in [[('unknown','timeout')],[('sat','sat'),('unknown','timeout')],[('sat','sat'),('error','bad solver')]]:
   self.attempt([],[True],'x',expect=1,override=responses)
 def test_unsupported_and_ill_typed_rejected(self):
  for e in [['sqrt','x'],['sin','x'],['+','x',True],['bits','0);(check-sat)'],['if','x','x','x'],1.0]:self.attempt([],[True],e,expect=2)
 def test_predicates_and_conditionals(self):
  self.attempt([],[['finite','result']],['if',['or',['nan','x'],['infinite','x']],bits(0.),['abs','x']])
 def test_preconditions_enforced_in_emitted_code(self):
  p,_=self.attempt([['finite','x']],[['same','result',['neg','x']]],['neg','x'])
  js=f'''import{{run}}from{json.dumps((p/'out/core.mjs').as_uri())};for(const x of [NaN,Infinity,-Infinity]){{let threw=false;try{{run(x)}}catch{{threw=true}}if(!threw)throw Error('precondition ignored')}}'''
  subprocess.run(['node','--input-type=module','-e',js],check=True,capture_output=True)
 def test_sqrt_model_only(self):
  for x,want in [('4010000000000000','4000000000000000'),('bff0000000000000','7ff8000000000000'),('8000000000000000','8000000000000000'),('7ff0000000000000','7ff0000000000000')]:
   p,r=self.attempt([['same','x',b(x)]],[['same','result',b(want)]],['sqrt','x'],check_only=True)
   self.assertFalse((p/'out/core.mjs').exists());self.assertEqual(r['translation_assurance'],'model_only')
  self.attempt([],[True],['sqrt','x'],expect=2)
 def test_floor_ieee_semantics(self):
  for x,want in [(1.9,1.0),(-1.1,-2.0),(-0.0,-0.0),(float('inf'),float('inf')),(float('nan'),float('nan'))]:
   p,r=self.attempt([['same','x',bits(x)]],[['same','result',bits(want)]],['floor','x'])
   h=bits(x)[1];w=bits(want)[1]
   js=f"import{{run}}from{json.dumps((p/'out/core.mjs').as_uri())};const f=h=>{{const d=new DataView(new ArrayBuffer(8));d.setBigUint64(0,BigInt('0x'+h));return d.getFloat64(0)}};if(!Object.is(run(f('{h}')),f('{w}')))throw Error('floor mismatch');"
   subprocess.run(['node','--input-type=module','-e',js],check=True,capture_output=True)
 def test_sqrt_wasm_emission(self):
  for x,want in [('4010000000000000','4000000000000000'),('4000000000000000','3ff6a09e667f3bcd'),('bff0000000000000','7ff8000000000000'),('8000000000000000','8000000000000000'),('7ff0000000000000','7ff0000000000000'),('0000000000000001','1e60000000000000')]:
   p,r=self.attempt([['same','x',b(x)]],[['same','result',b(want)]],['sqrt','x'],wasm=True)
   self.assertEqual(r['sqrt_runtime'],'wasm-f64.sqrt')
   js=f"import{{run}}from{json.dumps((p/'out/core.mjs').as_uri())};const f=h=>{{const d=new DataView(new ArrayBuffer(8));d.setBigUint64(0,BigInt('0x'+h));return d.getFloat64(0)}};if(!Object.is(run(f('{x}')),f('{want}')))throw Error('sqrt mismatch');"
   subprocess.run(['node','--input-type=module','-e',js],check=True,capture_output=True)
 def test_duplicate_keys_and_fingerprint_gate(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'c.json';p.write_text('{"name":"a","name":"b"}')
   with self.assertRaises(ValueError):floating.contract(p)
  with contextlib.redirect_stdout(io.StringIO()):
   rc=floating.main(['--contract',str(ROOT/'floating/clamp/contract.json'),'--candidate',str(ROOT/'floating/clamp/candidate.json'),'--expect-contract','wrong','--out','never-emitted'])
  self.assertEqual(rc,2)
if __name__=='__main__':unittest.main(verbosity=2)
