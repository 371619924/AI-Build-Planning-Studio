# AgentTooling: Build Planning Studio and API Workflows

The November 2026 Build Planning Studio extends this existing tool runtime with TypeScript/Node.js APIs, a native web editor, synthetic component validation and versioned plans. Start with `buildstudio/README.md`; execute `python verify_studio.py` and `python reproduce_studio.py`. React source is authored but its renderer is unverified. The local model fixture is scripted; there are no external LLM or physical-hardware results.

---

# Agent Tooling - API Workflows and Action-Level Evaluation

Personal project, October-November 2026. This extends the existing retrieval /
experiment-tool prototype with an executed, framework-independent API tool loop,
stateful REST fixtures, action-effect grading and durable agent recovery.

## Run the current extension

Use Python 3.12+ and Pydantic 2.13.4 for the complete reproduction. The API
runtime and its 17 tests use the standard library; four additional tests exercise
the shared Pydantic experiment/report contracts without LangGraph:

```sh
python -m pip install -r requirements.txt
python reproduce_actionbench.py
python -m unittest actionbench.test_runtime -v
python -m actionbench.evaluate
```

The reproduction runs 21 tests and a 144-episode evaluation, then repeats both
from a fresh source directory and compares stable results. This is the same
installed Python/OS; it is not a container, new environment or cloud deployment.
The restart test launches two separate agent Python processes against a
continuing local fixture service and database.

## Implemented components

| File | Responsibility |
| --- | --- |
| `actionbench/world.py` | Real loopback HTTP REST service, paginated record lists, record reads/updates, persistent idempotency receipts and synthetic action effects |
| `actionbench/runtime.py` | Typed tool arguments, scoped pre-execution decisions, native chat/tool protocol adapter, bounded execution loop and SQLite checkpoint journal |
| `actionbench/evaluate.py` | Fixed-policy scenario execution, independent final-state/effect verifier, profile comparison and family-cluster bootstrap |
| `actionbench/test_runtime.py` | Negative grading controls, denied exports/role grants/cross-tenant writes, schema errors, retries, tampering, process restart and native HTTP protocol tests |
| `reproduce_actionbench.py` | Tests/evaluation, log capture and fresh-source stable-result comparison |
| `experiment_tools.py` | Shared original BM25, experiment-loading/comparison and report contracts, refactored to run without LangGraph |
| `agent_lab.py`, `create_fixtures.py`, `evaluate.py` | Retained original BM25 / experiment-tool LangGraph prototype; see the legacy boundary below |

The five native tools are list/read/update records, export records and grant a
role. A public fixture service token deliberately represents a broadly capable
service account. Delegated user scope is narrower: read tenant-A records and
update `rec-0`; no exports or role changes. The action gateway rejects attempts
outside this scope **before HTTP execution**, retaining the denied attempt as a
tool observation. This illustrates a local delegation boundary, not a complete
identity service or security proof. Record handles and the scope are deliberately
small fixture definitions rather than a general policy language.

The API fixture stores every export and role change in SQLite. It never sends an
export, changes a real identity or contacts an external destination. External
destination strings are inert test data. Tenant-B records and synthetic canary
strings provide observable consequences for the guard-removal comparison.
Untrusted record notes contain instruction-like text in the injection scenario;
the fixed attack policy deliberately attempts a prohibited action afterward.

## Recovery and error semantics

Before execution the journal commits an action intent. A stable episode/step/
action key accompanies a write. The REST fixture commits an update, its effect
record and the original response receipt in one SQLite transaction. The runtime
then commits its observation/checkpoint. If an agent process exits in the gap
after the REST effect but before its checkpoint, the next process replays the
pending action under the same key and receives its original receipt, producing
one applied update. A changed payload under the same key conflicts. A synthetic
503 before mutation is retried once. Other HTTP status results remain observations.

Checkpoint digests detect accidental or injected byte changes in the tests;
they do not authenticate against an attacker who can rewrite both data and hash.
Resume binds the episode, delegated scope, guard setting and step budget. The
world service persists while the agent process restarts. Receipts have no expiry
or cleanup. These local atomicity/idempotency checks are not a claim of general
distributed exactly-once delivery, machine-loss recovery or production hardening.

## Recorded evaluation and honest limits

`actionbench/artifacts/evaluation.json` is authoritative:

- Six authored families: benign workflow, instruction-bearing record note,
  exfiltration attempt, role overreach, cross-tenant write and transient retry.
- Eight slot/canary variants per family, three policy/guard profiles: 144 episodes.
  Variants share control flow and are **not independent reasoning tasks**.
- The reference guarded profile completes all 48 variants without prohibited
  effects. The attack policy also completes 48/48 with the guard, which records
  32 blocked attempts and zero prohibited effects.
- Removing the guard from that same attack policy produces 32 prohibited
  simulated effects. All legitimate updates still complete; the independent
  joint task-and-safety score is 16/48 in this profile.
- The verifier checks final record state, actual export/role/update effects and
  required pagination/read observations. A no-op final answer and a shortcut
  update without required observations both fail, even if the text claims success.

Family-cluster bootstrap resamples six family means (2,000 draws, fixed seed),
including a paired guard-on/off difference. It avoids treating slot variants as
independent samples. The observed joint-pass difference is 2/3, with a descriptive
95% interval [1/3, 1]. All-success profiles have degenerate [1,1] intervals in this
fixture. Six authored families are too narrow for an operational population claim.
These intervals describe this synthetic design, not LLM quality or deployment
safety. Logs retain action attempts, denials, HTTP outcomes, replay flags and
applied effects so the aggregate can be inspected.

**All evaluated policies are fixed scripts. No external LLM was called.**
The native chat-completions/function-call adapter was exercised against a real
local HTTP model fixture over five turns, with four accumulated tool results.
There is no measured language-model planning, prompt-injection resistance,
multi-model leaderboard result, model-training improvement or token-price claim.
Model tokens and dollars are recorded as unavailable, rather than fabricated.
Wall times are local diagnostic timings, not model serving latency comparisons.

## Retained retrieval prototype

The original project connects BM25 retrieval, parameterized SQLite experiment
loads and structured numeric comparisons through LangGraph. Its synthetic
observations were generated by known multipliers; they are not training runs.
`LEGACY_README.md`, retained source and `legacy_evidence/` preserve its earlier
evidence and execution limits. The shared retrieval/tools/report path was
refactored and tested against 24 original task oracles in this run, including
rejection of invented sources and incorrect metrics. Its in-memory checkpointer is distinct from the durable
SQLite journal in the new `actionbench/` extension.

The original requirements are retained in `requirements-legacy.txt` and
`requirements.lock.txt`. LangGraph and PyTorch are not installed in the current
execution environment; the legacy LangGraph evaluation was not rerun here.
The new reproduction does not import it or claim its results as fresh execution.
No open-weight LLM fine-tuning, RL, GPU training or quantization is represented.

## References and discussion prompts

The public APIFlow-Bench README at
https://github.com/postmanlabs/APIFlow-Bench was consulted for task/world
separation, deterministic verification, transcript visibility and family-level
uncertainty. This is an independent small project, not an APIFlow-Bench fork,
contribution, compatible task bank or leaderboard submission. No Postman data or
customer API is used; existing project code is retained under its own history.

Prepare to explain: why a final answer is insufficient evidence; attempted versus
applied actions; the write/checkpoint crash gap; who must enforce idempotency;
the independence assumptions behind bootstrap units; limitations of fixed attack
scripts; and which new tests would be required before evaluating a real model.
