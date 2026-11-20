> Retained October prototype notes. The full LangGraph loop was not rerun in the current environment. Historical outputs are in legacy_evidence/; the shared retrieval/experiment/report code is now in experiment_tools.py and was verified separately in the current 21-test reproduction. Re-running the old evaluate.py requires the legacy dependencies and writes new outputs to artifacts/.

# Agent Tooling & Evaluation Prototype

Personal project | October 2026. A local Agent tooling and evaluation prototype
connecting retrieval, experiment tools, stateful execution and reproducible
control-plane evaluation.

## What actually runs

Python and LangGraph execute a stateful plan/tool loop connecting three tools:

1. `search_knowledge`: BM25 ranking over 12 synthetic engineering notes.
2. `load_run`: parameterized SQLite loading of synthetic experiment observations.
3. `compare_runs`: mean reconstruction-error comparison using previously loaded
   tool results; output includes experiment IDs, sample counts and metrics.

Pydantic validates action arguments and final-report structure. Each episode
records tool inputs/results, observes a step budget, retries a transient tool
timeout at most once, and checks that reported source IDs and comparison metrics
were observed in that episode. LangGraph's `InMemorySaver` retains state between
tool-node interruptions and resumes in the **same process**. This is neither a
persistent database checkpointer nor crash/restart recovery.

The model policy is interchangeable:

- The default `ScriptedPolicy` emits a predetermined sequence. This isolates
  retrieval, tool execution, state, report contracts and recovery for repeatable
  evaluation. It has **no learned planning or LLM reasoning**.
- `CompatibleHTTPPolicy` sends native function-call tool schemas and tool-result
  histories to a configured OpenAI-compatible Chat Completions endpoint. The
  adapter was tested against a loopback scripted HTTP server. **No external LLM
  was called, and no external model's compatibility or reasoning was validated.**

## Reproduce

Python 3.12 was used. In a fresh environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-legacy.txt
python3 create_fixtures.py
python3 evaluate.py
python3 agent_lab.py --task 0
```

The offline commands contact no model service. `create_fixtures.py` recreates the
synthetic SQLite database and JSON fixtures. Results and complete traces are
under `artifacts/`; expected answers and source labels are visible in `data/`.

To try an external model yourself, configure `AGENT_MODEL_ENDPOINT`,
`AGENT_MODEL_NAME`, and optionally `AGENT_MODEL_API_KEY`, then explicitly run
`python3 agent_lab.py --live`. Endpoint must be the full Chat Completions URL.
The adapter supports one tool call per turn and JSON final reports. Model-specific
behavior remains to be evaluated. No credential is included in this package.

## Recorded evaluation

See `artifacts/summary.json` for authoritative values and versions.

- 24 multi-step scripted episodes passed independent fixture oracles for source
  selection, numeric comparison, four tool observations and four checkpoint
  resumes per episode (96 total resumes).
- Eight injected scenarios produced the expected outcome: unknown tool, missing
  argument, unknown experiment, invented citation, incorrect reported metric,
  malformed final report, exhausted step budget, and recovered transient timeout.
- One local HTTP adapter integration passed five request/response turns with
  native tool schemas and four accumulated tool results.
- Retrieval comparison used 12 hand-authored labeled queries over 12 synthetic
  notes. **BM25 and token overlap both achieved Recall@3 = 1 and MRR@3 = 1.**
  There is no demonstrated BM25 improvement on this easy set. The queries and
  labels are not a held-out natural-language benchmark.
- 48 synthetic experiment runs contain 1,536 rows. Candidate values are generated
  by a known multiplier for an independent numeric oracle. These are not model
  training experiments or observed industrial performance improvements.
- External LLM calls: **0**. No accuracy result for an LLM is asserted.

This is a control-plane and evaluation-scaffolding demonstration, not novel
Agentic AI research. Citation membership does not establish semantic entailment.
It does not implement reinforcement learning, post-training, autonomous discovery,
multi-agent collaboration, production deployment, or hardware control.

## Useful extensions to own and discuss

Add a larger held-out question set with relevance judgments made before tuning;
compare actual tool-calling models using the same task contracts; measure task
completion, tool errors, retrieval recall and token/latency cost separately;
replace in-memory checkpoints with durable persistence and test interruption
recovery; run semantic citation evaluation. These are proposed next steps,
not completed results.

## Source basis

The project implements original, small-scale application code using the public
LangGraph API. Framework reference:
https://docs.langchain.com/oss/python/langgraph/overview

All engineering notes, run values and relevance labels were authored as synthetic
fixtures for this work sample. They contain no Bosch data or claimed customer
research results. Existing CV internship and research facts are not used as
synthetic experimental outcomes.
