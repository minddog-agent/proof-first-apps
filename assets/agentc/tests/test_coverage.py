import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from coverage_gate import audit
class CoverageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  for f in ['core.mjs','contract.json','candidate.json','verification.smt2']:(self.p/f).write_text('fixture '+f)
  h=lambda f:hashlib.sha256((self.p/f).read_bytes()).hexdigest()
  self.r={'backend':'z3-smtlib-fp','status':'verified','translation_assurance':'source_verified_renderer_trusted','source_sha256':h('core.mjs'),'contract_fingerprint':h('contract.json'),'candidate_sha256':h('candidate.json'),'smt_sha256':h('verification.smt2')}
  (self.p/'receipt.json').write_text(json.dumps(self.r))
  self.c={'id':'core','requirements':['distance'],'depends_on':[],'status':'proved','sources':{'core.mjs':h('core.mjs')},'receipt':'receipt.json','integrated':True}
  self.m={'schema_version':1,'scope':'test fixture only','requirements':['distance'],'components':[self.c]}
 def run_audit(self):
  (self.p/'coverage.json').write_text(json.dumps(self.m));return audit(self.p/'coverage.json',self.p)
 def test_consistent_fixture_never_claims_full_app(self):
  r=self.run_audit();self.assertEqual(r['status'],'declared_coverage_complete');self.assertFalse(r['full_app_verified'])
 def test_dafny_sequence_receipts_and_tampering(self):
  for f in ['Timeline.dfy','compiler.js']:(self.p/f).write_text('fixture '+f)
  h=lambda f:hashlib.sha256((self.p/f).read_bytes()).hexdigest()
  self.r.update(backend='dafny-sequence',translation_assurance='source_verified_compiler_trusted',contract_fingerprint=h('Timeline.dfy'),compiler_sha256=h('compiler.js'))
  (self.p/'receipt.json').write_text(json.dumps(self.r))
  self.assertEqual(self.run_audit()['status'],'declared_coverage_complete')
  (self.p/'compiler.js').write_text('changed')
  self.assertEqual(self.run_audit()['status'],'gaps')
 def test_changed_source(self):
  (self.p/'core.mjs').write_text('changed');self.assertEqual(self.run_audit()['status'],'gaps')
 def test_changed_contract(self):
  (self.p/'contract.json').write_text('changed');self.assertEqual(self.run_audit()['status'],'gaps')
 def test_model_only_is_not_app_proof(self):
  self.r['translation_assurance']='model_only';(self.p/'receipt.json').write_text(json.dumps(self.r));self.assertEqual(self.run_audit()['status'],'gaps')
 def test_unmapped_requirement(self):
  self.m['requirements'].append('ui');self.assertEqual(self.run_audit()['status'],'gaps')
 def test_unintegrated_and_trusted(self):
  self.c['integrated']=False;self.c['status']='trusted';self.assertEqual(len(self.run_audit()['gaps']),2)
 def test_dependency_validation(self):
  self.c['depends_on']=['missing']
  with self.assertRaises(ValueError):self.run_audit()
  self.c['depends_on']=['core']
  with self.assertRaises(ValueError):self.run_audit()
 def test_path_escape(self):
  self.c['sources']={'../outside': '0'*64}
  with self.assertRaises(ValueError):self.run_audit()
if __name__=='__main__':unittest.main(verbosity=2)
