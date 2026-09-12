const COMMON_API = 'https://form-lens-api.hurukigeoetym.workers.dev';
function reportVisit() { fetch(`${COMMON_API}/api/events`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ site: 'image-shrink-jp', eventName: 'page_view' }) }).catch(() => {}); }

const PACKS = {
  ja: { title: '画像圧縮｜ブラウザだけで軽くする無料ツール', desc: '画像を選ぶだけで、ブラウザ内でJPEG・PNG・WebPを圧縮。画像をサーバーへアップロードせず、軽くした画像を保存できます。', brand: '画像を軽くする帖', navCompress: '圧縮する', navPrivacy: '安全性', navUse: '無料で使う', eyebrow: '画像ツール / 無料', hero: '画像を、<br><span>軽くする。</span>', lede: 'アップロード不要。画像を選ぶと、ブラウザの中で圧縮して保存できます。', panel: '画像圧縮', note: 'ファイルは外へ送信しません', choose: '画像を選ぶ', drop: '画像をここに選択', quality: '圧縮品質', original: '元のサイズ', compressed: '圧縮後', saved: '削減率', download: '圧縮画像を保存', ready: '品質を調整すると、圧縮結果が更新されます。', selectImage: 'JPG、PNG、WebPの画像を選んでください。', updated: '圧縮結果を更新しました。', privacy: '画像はブラウザ内だけで処理。', privacyCopy: '選んだ画像を外部サーバーへ送らず、端末上のCanvas APIで圧縮します。', guideEyebrow: 'HOW IT WORKS', guideTitle: '3つの操作で、<br>送れるサイズに。', g1: '画像を選ぶ', g1p: '端末の画像を選択するか、ドロップします。', g2: '品質を調整する', g2p: '見た目とファイルサイズのバランスを確認します。', g3: '保存する', g3p: '圧縮した画像を端末へ保存します。', faq: 'よくある質問', faqTitle: '軽くする前に。', faq1: '対応している画像形式は？', faq1p: 'JPEG、PNG、WebPを選べます。出力はWebP形式で保存します。', faq2: '画像はアップロードされますか？', faq2p: 'このページでは画像処理をブラウザ内で行います。画像ファイルをサーバーへ送信する処理はありません。', faq3: '圧縮後の画像はどこにありますか？', faq3p: '「圧縮画像を保存」を押すと、ブラウザのダウンロード機能で端末へ保存されます。', footerCompress: '画像圧縮', footerPrivacy: 'プライバシー' },
  en: { title: 'Image Compressor | Make images lighter in your browser', desc: 'Compress JPEG, PNG and WebP images in your browser without uploading them, then save the lighter file.', brand: 'Image Shrink Notes', navCompress: 'Compress', navPrivacy: 'Privacy', navUse: 'Use free', eyebrow: 'IMAGE TOOL / FREE', hero: 'Make images<br><span>lighter.</span>', lede: 'No upload needed. Choose an image, compress it in your browser and save it locally.', panel: 'Image compressor', note: 'FILE NEVER LEAVES YOUR DEVICE', choose: 'Choose image', drop: 'Choose an image here', quality: 'Compression quality', original: 'Original size', compressed: 'Compressed', saved: 'Saved', download: 'Save compressed image', ready: 'Adjust quality to update the result.', selectImage: 'Choose a JPG, PNG or WebP image.', updated: 'Compression result updated.', privacy: 'Images stay in your browser.', privacyCopy: 'The selected image is compressed with the Canvas API without sending it to an external server.', guideEyebrow: 'HOW IT WORKS', guideTitle: 'Three steps to a<br>sendable file.', g1: 'Choose an image', g1p: 'Select an image from your device or drop it here.', g2: 'Tune quality', g2p: 'Balance visual quality and file size.', g3: 'Save it', g3p: 'Save the compressed image back to your device.', faq: 'FAQ', faqTitle: 'Before you shrink.', faq1: 'Which formats are supported?', faq1p: 'Choose JPEG, PNG or WebP. The output is saved as WebP.', faq2: 'Is my image uploaded?', faq2p: 'No. Image processing happens in the browser and no image file is sent to a server.', faq3: 'Where is the compressed image?', faq3p: 'Press “Save compressed image” to download it through your browser.', footerCompress: 'Image compressor', footerPrivacy: 'Privacy' },
  zh: { title: '图片压缩｜仅在浏览器中减小图片', desc: '在浏览器中压缩JPEG、PNG和WebP图片，不上传文件即可保存更小的图片。', brand: '图片轻量册', navCompress: '压缩', navPrivacy: '安全性', navUse: '免费使用', eyebrow: '图片工具 / 免费', hero: '让图片，<br><span>更轻。</span>', lede: '无需上传。选择图片后，在浏览器中压缩并保存到本地。', panel: '图片压缩', note: '文件不会离开设备', choose: '选择图片', drop: '在这里选择图片', quality: '压缩质量', original: '原始大小', compressed: '压缩后', saved: '减少率', download: '保存压缩图片', ready: '调整质量即可更新结果。', selectImage: '请选择JPG、PNG或WebP图片。', updated: '压缩结果已更新。', privacy: '图片只在浏览器中处理。', privacyCopy: '使用设备上的Canvas API压缩，不会把图片发送到外部服务器。', guideEyebrow: 'HOW IT WORKS', guideTitle: '三步操作，<br>得到易发送的大小。', g1: '选择图片', g1p: '从设备中选择图片或拖放到这里。', g2: '调整质量', g2p: '在画质与文件大小之间找到平衡。', g3: '保存', g3p: '将压缩后的图片保存回设备。', faq: '常见问题', faqTitle: '压缩之前。', faq1: '支持哪些图片格式？', faq1p: '支持JPEG、PNG和WebP，输出会保存为WebP。', faq2: '图片会被上传吗？', faq2p: '不会。图片处理在浏览器中完成，不会发送图片文件到服务器。', faq3: '压缩后的图片在哪里？', faq3p: '点击“保存压缩图片”，通过浏览器下载到设备。', footerCompress: '图片压缩', footerPrivacy: '隐私' },
  ko: { title: '이미지 압축 | 브라우저에서 이미지 가볍게 만들기', desc: '이미지를 업로드하지 않고 브라우저에서 JPEG, PNG, WebP를 압축해 저장합니다.', brand: '이미지 가볍게 노트', navCompress: '압축하기', navPrivacy: '안전성', navUse: '무료 사용', eyebrow: '이미지 도구 / 무료', hero: '이미지를<br><span>가볍게.</span>', lede: '업로드가 필요 없습니다. 이미지를 선택하고 브라우저에서 압축해 저장하세요.', panel: '이미지 압축', note: '파일은 기기를 떠나지 않습니다', choose: '이미지 선택', drop: '여기에 이미지를 선택', quality: '압축 품질', original: '원본 크기', compressed: '압축 후', saved: '절약률', download: '압축 이미지 저장', ready: '품질을 조정하면 결과가 업데이트됩니다.', selectImage: 'JPG, PNG 또는 WebP 이미지를 선택하세요.', updated: '압축 결과를 업데이트했습니다.', privacy: '이미지는 브라우저 안에서만 처리됩니다.', privacyCopy: '외부 서버로 보내지 않고 기기의 Canvas API로 이미지를 압축합니다.', guideEyebrow: 'HOW IT WORKS', guideTitle: '세 단계로<br>보내기 좋은 크기.', g1: '이미지 선택', g1p: '기기에서 이미지를 선택하거나 드롭하세요.', g2: '품질 조정', g2p: '화질과 파일 크기의 균형을 확인하세요.', g3: '저장', g3p: '압축한 이미지를 기기에 저장하세요.', faq: '자주 묻는 질문', faqTitle: '가볍게 만들기 전에.', faq1: '지원하는 이미지 형식은?', faq1p: 'JPEG, PNG, WebP를 선택할 수 있으며 출력은 WebP로 저장됩니다.', faq2: '이미지가 업로드되나요?', faq2p: '아니요. 브라우저에서 처리하며 이미지 파일을 서버로 보내지 않습니다.', faq3: '압축한 이미지는 어디에 있나요?', faq3p: '“압축 이미지 저장”을 누르면 브라우저 다운로드로 저장됩니다.', footerCompress: '이미지 압축', footerPrivacy: '개인정보' }
};
let currentLanguage = localStorage.getItem('site-language') || 'ja';
const currentCopy = () => PACKS[currentLanguage] || PACKS.en;

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
function setText(selector, key) { const element = document.querySelector(selector); if (element) element.textContent = currentCopy()[key]; }
function setHtml(selector, key) { const element = document.querySelector(selector); if (element) element.innerHTML = currentCopy()[key]; }
function applyLanguage() {
  const strings = currentCopy();
  document.documentElement.lang = currentLanguage;
  document.title = strings.title;
  document.querySelector('meta[name="description"]')?.setAttribute('content', strings.desc);
  const select = document.querySelector('#languageSelect');
  if (select) select.value = currentLanguage;
  [['header .brand span:last-child','brand'],['.nav-links a:nth-child(1)','navCompress'],['.nav-links a:nth-child(2)','navPrivacy'],['.nav-links a:nth-child(3)','navUse'],['.compress-hero .eyebrow','eyebrow'],['.panel-title','panel'],['.panel-note','note'],['.file-button','choose'],['.drop-zone strong','drop'],['.controls > label','quality'],['.result-row > div:nth-child(1) span','original'],['.result-row > div:nth-child(2) span','compressed'],['.result-row > div:nth-child(3) span','saved'],['#downloadButton','download'],['.guide .eyebrow','guideEyebrow'],['.guide-list > div:nth-child(1) h3','g1'],['.guide-list > div:nth-child(1) p','g1p'],['.guide-list > div:nth-child(2) h3','g2'],['.guide-list > div:nth-child(2) p','g2p'],['.guide-list > div:nth-child(3) h3','g3'],['.guide-list > div:nth-child(3) p','g3p'],['.faq .eyebrow','faq'],['.faq-list details:nth-child(1) summary','faq1'],['.faq-list details:nth-child(1) p','faq1p'],['.faq-list details:nth-child(2) summary','faq2'],['.faq-list details:nth-child(2) p','faq2p'],['.faq-list details:nth-child(3) summary','faq3'],['.faq-list details:nth-child(3) p','faq3p'],['.site-footer > span','brand'],['.site-footer a:nth-child(1)','footerCompress'],['.site-footer a:nth-child(2)','footerPrivacy']].forEach(([selector,key]) => setText(selector,key));
  setText('.compress-hero .lede','lede');
  setHtml('h1','hero'); setHtml('.guide h2','guideTitle'); setHtml('.faq h2','faqTitle');
  document.querySelector('.privacy-strip p').innerHTML = `<strong>${strings.privacy}</strong> ${strings.privacyCopy}`;
  const qualityLabel = document.querySelector('.controls > label');
  if (qualityLabel) qualityLabel.innerHTML = `${strings.quality} <output id="qualityValue">${quality.value}</output>`;
  if (!sourceFile) status.textContent = strings.ready;
}

