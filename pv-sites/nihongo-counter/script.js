const COMMON_API = 'https://form-lens-api.hurukigeoetym.workers.dev';
function reportVisit() { fetch(`${COMMON_API}/api/events`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ site: 'nihongo-counter', eventName: 'page_view' }) }).catch(() => {}); }

const input = document.querySelector('#textInput');
const countAll = document.querySelector('#countAll');
const countNoSpace = document.querySelector('#countNoSpace');
const countLines = document.querySelector('#countLines');
const countPages = document.querySelector('#countPages');
const status = document.querySelector('#status');

function updateCounts() {
  const value = input.value;
  const withoutWhitespace = value.replace(/\s/g, '');
  countAll.textContent = value.length.toLocaleString('ja-JP');
  countNoSpace.textContent = withoutWhitespace.length.toLocaleString('ja-JP');
  countLines.textContent = value ? String(value.split(/\r?\n/).length) : '0';
  countPages.textContent = withoutWhitespace ? String(Math.ceil(withoutWhitespace.length / 400)) : '0';
}

input.addEventListener('input', updateCounts);
document.querySelector('#clearButton').addEventListener('click', () => { input.value = ''; updateCounts(); input.focus(); status.textContent = '入力欄をクリアしました。'; });
document.querySelector('#copyButton').addEventListener('click', async () => {
  if (!input.value) { status.textContent = 'コピーする文章がありません。'; return; }
  try { await navigator.clipboard.writeText(input.value); status.textContent = '文章をコピーしました。'; status.classList.add('is-success'); } catch { status.textContent = 'コピーできませんでした。文章を選択してコピーしてください。'; }
});
updateCounts();
reportVisit();

