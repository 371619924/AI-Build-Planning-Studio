# Build Planning Studio

Personal extension, November 2026. A local product-planning workflow layered onto AgentTooling's existing `ChatPolicy` transport. It implements component discovery, structured build proposals, deterministic validation, editable revisions and an illustrative enclosure-source export.

## Start the local application

From `AgentTooling/`, start these in separate terminals:

```sh
python -m buildstudio.model_fixture --port 8091
BUILD_PYTHON=python node buildstudio/server.ts
```

Open `http://127.0.0.1:8080`. The server binds loopback. `BUILD_DB`, `PORT`, `BUILD_PYTHON`, and `MODEL_ENDPOINT` can configure paths/runtime/ports. The planning loop intentionally accepts only a local HTTP model fixture endpoint. Do not send real hardware requirements or personal information. The public bearer value `demo-local` is a fixture, not a production identity system.

Examples recognized by the scripted provider: **Plant moisture monitor**, **Climate monitor with display**, **Indicator light**. Unsupported motor/battery requests receive an explicit unsupported result. This fixture uses keyword rules and fixed tool policies; it is not a natural-language understanding model. Other wording may be interpreted incorrectly. Broad prompt coverage, planning quality and prompt-injection resistance have not been measured.

## Data flow

1. A native JavaScript editor POSTs a prompt and retry key to the TypeScript/Node.js host.
2. The host starts a bounded Python planning process, which reuses the existing native chat-completions/tool transport with new domain-specific schemas and instructions.
3. The workflow searches a versioned synthetic catalog, validates a complete build, and finishes only with the latest successful validation hash. Errors become tool observations for correction. Budget exhaustion, missing validation and provider errors fail explicitly.
4. The Node host commits the plan, revision and create receipt atomically in SQLite. Edits must provide the expected version and pass the same Python domain validator.
5. The UI renders build details and supports plan JSON editing, reload after conflicts and OpenSCAD source download. Its shared state controller guards duplicate pending actions and late responses, retains drafts on conflict, and reuses a create key after an uncertain failure.

## Domain rules and geometry boundary

The catalog has one synthetic controller and five synthetic modules (including a deliberately incompatible legacy module). Rules cover voltage equality, a current budget, I2C address collisions, exact catalog-derived wiring, unique module IDs, finite millimeter dimensions and a fixed left-to-right bounding-box layout with 3mm gaps. Current-budget and address-conflict negative tests temporarily alter fixture parameters; they do not represent measured electrical properties.

Assembly guidance is derived from the validated wire list. The geometry adapter emits an open-top OpenSCAD shell with source dimensions and a validation hash. It does not execute OpenSCAD or validate connector access, printable tolerances, wall strength, thermal behavior, battery safety or assembly feasibility. No firmware generation, CAD kernel, mesh repair, circuit simulation or physical prototype exists in this project.

All components, dimensions and compatibility properties are authored fixtures. They are not Makeable's component library and must not be used as real wiring guidance.

## HTTP and consistency behavior

- `GET /api/catalog`: versioned synthetic component library.
- `POST /api/plans`: exact `{"prompt":"Plant moisture monitor"}` body and `Idempotency-Key` of 8-64 letters, digits, underscores or hyphens.
- `GET /api/plans/<id>` and `/history`: saved plan and ordered revisions.
- `PATCH /api/plans/<id>`: exact `expected_version` and complete `plan`; validation precedes a conditional version update and history insert in one transaction.
- `GET /api/plans/<id>/enclosure.scad`: source export for supported builds only.

All API routes require the fixture bearer value. A create-key replay returns the same plan identity and its **current** saved revision, not necessarily the original creation response. Changed content under the same key conflicts. Concurrent identical creates coalesce within the one running Node host; durable receipts preserve identity after restart. This does not implement cross-process coalescing across multiple Node workers. SQLite operations are synchronous, designed for a small local demo, not a throughput benchmark.

Concurrent versioned edits allow one writer; rejected validation/conflicts do not append history. There is no edit-request receipt: if an edit response is lost, reload to see whether the version advanced. No receipt expiry, authentication integration, TLS termination, distributed queue, multi-tenant isolation, rate limiting or production deployment is implemented.

## Verification and scope

Run `python verify_studio.py` and `python reproduce_studio.py` from the parent directory. Evidence in `evidence/` retains stage logs, HTTP responses and model-protocol transcripts. New domain/protocol tests, Node HTTP/controller tests, twelve authored scenarios and the retained runtime evaluation are separate layers and overlap; they are not an independent-test or coverage percentage.

The twelve scripted scenarios cover four supported outcomes (including an invalid-wiring repair), three explicit unsupported outcomes and five expected failures. All use a deterministic local provider. Passing is software contract behavior, not LLM accuracy, hardware correctness or measured customer impact. The existing 144-episode runtime evaluation remains six scenario families with eight variants and three fixed policy/guard profiles.

`server.ts` and `test_server.ts` execute through Node's native type stripping. The `tsc` compiler was unavailable, so static type checking was not executed. `web/ReactStudio.mjs` is an optional React component adapter with syntax checks only; React is not needed for the native UI and its renderer was not executed. Next.js is not implemented. HTML/JS delivery and controller behavior are tested; browser DOM, accessibility tooling, hosted deployment, real model APIs and physical builds are unverified.

## Source map and design references

- `domain.py`: catalog lookup, compatibility/layout rules, validation hash and enclosure-source adapter.
- `planner.py`: bounded search/validate/finish tool loop using the retained `ChatPolicy` transport.
- `model_fixture.py`: deterministic local protocol fixture; includes repair/failure scenarios.
- `server.ts`: local API, Python process bridge, SQLite plans/history/receipts.
- `web/ui_model.mjs`: framework-independent client state; `app.mjs`: native DOM adapter; `ReactStudio.mjs`: optional React source.
- `test_domain.py`, `test_server.ts`, `test_ui.mjs`, `evaluate.py`: executable checks and authored scenarios.

Official Node TypeScript type-stripping and SQLite documentation informed the runtime choice. Zoo Design Studio's public README (`https://github.com/KittyCAD/modeling-app`) was read for human-readable design artifacts and separation of interface actions from geometry execution. This is independent source, not a Zoo contribution, fork or compatible CAD implementation. No third-party source was copied.
