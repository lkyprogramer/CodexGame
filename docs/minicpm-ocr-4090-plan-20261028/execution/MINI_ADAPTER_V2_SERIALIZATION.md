# Mini adapter v2: mixed math document serialization

`mini-adapter-v2` fixes local postprocessing and Markdown assembly only. The pinned
SDK revision remains `62d5e649c32be2271f2c8c66ec8307f3d7373903`.

The observed full-page `PAPER-026-p014` block 3 contains two balanced inline math
spans. The SDK's outer-pair stripping crosses those spans and removes the first
opening and final closing delimiters. The three R0 formula regions
`chem-q2-cd`, `math-q2`, and `physics-q1` contain prose and multiple balanced inline
math spans; wrapping the complete content in display math creates nested math.
Those four syntax-failing raw strings are regression fixtures in `tests/test_mini.py`.
A subsequent full-corpus impact audit found a fifth changed block:
`R0-STRUCT-physics-q3-graph-options` block 0, containing one display math span
with axis labels followed by four prose answer options. Its old serialization
was valid as a whole math expression, but placed the options inside math. V2
preserves the original display span and prose boundaries. This fifth exact raw
string is also a fixture; it is a formatting correction, not a fifth syntax failure.
They contain no student identifiers.

For formula labels, the adapter recognizes complete `\(...\)`, `\[...\]`,
`$...$`, and `$$...$$` spans, consuming escaped dollars, braces, and backslashes first. Delimiters inside
TeX brace groups do not count as document-level spans. A closing inline `$`
consumes one dollar even when followed immediately by another inline opening `$`.
Multiple spans, or non-whitespace content outside a complete span, identify a
`mixed_math_document`. Its `content`, `text`, and `formula_latex` contain the raw
string with outer whitespace stripped; Markdown uses that string directly.
`raw_content` and `raw_text` retain the original string. A `single_latex` keeps
the existing SDK postprocessor and label-specific math wrapper. The classifier
is a delimiter scanner, not a TeX parser, and performs no semantic formula repair.

Every page result includes `adapter_version: mini-adapter-v2`. Successful formula
blocks include `formula_representation: mixed_math_document` or `single_latex`.
For `mixed_math_document`, `formula_latex` is a math-containing document rather
than a single expression: render audits must inspect each math span separately.
This test suite establishes serialization preservation, not browser/TeX render
acceptance or model recognition accuracy.

No old candidate results were rewritten. No remote requests were made. SDK code,
prompts, sampling, and model input are unchanged. Historical quality scores do
not change on the basis of these local tests.

## Verification

The following command was run from the repository root before and after the
adapter change, using the same newly added regression tests:

```sh
PYTHONPATH=docs/minicpm-ocr-4090-plan-20261028/execution /private/tmp/ocr-full-test-20261029/bin/python -m unittest discover -s docs/minicpm-ocr-4090-plan-20261028/execution/tests -p test_mini.py
```

- Red on the original adapter: 13 tests; 16 subtest failures and 18 subtest errors
  (including absent v2 metadata). Log: `/private/tmp/mini-adapter-v2-red.log`.
- Initial green on v2: 13 tests passed. Log: `/private/tmp/mini-adapter-v2-green.log`.
- Independent SDK/render review found adjacent inline spans `$x$$y$` and
  math inside a TeX argument `\text{if $x>0$}, x^2` needed scanner fixes.
  Two fixed-expected-value regression tests reproduced these before correction:
  15 tests, 3 failures. Log: `/private/tmp/mini-adapter-v2-review-red.log`.
- Final green after those corrections and escaped-brace/backslash cases:
  15 tests passed. Log: `/private/tmp/mini-adapter-v2-review-green.log`.
  The four original captured fixtures remain covered.
- After adding the fifth exact raw formatting fixture, the complete suite still
  passed: 15 tests. Log: `/private/tmp/mini-adapter-v2-five-fixture-green.log`.
  `mini.py` was unchanged for this fixture-only addition.
- Direct execution of the pinned SDK `markdown.py` and `latex_repair.py` source
  confirmed display processing returns `xy` for `$x$$y$`, and preserves
  `\text{if $x>0$}, x^2` unchanged. Its normal package import was unavailable
  because this test environment lacks `pydantic`; loading the original two
  source modules through a temporary in-memory package avoided unrelated imports.
  No SDK source or model was changed or substituted.
- Tests execute the complete `MiniAdapter.process_page` path with fake local
  model responses and a mock reproducing the SDK's actual outer-pair stripping.
  They cover the five observed raw outputs, Chinese prose/labels, all four
  delimiter styles, escaped dollars, unchanged single-expression SDK calls and
  wrappers, plus the existing adapter cases.
- Full repository tests and actual model inference were not run for this local
  serialization change. Actual rendering is a separate audit.

SHA-256:

```text
135321e34ca69592c2d43e778f3b0811f713b892b552516b598065de92280933  ocrbench/mini.py
d811e660912d0b933b615b139a8bc18041f784339281099bd7fa5ba236476be6  tests/test_mini.py
1ba9016e3922ba79a0ad96e8a54529f271220c571df5c6416260c638f605e04d  /private/tmp/mini-adapter-v2-red.log
207d4396cdeb6959a19be532c44af04c8193e807883c47e9c4e20a6a03e90c8c  /private/tmp/mini-adapter-v2-green.log
e25b148c94cc5a7c8d9b588acc8555d318580660321dee4419351f595e25663b  /private/tmp/mini-adapter-v2-review-red.log
343990f02ba6eb137fb305eb7a9e3493b36764c2e1073fb6d3eecfd52b3ff32a  /private/tmp/mini-adapter-v2-review-green.log
343990f02ba6eb137fb305eb7a9e3493b36764c2e1073fb6d3eecfd52b3ff32a  /private/tmp/mini-adapter-v2-five-fixture-green.log
```
