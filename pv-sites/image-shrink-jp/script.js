const COMMON_API = 'https://form-lens-api.hurukigeoetym.workers.dev';
function reportVisit() { fetch(`${COMMON_API}/api/events`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ site: 'image-shrink-jp', eventName: 'page_view' }) }).catch(() => {}); }

const fileInput = document.querySelector('#fileInput');
const dropZone = document.querySelector('#dropZone');
const controls = document.querySelector('#controls');
const quality = document.querySelector('#quality');
const qualityValue = document.querySelector('#qualityValue');
const originalSize = document.querySelector('#originalSize');
const compressedSize = document.querySelector('#compressedSize');
const savedSize = document.querySelector('#savedSize');
const downloadButton = document.querySelector('#downloadButton');
const status = document.querySelector('#status');
let sourceFile = null;
let image = null;
let objectUrl = null;

function formatBytes(bytes) { if (bytes < 1024) return `${bytes} B`; if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`; return `${(bytes / 1024 / 1024).toFixed(2)} MB`; }
function loadFile(file) {
  if (!file || !file.type.startsWith('image/')) { status.textContent = 'JPG、PNG、WebPの画像を選んでください。'; return; }
  sourceFile = file;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(file);
  image = new Image();
  image.onload = () => { controls.hidden = false; originalSize.textContent = formatBytes(sourceFile.size); compress(); };
  image.src = objectUrl;
  dropZone.innerHTML = `<strong>${file.name}</strong><span>${formatBytes(file.size)} / ${file.type}</span>`;
}
function compress() {
  if (!sourceFile || !image) return;
  const canvas = document.createElement('canvas');
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  canvas.getContext('2d').drawImage(image, 0, 0);
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    downloadButton.href = url;
    downloadButton.classList.remove('disabled');
    downloadButton.setAttribute('aria-disabled', 'false');
    compressedSize.textContent = formatBytes(blob.size);
    const saved = Math.max(0, Math.round((1 - blob.size / sourceFile.size) * 100));
    savedSize.textContent = `${saved}%`;
    status.textContent = '圧縮結果を更新しました。';
    status.classList.add('is-success');
  }, 'image/webp', Number(quality.value) / 100);
}
fileInput.addEventListener('change', () => loadFile(fileInput.files[0]));
['dragenter', 'dragover'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.add('is-over'); }));
['dragleave', 'drop'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.remove('is-over'); }));
dropZone.addEventListener('drop', (event) => loadFile(event.dataTransfer.files[0]));
quality.addEventListener('input', () => { qualityValue.textContent = quality.value; compress(); });
downloadButton.addEventListener('click', (event) => { if (downloadButton.classList.contains('disabled')) event.preventDefault(); });
reportVisit();

