# AI Build Planning Studio

Build Planning Studio uses AgentTooling's chat and tool adapter to search a synthetic component catalog, validate build plans, and save revisions. A TypeScript server serves the browser interface and stores plan history in SQLite.

For local startup commands and sample requests, see [Build Planning Studio](AgentTooling/buildstudio/README.md).

## Reproduce the software checks

Python 3.12+, Pydantic 2.13.4, and Node.js 24.12+ are required. Node runs erasable TypeScript directly; no TypeScript compiler, bundler or third-party Node dependencies are needed for the executed core.

```sh
cd AgentTooling
python -m pip install -r requirements.txt
python verify_studio.py
python reproduce_studio.py
```

These commands generate fixtures, run new domain/protocol tests, actual HTTP tests, Node controller tests, scripted scenario evaluation, and retained agent-runtime checks. The clean-source reproduction uses the same installed Python/Node environment; it is not a new dependency installation or cloud deployment.

## Included

- `AgentTooling/buildstudio/`: runnable new backend, native browser UI, Python planning/domain modules, synthetic catalog and raw verification results.
- `AgentTooling/actionbench/`: retained typed API-agent loop, checkpoint recovery, persistent HTTP fixtures and independent action-effect evaluation.
- `Source_Manifest.json`: file sizes and SHA-256 checksums for the initial source and test materials.

The local provider follows scripted rules. The component catalog contains synthetic data, and the application exports illustrative OpenSCAD source. The [project documentation](AgentTooling/buildstudio/README.md) describes the test coverage and implementation scope.
