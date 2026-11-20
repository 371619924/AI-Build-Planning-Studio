"""Generate transparent synthetic fixtures; no Bosch/customer/proprietary data."""
import json, random, sqlite3
from pathlib import Path
ROOT=Path(__file__).parent
(ROOT/'data').mkdir(exist_ok=True)
notes=[
 ('thermal','Thermal drift calibration','Temperature drift in a sensor changes its baseline. Compare calibrated and uncalibrated residual mean squared error on matched samples; a lower residual does not alone establish field reliability.'),
 ('dropout','Missing sensor observations','Sensor dropout creates missing observations. Compare an imputation variant with the baseline on a held-out sequence and report the missingness rate and reconstruction error.'),
 ('vibration','Vibration reconstruction','A vibration autoencoder reconstructs sampled machine signals. Reconstruction mean squared error can identify changed operating conditions, but threshold calibration and labeled validation are separate experiments.'),
 ('energy','Energy demand residuals','Energy demand forecasting residuals measure errors between predicted and observed power. Align timestamps and units before comparing smoothing or feature variants.'),
 ('cache','Cache expiry reliability','Simultaneous cache expiration causes a cache stampede. Dynamic TTL and rate limiting reduce request bursts; measure peak throughput on the same workload rather than extrapolating to all requests.'),
 ('sort','Aligned catalog sorting','Time, magnitude, position and class labels must share one sorting permutation. Sorting each column independently destroys event alignment and invalidates subsequent analysis.'),
 ('fft','Fourier stress synthesis','Conjugate-symmetric Fourier coefficients and an inverse two-dimensional FFT synthesize real stress fields. Compare runtime for the same grid and preserve the intended spatial correlation.'),
 ('ema','Exponential moving averages','Irregular events first become fixed-interval counts. Normalized exponential moving-average weights smooth count histories; the observation interval and decay parameter change the interpretation.'),
 ('retry','Retry semantics','Retry a failed tool only if its operation is idempotent or deduplicated. A bounded retry count prevents indefinite loops, while a checkpoint records completed tool observations.'),
 ('sources','Evidence attribution','An experimental report associates factual claims with retrieved source identifiers and observed run metrics. Source presence validates attribution, not semantic entailment or factual truth.'),
 ('evaluation','Controlled evaluation','Use separate training and evaluation sets. Compare ablations on matched workloads, record random seeds, and distinguish a scripted control-plane test from model reasoning accuracy.'),
 ('safety','Industrial deployment scope','An offline synthetic prototype does not control machinery. Field deployment requires domain-specific validation, permissions, monitoring and independently reviewed operational procedures.')]
corpus=[{'id':i,'title':t,'text':x,'provenance':'Synthetic engineering note'} for i,t,x in notes]
(ROOT/'data/corpus.json').write_text(json.dumps(corpus,indent=2))
queries=[('thermal','sensor temperature drift calibrated residual'),('dropout','missing observations imputation dropout'),('vibration','vibration autoencoder reconstruction'),('energy','energy demand forecasting power residual')]
randomizer=random.Random(298112)
dbpath=ROOT/'data/experiments.sqlite'
dbpath.unlink(missing_ok=True)
tasks=[]
with sqlite3.connect(dbpath) as db:
 db.execute('CREATE TABLE observations (run_id TEXT, sample_id INTEGER, mse REAL NOT NULL, PRIMARY KEY(run_id,sample_id))')
 for topic,query in queries:
  for variant in range(6):
   baseline=f'{topic}_{variant}_base';candidate=f'{topic}_{variant}_candidate'
   factor=0.70+variant*0.025
   values=[round(randomizer.uniform(.1,1.0),9) for _ in range(32)]
   for run,scale in [(baseline,1.0),(candidate,factor)]:
    db.executemany('INSERT INTO observations VALUES (?,?,?)',[(run,i,x*scale) for i,x in enumerate(values)])
   tasks.append({'id':f'{topic}_{variant}','query':query,'baseline':baseline,'variant':candidate,
                 'expected_source':topic,'expected_improvement_pct':100*(1-factor)})
(ROOT/'data/tasks.json').write_text(json.dumps(tasks,indent=2))
retrieval_queries=[{'query':q,'relevant_id':i} for i,q in queries]+[
 {'query':'cache expiration stampede TTL request bursts','relevant_id':'cache'},
 {'query':'preserve event position magnitude sorting permutation','relevant_id':'sort'},
 {'query':'conjugate symmetric Fourier real stress field','relevant_id':'fft'},
 {'query':'irregular events fixed interval exponential weights','relevant_id':'ema'},
 {'query':'idempotent failed tool bounded retry','relevant_id':'retry'},
 {'query':'retrieved source identifiers factual attribution','relevant_id':'sources'},
 {'query':'matched workloads ablation random seeds','relevant_id':'evaluation'},
 {'query':'offline prototype machinery field validation','relevant_id':'safety'}]
(ROOT/'data/retrieval_queries.json').write_text(json.dumps(retrieval_queries,indent=2))
print(json.dumps({'documents':len(corpus),'tasks':len(tasks),'runs':len(tasks)*2,'rows':len(tasks)*64,'retrieval_queries':len(retrieval_queries)}))
