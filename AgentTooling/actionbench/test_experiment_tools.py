import json,unittest
from pathlib import Path
from pydantic import ValidationError
from experiment_tools import BM25,Sandbox,verify_report

ROOT=Path(__file__).resolve().parents[1]
class ExperimentToolTests(unittest.TestCase):
    def setUp(self):
        self.corpus=json.loads((ROOT/'data/corpus.json').read_text())
        self.tasks=json.loads((ROOT/'data/tasks.json').read_text())
        self.sandbox=Sandbox(self.corpus,ROOT/'data/experiments.sqlite')
    def test_retrieval_and_numeric_comparison_match_original_task_oracles(self):
        for task in self.tasks:
            observations=[];state={'loaded':{}}
            for name,args in [('search_knowledge',{'query':task['query'],'k':3}),
                ('load_run',{'run_id':task['baseline']}),('load_run',{'run_id':task['variant']}),
                ('compare_runs',{'baseline_id':task['baseline'],'variant_id':task['variant']})]:
                result=self.sandbox.call(name,args,state);observations.append({'result':result})
                if name=='load_run':state['loaded'][result['run_id']]=result
            self.assertIn(task['expected_source'],[d['id'] for d in observations[0]['result']['documents']])
            self.assertAlmostEqual(result['improvement_pct'],task['expected_improvement_pct'])
            report={'summary':'Fixture experiment comparison','citations':[task['expected_source']],'improvement_pct':result['improvement_pct']}
            self.assertEqual(verify_report(report,observations,result).citations,[task['expected_source']])
    def test_fabricated_source_and_metric_are_rejected(self):
        observations=[{'result':{'documents':[{'id':'observed'}]}}]
        for report in [{'summary':'x','citations':['invented'],'improvement_pct':1},
                       {'summary':'x','citations':['observed'],'improvement_pct':99}]:
            with self.assertRaises(ValueError):verify_report(report,observations,{'improvement_pct':1})
    def test_invalid_tool_schema_and_unloaded_comparison_are_rejected(self):
        with self.assertRaises(ValidationError):self.sandbox.call('load_run',{'run_id':'../other'}, {})
        with self.assertRaises(ValueError):self.sandbox.call('invented',{}, {})
        with self.assertRaises(ValueError):self.sandbox.call('compare_runs',{'baseline_id':'a','variant_id':'b'}, {'loaded':{}})
    def test_retrieval_comparison_does_not_invent_a_gain(self):
        queries=json.loads((ROOT/'data/retrieval_queries.json').read_text());index=BM25(self.corpus)
        recalls={method:sum(any(d['id']==q['relevant_id'] for d in index.search(q['query'],3,method)) for q in queries)/len(queries) for method in ['overlap','bm25']}
        self.assertEqual(recalls,{'overlap':1,'bm25':1})

if __name__=='__main__':unittest.main(verbosity=2)
