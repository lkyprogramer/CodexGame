#!/usr/bin/env node
/** Offline MathJax renderability only. Never repairs LaTex or judges semantics. */
import {createRequire} from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {performance} from 'node:perf_hooks';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const args = process.argv.slice(2);
function option(name, fallback) {
  const index = args.indexOf(name);
  if (index < 0) return fallback;
  if (!args[index + 1] || args[index + 1].startsWith('--')) throw new Error(`Missing ${name} value`);
  return args[index + 1];
}
const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const deps = path.resolve(option('--deps', path.join(scriptDirectory, 'formula-renderer')));
const require = createRequire(path.join(deps, 'package.json'));
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
const {AllPackages} = require('mathjax-full/js/input/tex/AllPackages.js');
const version = require('mathjax-full/package.json').version;
if (version !== '3.2.2') throw new Error(`Expected mathjax-full 3.2.2, found ${version}`);
const packages = AllPackages.filter(name => !['noerrors', 'noundefined'].includes(name));
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const fileSha = file => sha(fs.readFileSync(file));
const write = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');

export function normalize(latex) {
  // Retain all whitespace and interior bytes; remove at most one enclosing pair.
  const match = /^(\s*)([\s\S]*?)(\s*)$/.exec(latex);
  const [, before, body, after] = match;
  for (const [open, close] of [['$$', '$$'], ['\\(', '\\)'], ['\\[', '\\]'], ['$', '$']]) {
    if (body.length >= open.length + close.length && body.startsWith(open) && body.endsWith(close)) {
      return before + body.slice(open.length, body.length - close.length) + after;
    }
  }
  return latex;
}

