# ANIOXAZ Changelog

## 1.0.2 - 2026-10-25

- Validate a requested model path before checking whether `llama-cpp-python` is installed.
- Make application logging safe before the Textual screen stack is mounted.
- Add behavioral tests for model loading, pipeline availability, logging, execution, editor and Philosophy interfaces, terminal execution, and AutoHeal state.
- Confirm all ten ANIOXAZ FRS requirements with NIWOEC 2.1.0.
- Add the expanded FRS verification report and NIWOEC improvement notes.
- Rebuild the ANIOXAZ wheel and source archive for version 1.0.2.

## 1.0.1

- Fix the Textual startup crash caused by the custom `log` method shadowing Textual's internal logger.
- Rename the application output method to `append_log`.
- Update package metadata, README installation instructions, and release validation.

## 1.0.0

- Initial package structure and CLI scaffold.
- Basic Textual app shell and editor flow.
- Initial local-model workflow and packaging metadata.
