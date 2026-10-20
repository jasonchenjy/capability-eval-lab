# Preserve text when splitting and indenting lines

In the provided Boltons checkout, `strutils.iter_splitlines` sometimes splits ordinary text in the middle of a date, and does not consistently recognize Unicode line/paragraph separators. `indent` inherits these problems. For example, `February 28, 2026` must remain a single line.

Repair the implementation while preserving the documented iterator behavior, supported line endings, leading/trailing empty lines and indentation behavior. Do not change public APIs or introduce dependencies. Only the string literal supplied to `_line_ending_re = re.compile(...)` in `boltons/strutils.py` may change. Keep every byte outside that literal unchanged, including API bodies, imports, flags and comments. Supply one ordinary or raw Python string literal (not an expression, f-string or bytes literal), at most 4096 UTF-8 bytes. Other implementations are unsupported/invalid in this bounded task, even if functionally correct. Leave tests, project configuration and all other files unchanged.

The public repository includes pytest tests and doctests. A separate black-box verifier exercises the existing `iter_splitlines(text)` and `indent(text, margin, newline)` APIs through a fixed JSON adapter. It does not require a particular implementation. No network or dependency installation is available during evaluation.

This task does not prescribe a search tool. Phase 5A only qualifies the task and verifier; it does not measure command recovery yet.
