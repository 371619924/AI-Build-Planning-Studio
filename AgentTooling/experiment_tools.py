"""Shared retrieval, experiment tools and report contracts, independent of LangGraph."""
import collections,math,re,sqlite3
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class SearchArgs(StrictModel):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=3, ge=1, le=5)

class RunArgs(StrictModel):
    run_id: str = Field(pattern=r'^[a-z0-9_]+$')

class CompareArgs(StrictModel):
    baseline_id: str
    variant_id: str

class Report(StrictModel):
    summary: str = Field(min_length=1)
    citations: list[str] = Field(min_length=1)
    improvement_pct: float = Field(allow_inf_nan=False)

class Action(StrictModel):
    kind: Literal['tool', 'finish']
    name: str = ''
    arguments: dict = Field(default_factory=dict)
    report: dict = Field(default_factory=dict)

def tokens(text):
    return re.findall(r'[a-z0-9]+', text.lower())

class BM25:
    def __init__(self, docs):
        self.docs = docs
        self.words = [tokens(d['title'] + ' ' + d['text']) for d in docs]
        self.average = sum(map(len, self.words)) / len(docs)
        self.df = collections.Counter(w for words in self.words for w in set(words))

    def search(self, query, k=3, method='bm25'):
        scores = []
        for doc, words in zip(self.docs, self.words):
            counts = collections.Counter(words)
            score = 0.0
            for word in set(tokens(query)):
                tf = counts[word]
                if not tf:
                    continue
                if method == 'overlap':
                    score += 1
                else:
                    idf = math.log(1 + (len(self.docs)-self.df[word]+0.5)/(self.df[word]+0.5))
                    norm = 1.2 * (0.25 + 0.75*len(words)/self.average)
                    score += idf * tf * 2.2 / (tf + norm)
            if score > 0:
                scores.append((score, doc))
        scores.sort(key=lambda item: (-item[0], item[1]['id']))
        return [{'id': d['id'], 'title': d['title'], 'text': d['text'], 'score': round(s, 6)}
                for s, d in scores[:k]]

TOOL_MODELS = {'search_knowledge': SearchArgs, 'load_run': RunArgs, 'compare_runs': CompareArgs}
TOOL_SCHEMAS = [
    {'type': 'function', 'function': {'name': name, 'description': description,
                                    'parameters': TOOL_MODELS[name].model_json_schema()}}
    for name, description in [
        ('search_knowledge', 'Retrieve synthetic engineering notes; return source IDs.'),
        ('load_run', 'Load a synthetic experiment run by its identifier.'),
        ('compare_runs', 'Compare two already-loaded runs, using mean MSE reduction.')]]

class Sandbox:
    def __init__(self, corpus, database, transient_failures=0):
        self.retriever = BM25(corpus)
        self.database = database
        self.transient_failures = transient_failures

    def call(self, name, args, state):
        if name not in TOOL_MODELS:
            raise ValueError('unknown tool')
        parsed = TOOL_MODELS[name].model_validate(args)
        if name == 'search_knowledge':
            return {'documents': self.retriever.search(parsed.query, parsed.k)}
        if name == 'load_run':
            if self.transient_failures:
                self.transient_failures -= 1
                raise TimeoutError('injected transient fixture failure')
            with sqlite3.connect(self.database) as db:
                rows = db.execute('SELECT mse FROM observations WHERE run_id=? ORDER BY sample_id',
                                  (parsed.run_id,)).fetchall()
            if not rows:
                raise ValueError('run not found')
            values = [row[0] for row in rows]
            return {'run_id': parsed.run_id, 'samples': len(values), 'mean_mse': sum(values)/len(values)}
        loaded = state.get('loaded', {})
        if parsed.baseline_id not in loaded or parsed.variant_id not in loaded:
            raise ValueError('comparison requires both run observations in memory')
        base, variant = loaded[parsed.baseline_id], loaded[parsed.variant_id]
        if base['mean_mse'] <= 0 or base['samples'] != variant['samples']:
            raise ValueError('invalid comparison baseline or sample count')
        return {'baseline_id': parsed.baseline_id, 'variant_id': parsed.variant_id,
                'baseline_mse': base['mean_mse'], 'variant_mse': variant['mean_mse'],
                'samples_per_run': base['samples'],
                'improvement_pct': 100*(base['mean_mse']-variant['mean_mse'])/base['mean_mse']}


def verify_report(report,observations,comparison):
    parsed=Report.model_validate(report)
    sources={doc["id"] for obs in observations for doc in obs["result"].get("documents",[])}
    if not set(parsed.citations).issubset(sources):raise ValueError("citation not observed by this episode")
    if not comparison or abs(parsed.improvement_pct-comparison["improvement_pct"])>1e-8:
        raise ValueError("metric does not match observed comparison")
    return parsed
