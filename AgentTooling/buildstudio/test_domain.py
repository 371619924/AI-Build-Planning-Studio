import copy,threading,unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from .domain import CATALOG,Invalid,recipe,validate,scad
from .model_fixture import Handler
from .planner import run

class DomainTests(unittest.TestCase):
 def test_supported_recipes(self):
  for ids in [['demo-moisture'],['demo-climate','demo-display'],['demo-led']]:
   result=validate(recipe(ids));self.assertEqual(result['catalog_version'],'fixture-one');self.assertIn('difference()',scad(result));self.assertEqual(len(result['validation_hash']),64)
 def test_catalog_and_shape_rejection(self):
  for plan in [None,{},dict(recipe(['demo-led']),board='invented'),dict(recipe(['demo-led']),modules=['invented']),dict(recipe(['demo-led']),modules=['demo-led','demo-led'])]:
   with self.assertRaises(Invalid):validate(plan)
 def test_wiring_is_exact(self):
  original=recipe(['demo-moisture'])
  candidates=[dict(original,wires=original['wires'][:-1]),dict(original,wires=original['wires']+[original['wires'][0]])]
  wrong=copy.deepcopy(original);wrong['wires'][0]['source']='demo-mcu.5V';candidates.append(wrong)
  for plan in candidates:
   with self.assertRaises(Invalid):validate(plan)
 def test_voltage_mismatch(self):
  with self.assertRaisesRegex(Invalid,'voltage'):validate(recipe(['demo-legacy']))
 def test_current_and_bus_address_rules(self):
  with patch.dict(CATALOG['board'],budget_ma=20):
   with self.assertRaisesRegex(Invalid,'current'):validate(recipe(['demo-climate','demo-display']))
  display=next(m for m in CATALOG['modules'] if m['id']=='demo-display')
  with patch.dict(display,address=64):
   with self.assertRaisesRegex(Invalid,'address'):validate(recipe(['demo-climate','demo-display']))
 def test_dimensions_and_nonfinite_rejected(self):
  for dimension in [True,0,'100',float('nan'),float('inf'),251,20]:
   plan=recipe(['demo-led']);plan['enclosure']['width_mm']=dimension
   with self.assertRaises(Invalid):validate(plan)
 def test_exact_fixture_fit(self):
  plan=recipe(['demo-led']);plan['enclosure']=dict(width_mm=51,depth_mm=26,height_mm=14)
  self.assertEqual(validate(plan)['layout_bounds_mm'],[51,26,14])
 def test_hash_tracks_catalog_and_plan(self):
  plan=recipe(['demo-led']);a=validate(plan);plan['enclosure']['width_mm']+=1;b=validate(plan)
  self.assertNotEqual(a['validation_hash'],b['validation_hash'])

class ProtocolTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.http=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start();cls.endpoint=f'http://127.0.0.1:{cls.http.server_port}/chat/completions'
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.thread.join()
 def test_supported_tool_sequence_and_provenance(self):
  result=run('Plant monitor',self.endpoint)
  self.assertEqual(result['status'],'supported');self.assertEqual([t['action']['name'] for t in result['transcript']],['search_components','validate_build','finish_build']);self.assertEqual(result['external_llm_calls'],0)
 def test_unsupported_explicit(self):self.assertEqual(run('Motor controller',self.endpoint)['status'],'unsupported')
 def test_invented_parts_cannot_finish(self):
  with self.assertRaisesRegex(Invalid,'budget'):run('invented plant part',self.endpoint)
 def test_loop_bound(self):
  with self.assertRaisesRegex(Invalid,'budget'):run('loop',self.endpoint,max_steps=3)
 def test_provider_failure_propagates(self):
  with self.assertRaises(Exception):run('timeout plant',self.endpoint)
 def test_premature_finalization_rejected(self):
  class Policy:
   def __init__(self,*a,**kw):pass
   def next(self,state):return dict(name='finish_build',arguments=dict(validation_hash='fabricated'))
  with patch('buildstudio.planner.ChatPolicy',Policy),self.assertRaisesRegex(Invalid,'budget'):run('plant',self.endpoint,max_steps=2)
 def test_external_provider_not_enabled(self):
  with self.assertRaisesRegex(Invalid,'local scripted'):run('plant','https://remote.invalid/chat/completions')
 def test_bad_prompt(self):
  for prompt in ['',None,'x'*1001]:
   with self.assertRaises(Invalid):run(prompt,self.endpoint)
if __name__=='__main__':unittest.main(verbosity=2)
