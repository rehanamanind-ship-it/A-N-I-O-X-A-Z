ANIOXAZ FRS REPORT
==================

Tool used: NIWOEC 2.1.0
Official repository:
https://github.com/rehanamanind-ship-it/N.I.W.O.E.C.

Purpose
-------
NIWOEC is a deterministic, offline verification tool for checking whether a
source codebase implements the requirements in a Functional Requirements
Specification (FRS). It also checks for placeholder functions and simple
maintainability findings.

Use case
--------
ANIOXAZ uses NIWOEC to compare requirements.frs against src/ and tests/. This
provides repeatable source mapping, test coverage verification, and source
scanning without sending project code or requirements to an LLM, remote service,
or telemetry system. It is suitable for local and air-gapped development.

ANIOXAZ verification
---------------------
- FRS input: requirements.frs
- Source input: src/
- Test input: tests/
- Requirements checked: 10
- Requirements mapped: 10
- Requirements test-pinned: 10
- Requirements satisfied: 10
- Source findings: 0
- Test result: 10 passed

The check command was:

niwoec check requirements.frs src/ --tests tests/

The NIWOEC wheel used for this verification was version 2.1.0. Download the
latest official tool from the repository above, not from an unverified mirror.
