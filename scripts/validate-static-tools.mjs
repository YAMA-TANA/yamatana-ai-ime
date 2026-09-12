#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const root = path.resolve(process.cwd(), 'pv-sites');
const errors = [];
const warnings = [];
let htmlCount = 0;
let jsCount = 0;
let inlineCount = 0;

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}

function rel(p) { return path.relative(process.cwd(), p).replaceAll(path.sep, '/'); }
function fail(file, msg) { errors.push(`${rel(file)}: ${msg}`); }
function warn(file, msg) { warnings.push(`${rel(file)}: ${msg}`); }

function checkJs(file, source = null, label = '') {
  jsCount++;
  let target = file;
  let cleanup = false;
  if (source != null) {
    const safe = rel(file).replace(/[^a-z0-9_.-]+/gi, '_');
    target = path.join(os.tmpdir(), `static-tool-${process.pid}-${safe}-${inlineCount++}.js`);
    fs.writeFileSync(target, source, 'utf8');
    cleanup = true;
  }
  const r = spawnSync(process.execPath, ['--check', target], { encoding: 'utf8' });
  if (cleanup) fs.rmSync(target, { force: true });
  if (r.status !== 0) fail(file, `${label || 'JavaScript'} syntax error: ${(r.stderr || r.stdout).trim().split('\n').slice(-2).join(' ')}`);
}

function attrs(tag) {
  const out = new Map();
  const re = /([:\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
  let m;
  while ((m = re.exec(tag))) out.set(m[1].toLowerCase(), m[2] ?? m[3] ?? m[4] ?? '');
  return out;
}

function checkLocalRef(file, value, kind) {
  if (!value || /^(?:https?:|data:|blob:|mailto:|tel:|#|\/\/)/i.test(value)) return;
  const clean = value.split(/[?#]/)[0];
  if (!clean || clean.startsWith('/')) return;
  const target = path.resolve(path.dirname(file), clean);
  if (!fs.existsSync(target)) fail(file, `missing local ${kind}: ${value}`);
}

function checkHtml(file) {
  htmlCount++;
  const s = fs.readFileSync(file, 'utf8');
  if (!/^\s*<!doctype html>/i.test(s)) fail(file, 'missing <!doctype html>');
  if (!/<html\b[^>]*\blang\s*=/i.test(s)) fail(file, 'missing html lang');
  if (!/<meta\b[^>]*name=["']viewport["']/i.test(s)) fail(file, 'missing viewport meta');
  if (!/<title>[^<]+<\/title>/i.test(s)) fail(file, 'missing non-empty title');
  if (!/<meta\b[^>]*name=["']description["'][^>]*content=["'][^"']+/i.test(s) && !/<meta\b[^>]*content=["'][^"']+["'][^>]*name=["']description["']/i.test(s)) fail(file, 'missing meta description');
  if (!/<link\b[^>]*rel=["']canonical["'][^>]*href=/i.test(s) && !/<link\b[^>]*href=[^>]*rel=["']canonical["']/i.test(s)) warn(file, 'missing canonical link');

  const ids = new Map();
  for (const m of s.matchAll(/\bid\s*=\s*["']([^"']+)["']/gi)) ids.set(m[1], (ids.get(m[1]) || 0) + 1);
  for (const [id, count] of ids) if (count > 1) fail(file, `duplicate id="${id}" (${count} occurrences)`);

  for (const m of s.matchAll(/<script\b[^>]*>[\s\S]*?<\/script>/gi)) {
    const full = m[0];
    const open = full.match(/^<script\b[^>]*>/i)?.[0] || '<script>';
    const a = attrs(open);
    const src = a.get('src');
    if (src) { checkLocalRef(file, src, 'script'); continue; }
    const type = (a.get('type') || '').toLowerCase();
    if (type && !['text/javascript', 'application/javascript', 'module'].includes(type)) continue;
    const body = full.slice(open.length, full.toLowerCase().lastIndexOf('</script>'));
    if (body.trim()) checkJs(file, body, 'inline JavaScript');
  }

  for (const m of s.matchAll(/<link\b[^>]*>/gi)) {
    const a = attrs(m[0]);
    const href = a.get('href');
    const relation = (a.get('rel') || '').toLowerCase();
    if (href && relation.includes('stylesheet')) checkLocalRef(file, href, 'stylesheet');
  }

  for (const m of s.matchAll(/<a\b[^>]*\btarget\s*=\s*["']_blank["'][^>]*>/gi)) {
    const a = attrs(m[0]);
    const r = (a.get('rel') || '').toLowerCase().split(/\s+/);
    if (!r.includes('noopener')) fail(file, 'target="_blank" link missing rel="noopener"');
  }

  for (const m of s.matchAll(/\son[a-z]+\s*=/gi)) warn(file, `inline event handler ${m[0].trim()} reduces CSP hardening options`);
}

if (!fs.existsSync(root)) {
  console.error('pv-sites directory not found');
  process.exit(2);
}

const files = walk(root);
for (const file of files) {
  if (file.endsWith('.js')) checkJs(file);
  else if (file.endsWith('.html')) checkHtml(file);
}

console.log(`Validated ${htmlCount} HTML files, ${jsCount} JavaScript blocks/files.`);
if (warnings.length) {
  console.log(`\nWarnings (${warnings.length}):`);
  for (const w of warnings) console.log(`  - ${w}`);
}
if (errors.length) {
  console.error(`\nErrors (${errors.length}):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log('\nStatic tool quality gate passed.');