function render(row, index, out) {
  const started = performance.now();
  const normalized = normalize(row.latex);
  const result = {id: row.id, original_latex: row.latex, original_sha256: sha(row.latex),
    normalized_latex: normalized, mathjax_version: version, node_version: process.version,
    valid: false, error: null, svg_path: null, svg_sha256: null};
  try {
    // New TeX state per formula prevents definitions from leaking between items.
    const tex = new TeX({packages, formatError: (_jax, error) => {throw error;}});
    const document = mathjax.document('', {InputJax: tex, OutputJax: new SVG({fontCache: 'none'}),
      compileError: (_doc, _math, error) => {throw error;},
      typesetError: (_doc, _math, error) => {throw error;}});
    const node = document.convert(normalized, {display: true, em: 16, ex: 8, containerWidth: 1280});
    const svgNode = adaptor.tags(node, 'svg')[0];
    if (!svgNode || tex.parseOptions.error) throw new Error('MathJax did not produce a successful SVG');
    const svg = adaptor.outerHTML(svgNode);
    if (/data-mml-node=["']merror["']/.test(svg)) throw new Error('MathJax produced an error node');
    const filename = `${String(index + 1).padStart(5, '0')}-${sha(String(row.id)).slice(0, 16)}.svg`;
    fs.writeFileSync(path.join(out, filename), svg);
    result.valid = true;
    result.svg_path = filename;
    result.svg_sha256 = sha(svg);
  } catch (error) {
    result.error = {name: error.name || 'MathJaxTeXError', code: error.id || null,
      message: String(error.message || error)};
  }
  result.elapsed_ms = performance.now() - started;
  return result;
}

function main() {
  const selfTest = args.includes('--self-test');
  const inputPath = option('--input', null);
  const outValue = option('--out', null);
  if (!outValue || (!selfTest && !inputPath)) throw new Error('Usage: node evaluate_formulas.mjs --input formulas.json --out NEW_DIR [--deps DIR] [--self-test] [--control-reference GT_JSON]');
  const out = path.resolve(outValue);
  let rows;
  if (selfTest) {
    const controls = option('--control-reference', null);
    const formulas = controls
      ? JSON.parse(fs.readFileSync(controls, 'utf8')).pages.find(p => p.page_id === 'CONTROL-03').formula_latex
      : [String.raw`\frac{a+b}{2}=c`, String.raw`x^2+y^2=z^2`, String.raw`H_2O+CO_2\rightarrow H_2CO_3`];
    rows = formulas.map((latex, index) => ({id: `synthetic-control-${index}`, latex, expect_valid: true}));
    rows.push({id: 'mhchem', latex: String.raw`\ce{H2O + CO2 -> H2CO3}`, expect_valid: true},
      {id: 'ams', latex: String.raw`\begin{aligned}a&=b+c\\d&=e\end{aligned}`, expect_valid: true},
      {id: 'unknown', latex: String.raw`\doesNotExistControl{x}`, expect_valid: false},
      {id: 'unbalanced-open', latex: String.raw`\frac{a}{b`, expect_valid: false},
      {id: 'unbalanced-close', latex: 'x+1}', expect_valid: false},
      {id: 'missing-argument', latex: String.raw`\frac{x}`, expect_valid: false},
      {id: 'unclosed-env', latex: String.raw`\begin{aligned}x&=1`, expect_valid: false},
      {id: 'defined-local', latex: String.raw`\newcommand{\localControl}{x}\localControl`, expect_valid: true},
      {id: 'no-macro-leak', latex: String.raw`\localControl`, expect_valid: false},
      {id: 'dollar-boundary', latex: '  $x_1^2$ \n', expect_valid: true},
      {id: 'double-dollar', latex: '$$\\frac{1}{2}$$', expect_valid: true},
      {id: 'paren-boundary', latex: String.raw`\(x+y\)`, expect_valid: true},
      {id: 'bracket-boundary', latex: String.raw`\[x+y\]`, expect_valid: true},
      {id: 'plain-interior', latex: ' x + y  ', expect_valid: true});
    assert.equal(normalize(rows.find(r => r.id === 'dollar-boundary').latex), '  x_1^2 \n');
    assert.equal(normalize(' x + y  '), ' x + y  ');
    assert.equal(normalize(String.raw`\text{a $ b}`), String.raw`\text{a $ b}`);
    assert.equal(normalize('$$$x$$$'), '$x$'); // Exactly one wrapper only.
  } else {
    rows = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  }
  if (!Array.isArray(rows)) throw new Error('Input must be a JSON array of {id, latex}');
  const seen = new Set();
  for (const row of rows) {
    if (!row || !['string', 'number'].includes(typeof row.id) || typeof row.latex !== 'string') throw new Error('Every input needs string/number id and string latex');
    if (seen.has(String(row.id))) throw new Error('Duplicate formula id');
    seen.add(String(row.id));
  }
  fs.mkdirSync(out, {recursive: false, mode: 0o700});
  const started = performance.now();
  const results = rows.map((row, index) => render(row, index, out));
  let preview = 'not_requested_SVG_available';
  const previewPython = option('--preview-python', null);
  if (previewPython) {
    const conversion = spawnSync(previewPython, ['-c', `
import hashlib,json,sys
from pathlib import Path
import fitz
result=[]
for name in json.load(sys.stdin):
    source=Path(name)
    with fitz.open(source) as doc:
        pix=doc[0].get_pixmap(matrix=fitz.Matrix(4,4),alpha=False)
    dest=source.with_suffix('.png')
    pix.save(dest)
    result.append({'svg_path':source.name,'png_path':dest.name,'png_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'png_dimensions':[pix.width,pix.height]})
print(json.dumps({'renderer':'PyMuPDF','version':fitz.VersionBind,'scale':4,'files':result}))
`], {input: JSON.stringify(results.filter(r => r.valid).map(r => path.join(out, r.svg_path))),
      encoding: 'utf8', timeout: 120000});
    if (conversion.error || conversion.status !== 0) {
      preview = {status: 'FAIL', error: String(conversion.error || conversion.stderr)};
    } else {
      const converted = JSON.parse(conversion.stdout);
      for (const file of converted.files) Object.assign(results.find(r => r.svg_path === file.svg_path), file);
      preview = {status: 'PASS', renderer: converted.renderer, version: converted.version, scale: converted.scale};
    }
  }
  write(path.join(out, 'results.json'), results);
  if (selfTest) {
    for (let i = 0; i < rows.length; i++) {
      assert.equal(results[i].valid, rows[i].expect_valid, `${rows[i].id}: ${JSON.stringify(results[i].error)}`);
      assert.equal(results[i].original_latex, rows[i].latex);
      assert.equal(results[i].original_sha256, sha(rows[i].latex));
      if (!results[i].valid) assert.equal(results[i].svg_path, null);
    }
    write(path.join(out, 'self-test-inputs.json'), rows);
  }
  const sources = ['js/mathjax.js', 'js/input/tex.js', 'js/output/svg.js', 'js/adaptors/liteAdaptor.js',
    'js/input/tex/AllPackages.js', 'js/input/tex/base/BaseConfiguration.js', 'js/input/tex/mhchem/MhchemConfiguration.js'];
  write(path.join(out, 'evidence.json'), {
    scope: 'real_MathJax_SVG_renderability_only_not_semantic_or_structural_correctness',
    node_version: process.version, node_binary_sha256: fileSha(process.execPath),
    npm_lock_sha256: fileSha(path.join(deps, 'package-lock.json')), mathjax_version: version,
    mathjax_package_sha256: fileSha(require.resolve('mathjax-full/package.json')),
    evaluator_sha256: fileSha(fileURLToPath(import.meta.url)), input_sha256: inputPath ? fileSha(inputPath) : null,
    control_reference_sha256: selfTest && option('--control-reference', null)
      ? fileSha(option('--control-reference', null)) : null,
    packages, excluded_error_hiding_packages: ['noerrors', 'noundefined'],
    error_policy: 'throw formatError/compileError/typesetError; reject merror; no SVG on failure',
    dependency_sources: Object.fromEntries(sources.map(source => [source, fileSha(require.resolve('mathjax-full/' + source))])),
    self_test: selfTest ? 'PASS' : 'not_requested', formula_count: rows.length,
    valid_count: results.filter(r => r.valid).length, invalid_count: results.filter(r => !r.valid).length,
    elapsed_ms: performance.now() - started, offline_runtime: true, png_preview: preview});
  console.log(JSON.stringify({out, count: results.length, valid: results.filter(r => r.valid).length,
    invalid: results.filter(r => !r.valid).length, self_test: selfTest ? 'PASS' : null}));
}

try {main();} catch (error) {console.error(String(error.stack || error)); process.exitCode = 1;}
