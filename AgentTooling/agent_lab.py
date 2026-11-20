"""Agent tooling prototype. Offline results use scripted policies, not an LLM.

LangGraph orchestrates real local retrieval, experiment loading and comparison.
An optional OpenAI-compatible adapter can supply actions; it is never contacted
by the offline evaluation. All corpus documents and experiment rows are synthetic.
"""
from __future__ import annotations
import argparse, collections, json, math, os, re, sqlite3, urllib.request
from pathlib import Path
from typing import TypedDict, Literal
from pydantic import BaseModel, ConfigDict, Field
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

ROOT = Path(__file__).parent

from experiment_tools import Action,Report,BM25,Sandbox,TOOL_SCHEMAS,verify_report

class State(TypedDict, total=False):
    task: dict
    steps: int
    max_steps: int
    action: dict
    observations: list[dict]
    loaded: dict
    comparison: dict
    status: str
    error: str
    report: dict

class ScriptedPolicy:
    """Deliberately fixed control-plane fixture. This is not a learned planner."""
    def __init__(self, fault=''):
        self.fault = fault

    def next(self, state):
        task, step = state['task'], len(state['observations'])
        actions = [
            {'kind': 'tool', 'name': 'search_knowledge', 'arguments': {'query': task['query'], 'k': 3}},
            {'kind': 'tool', 'name': 'load_run', 'arguments': {'run_id': task['baseline']}},
            {'kind': 'tool', 'name': 'load_run', 'arguments': {'run_id': task['variant']}},
            {'kind': 'tool', 'name': 'compare_runs',
             'arguments': {'baseline_id': task['baseline'], 'variant_id': task['variant']}}]
        if self.fault == 'budget_loop':
            return actions[0]
        if step < len(actions):
            action = actions[step]
            if step == 0 and self.fault == 'unknown_tool':
                action['name'] = 'invented_tool'
            if step == 0 and self.fault == 'missing_argument':
                action['arguments'] = {}
            if step == 1 and self.fault == 'missing_run':
                action['arguments']['run_id'] = 'does_not_exist'
            return action
        report = {'summary': 'Synthetic experiment comparison with retrieved engineering context.',
                  'citations': [state['observations'][0]['result']['documents'][0]['id']],
                  'improvement_pct': state['comparison']['improvement_pct']}
        if self.fault == 'invalid_citation':
            report['citations'] = ['invented_source']
        if self.fault == 'wrong_metric':
            report['improvement_pct'] += 10
        if self.fault == 'malformed_report':
            report.pop('improvement_pct')
        return {'kind': 'finish', 'report': report}

class CompatibleHTTPPolicy:
    """Native function-calling HTTP adapter. Tested against a local fixture only."""
    def __init__(self, endpoint, model, api_key=''):
        self.endpoint, self.model, self.api_key = endpoint, model, api_key

    def next(self, state):
        messages = [{'role': 'system', 'content':
                     'Use available tools to retrieve context, load both runs, and compare them. '
                     'Call at most one tool per turn. Finish with a JSON object containing '
                     'summary, citations (retrieved source IDs), and improvement_pct from compare_runs.'},
                    {'role': 'user', 'content': json.dumps(state['task'])}]
        for index, obs in enumerate(state['observations']):
            call_id = f'call_{index}'
            messages += [{'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': call_id, 'type': 'function', 'function':
                 {'name': obs['name'], 'arguments': json.dumps(obs['arguments'])}}]},
                {'role': 'tool', 'tool_call_id': call_id, 'content': json.dumps(obs['result'])}]
        payload = {'model': self.model, 'messages': messages, 'tools': TOOL_SCHEMAS, 'temperature': 0}
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = 'Bearer ' + self.api_key
        request = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            message = json.load(response)['choices'][0]['message']
        calls = message.get('tool_calls', [])
        if calls:
            if len(calls) != 1:
                raise ValueError('only one tool call per turn is supported')
            fn = calls[0]['function']
            return {'kind': 'tool', 'name': fn['name'], 'arguments': json.loads(fn['arguments'])}
        return {'kind': 'finish', 'report': json.loads(message['content'])}

def build_graph(policy, sandbox, checkpoint=True):
    def plan(state):
        if state['steps'] >= state['max_steps']:
            return {'status': 'failed', 'error': 'step budget exhausted'}
        try:
            action = Action.model_validate(policy.next(state))
            if action.kind == 'tool':
                return {'action': action.model_dump(), 'steps': state['steps']+1, 'status': 'running'}
            report = verify_report(action.report,state['observations'],state.get('comparison'))
            return {'status': 'complete', 'report': report.model_dump(), 'steps': state['steps']+1}
        except Exception as exc:
            return {'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}

    def execute(state):
        action = state['action']
        try:
            for attempt in range(1, 3):
                try:
                    result = sandbox.call(action['name'], action['arguments'], state)
                    break
                except TimeoutError:
                    if attempt == 2:
                        raise
            observation = {'name': action['name'], 'arguments': action['arguments'],
                           'attempts': attempt, 'result': result}
            update = {'observations': state['observations']+[observation]}
            if action['name'] == 'load_run':
                update['loaded'] = {**state.get('loaded', {}), result['run_id']: result}
            if action['name'] == 'compare_runs':
                update['comparison'] = result
            return update
        except Exception as exc:
            return {'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}

    graph = StateGraph(State)
    graph.add_node('plan', plan)
    graph.add_node('execute', execute)
    graph.add_edge(START, 'plan')
    graph.add_conditional_edges('plan', lambda state: 'execute' if state['status']=='running' else END)
    graph.add_conditional_edges('execute', lambda state: END if state['status']=='failed' else 'plan')
    return graph.compile(checkpointer=InMemorySaver() if checkpoint else None,
                         interrupt_after=['execute'] if checkpoint else None)

def run_episode(task, corpus, database, policy=None, transient_failures=0, max_steps=8, checkpoint=True):
    sandbox = Sandbox(corpus, database, transient_failures)
    graph = build_graph(policy or ScriptedPolicy(), sandbox, checkpoint)
    config = {'configurable': {'thread_id': task['id']}, 'recursion_limit': 64}
    state = {'task': task, 'steps': 0, 'max_steps': max_steps, 'status': 'running',
             'observations': [], 'loaded': {}}
    result = graph.invoke(state, config)
    resumes = 0
    if checkpoint:
        while graph.get_state(config).next:
            resumes += 1
            result = graph.invoke(None, config)
    result['checkpoint_resumes'] = resumes
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Explicitly enable configured external model call')
    parser.add_argument('--task', type=int, default=0)
    args = parser.parse_args()
    corpus = json.loads((ROOT/'data/corpus.json').read_text())
    tasks = json.loads((ROOT/'data/tasks.json').read_text())
    if args.live:
        policy = CompatibleHTTPPolicy(os.environ['AGENT_MODEL_ENDPOINT'], os.environ['AGENT_MODEL_NAME'],
                                      os.environ.get('AGENT_MODEL_API_KEY', ''))
    else:
        policy = ScriptedPolicy()
    print(json.dumps(run_episode(tasks[args.task], corpus, ROOT/'data/experiments.sqlite', policy), indent=2))
