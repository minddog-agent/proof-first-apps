"""Run from a JS project with bignumber.js installed; requires AGENTC_DAFNY."""
import hashlib,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TimelineTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='.timeline-test-',dir=Path.cwd());cls.root=Path(cls.tmp.name);cls.out=cls.root/'out'
  cls.fingerprint=hashlib.sha256((ROOT/'timelines/Timeline.dfy').read_bytes()).hexdigest()
  cls.tool=['python3',str(ROOT/'agentc.py'),'timeline']
  r=subprocess.run(cls.tool+['--expect-contract',cls.fingerprint,'--out',str(cls.out)],capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_exact_sequences(self):
  code='''import assert from 'node:assert/strict';import {buildTimeline} from %s;
  for(const xs of [[],['0'],['0','1','0'],['9007199254740993','999999999999999999999999999999'],Array(256).fill('999')]){
   let sum=0n;const want=['0'];for(const x of xs){sum+=BigInt(x);want.push(String(sum));}assert.deepEqual(buildTimeline(xs),want);
  }'''%json.dumps(str(self.out/'core.mjs'))
  r=subprocess.run(['node','--input-type=module','-e',code],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
 def test_adapter_rejections(self):
  code='''import assert from 'node:assert/strict';import {buildTimeline} from %s;
  for(const xs of [new Array(1),null,[1],['-1'],['01'],['1.5'],[' 1'],['NaN'],['1\\n'],Array(257).fill('0'),['1'.repeat(4097)]])assert.throws(()=>buildTimeline(xs));'''%json.dumps(str(self.out/'core.mjs'))
  r=subprocess.run(['node','--input-type=module','-e',code],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
 def test_wrong_fingerprint_no_output(self):
  out=self.root/'wrong';r=subprocess.run(self.tool+['--expect-contract','wrong','--out',str(out)],capture_output=True);self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists())
 def test_wrong_recurrence_rejected(self):
  raw=(ROOT/'timelines/Timeline.dfy').read_text();bad=self.root/'Bad.dfy';bad.write_text(raw.replace('ends := ends + [ends[i] + ds[i]];','ends := ends + [ends[i]];'))
  r=subprocess.run([os.environ.get('AGENTC_DAFNY','dafny'),'verify',str(bad),'--verification-time-limit','10'],capture_output=True,text=True,timeout=40);self.assertNotEqual(r.returncode,0);self.assertIn('could not be proved',r.stdout+r.stderr)
 def test_receipt_binds_sources(self):
  e=json.loads((self.out/'evidence.json').read_text());self.assertEqual(e['status'],'verified')
  for key,file in [('contract_fingerprint','Timeline.dfy'),('compiler_sha256','compiler.js'),('source_sha256','core.mjs')]:self.assertEqual(e[key],hashlib.sha256((self.out/file).read_bytes()).hexdigest())
if __name__=='__main__':unittest.main(verbosity=2)
