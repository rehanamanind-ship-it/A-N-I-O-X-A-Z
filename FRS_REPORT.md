# ANIOXAZ FRS Verification Report

## Tool and inputs

- Tool: `niwoec` 2.1.0
- FRS: `requirements.frs`
- Source: `src/`
- Tests: `tests/`
- Check command: `niwoec check requirements.frs src/ --tests tests/`

## Result

The source mapping completed successfully. NIWOEC found source links for all ten requirements, all ten requirements are pinned by behavioral tests, and the source scan reported no findings.

| Requirement | Source mapped | Test-pinned | NIWOEC verdict |
| --- | --- | --- | --- |
| `AutoHeal` | Yes | Yes | Satisfied |
| `CodeExecutor` | Yes | Yes | Satisfied |
| `EditorScreen` | Yes | Yes | Satisfied |
| `Philosophy` | Yes | Yes | Satisfied |
| `Terminal` | Yes | Yes | Satisfied |
| `anioxaz` | Yes | Yes | Satisfied |
| `append_log` | Yes | Yes | Satisfied |
| `detect_language` | Yes | Yes | Satisfied |
| `load_model` | Yes | Yes | Satisfied |
| `run_pipeline` | Yes | Yes | Satisfied |

## Interpretation

NIWOEC's `check` command requires a requirement to be both mapped to source and referenced by the test input. The current test suite now exercises and pins all ten requirements.

The separate `map`, `verify`, and `scan` commands reported:

- All ten requirements were mapped to one or more source files.
- Pinned requirements: all ten requirements in `requirements.frs`.
- Source scan findings: none.

## Installation verification

The requested wheel was installed successfully into the project virtual environment:

```text
niwoec-2.1.0
```

## Fixes made during verification

- Model loading now validates the requested file path before reporting the optional `llama-cpp-python` dependency state.
- Application logging now updates history safely before Textual has mounted a screen.
- Added behavioral tests for model loading, pipeline availability, logging, execution, editor and Philosophy interfaces, terminal execution, and AutoHeal state.

## Why NIWOEC was used

NIWOEC means deterministic offline verification of source code against a
Functional Requirements Specification. It was built to provide a repeatable
way to check whether a local source tree implements the requirements described
by an FRS, while also identifying placeholder functions and simple maintainability
findings.

The main use case is local or air-gapped software verification. A developer can
write requirements in `requirements.frs`, point NIWOEC at `src/` and `tests/`,
and receive deterministic mapping, behavioral-test coverage, and source-scan
results without sending code or requirements to an LLM, remote service, or
telemetry endpoint.

## Official NIWOEC download

The official NIWOEC repository is owned by `rehanamanind-ship-it`:

https://github.com/rehanamanind-ship-it/N.I.W.O.E.C.

The repository is the correct place to download the latest NIWOEC source or
release artifacts. The lowercase URL without the punctuation is not the
official repository URL and returned a 404 during verification. The local
2.1.0 wheel used for this report was installed before being removed to keep the
ANIOXAZ release directory clean.
