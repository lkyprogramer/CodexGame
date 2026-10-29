# Offline formula renderability

This directory freezes `mathjax-full` at **3.2.2**, including transitive dependencies
in `package-lock.json`. Tested with Node **22.16.0** and npm **10.9.2**.
Install once; evaluation uses local packages, SVG liteAdaptor, and no browser or network.

From the repository root:

```bash
npm ci --prefix docs/minicpm-ocr-4090-plan-20261028/execution/formula-renderer --ignore-scripts
node docs/minicpm-ocr-4090-plan-20261028/execution/evaluate_formulas.mjs \
  --input formulas.json --out /absolute/path/to/new-results
```

The evaluator defaults to this dependency directory regardless of the working
directory. For an isolated installation, copy only these two package JSON files,
run `npm ci --ignore-scripts` there, and pass `--deps /absolute/install/directory`.
Do not commit `node_modules`.

Input is a JSON array such as:

```json
[{"id":"fraction","latex":"\\frac{a+b}{2}=c"}]
```

`results.json` retains the original string and SHA-256. Normalization only removes
one enclosing `$…$`, `$$…$$`, `\(…\)`, or `\[…\]` pair. Interior text and whitespace
are retained. Each result includes `valid`, error code/message, normalized LaTex,
SVG path/hash, Node/MathJax versions, and elapsed milliseconds. Invalid expressions
have no SVG. The output directory must not already exist.

`evidence.json` records dependency lock, evaluator/source/binary hashes, enabled
packages, timings, and self-test status. `ams`, `mhchem`, and other bundled official
packages are enabled; `noerrors` and `noundefined` are disabled. Parser/compile/typeset
errors and rendered `merror` nodes are rejected. Macro definitions cannot leak
between formulas. Unsupported commands remain failures; there is no correction.

```bash
node docs/minicpm-ocr-4090-plan-20261028/execution/evaluate_formulas.mjs \
  --self-test --out /absolute/path/to/new-self-test
```

The 17 built-in self-tests cover fractions, scripts, chemistry, AMS, delimiters,
unknown commands, unmatched braces, missing arguments/environments, and macro
isolation. To reuse the independently prepared synthetic references, add
`--control-reference /absolute/path/to/controls/gt-reference.json`.

Optionally add `--preview-python /absolute/path/to/python` with PyMuPDF installed
to produce PNG previews from successful SVGs. Preview failure is reported separately
and does not change LaTex renderability.

`valid: true` proves that this MathJax configuration rendered the expression.
It does **not** establish semantic, mathematical, or source-image structural correctness.
An invalid formula is a per-item result; a completed batch can exit with code 0
while containing invalid formulas. Setup/input/self-test errors exit nonzero.