function formatBytes(bytes) { if (bytes < 1024) return `${bytes} B`; if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`; return `${(bytes / 1024 / 1024).toFixed(2)} MB`; }
function loadFile(file) {
  if (!file || !file.type.startsWith('image/')) { status.textContent = currentCopy().selectImage; return; }
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
    status.textContent = currentCopy().updated;
    status.classList.add('is-success');
  }, 'image/webp', Number(quality.value) / 100);
}
fileInput.addEventListener('change', () => loadFile(fileInput.files[0]));
['dragenter', 'dragover'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.add('is-over'); }));
['dragleave', 'drop'].forEach((eventName) => dropZone.addEventListener(eventName, (event) => { event.preventDefault(); dropZone.classList.remove('is-over'); }));
dropZone.addEventListener('drop', (event) => loadFile(event.dataTransfer.files[0]));
quality.addEventListener('input', () => { document.querySelector('#qualityValue').textContent = quality.value; compress(); });
downloadButton.addEventListener('click', (event) => { if (downloadButton.classList.contains('disabled')) event.preventDefault(); });
document.querySelector('#languageSelect').addEventListener('change', (event) => { currentLanguage = event.target.value; localStorage.setItem('site-language', currentLanguage); applyLanguage(); });
applyLanguage();
reportVisit();

