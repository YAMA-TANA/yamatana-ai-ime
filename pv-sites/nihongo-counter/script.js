const COMMON_API = 'https://form-lens-api.hurukigeoetym.workers.dev';
function reportVisit() { fetch(`${COMMON_API}/api/events`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ site: 'nihongo-counter', eventName: 'page_view' }) }).catch(() => {}); }

const PACKS = {
  ja: { title: '文字数カウント｜原稿用紙・レポート文字数をすぐ確認', desc: '文章を貼り付けるだけで、文字数・空白を除いた文字数・行数・原稿用紙換算を確認できる無料ツールです。', brand: '日本語ツール帖', count: 'カウント', guide: '使い方', use: '無料で使う', eyebrow: '文章ツール / 無料', hero: '文字数を、<br><span>迷わず確認。</span>', lede: 'レポート、作文、応募文、SNS投稿。文章を貼り付けるだけで、必要な数字がその場で分かります。', panel: '文字数カウント', local: 'ブラウザ内処理', placeholder: 'ここに文章を貼り付けてください', sample: '文章を貼り付けると、文字数を自動で数えます。', all: '文字', noSpace: '空白なし', lines: '行', pages: '原稿用紙', clear: 'クリア', copy: '文章をコピー', localStatus: '入力内容はこのブラウザ内だけで処理します。', clearStatus: '入力欄をクリアしました。', noCopy: 'コピーする文章がありません。', copied: '文章をコピーしました。', copyFailed: 'コピーできませんでした。文章を選択してコピーしてください。', quick: 'よく使う計算', q1: '原稿用紙400字換算', q2: '空白を除いた文字数', q3: '改行を含む行数', guideEyebrow: 'HOW TO READ THE NUMBERS', guideTitle: '用途に合わせて、<br>見る数字を選ぶ。', g1: '文字数', g1p: '入力した文章をそのまま数えます。空白や改行も1文字として扱います。', g2: '空白なし', g2p: 'スペースと改行を除いて数えます。レポートや応募フォームの目安に便利です。', g3: '原稿用紙', g3p: '空白を除いた文字数を400で割り、必要な枚数を目安として表示します。', faq: 'よくある質問', faqTitle: '短く、正確に。', faq1: '入力した文章は保存されますか？', faq1p: 'このページでは入力内容をサーバーへ送信せず、ブラウザ内でカウントしています。ページを閉じると入力内容は残りません。', faq2: '原稿用紙は何文字で計算しますか？', faq2p: '400字詰め原稿用紙を基準に、空白を除いた文字数から目安を計算しています。', faq3: 'スマートフォンでも使えますか？', faq3p: 'スマートフォンのブラウザでも使えます。文章をコピーして貼り付けてください。', footerCount: '文字数カウント', footerOwner: '運営者情報' },
  en: { title: 'Character Counter | Japanese manuscript and report length', desc: 'Paste text to check characters, characters without spaces, lines and 400-character manuscript pages for free.', brand: 'Japanese Tool Notes', count: 'Counter', guide: 'Guide', use: 'Use free', eyebrow: 'WRITING TOOL / FREE', hero: 'Know your<br><span>word count.</span>', lede: 'Reports, essays, applications and social posts. Paste your text and get the numbers you need right away.', panel: 'Character counter', local: 'PROCESSED IN BROWSER', placeholder: 'Paste your text here', sample: 'Paste text to count characters automatically.', all: 'characters', noSpace: 'no spaces', lines: 'lines', pages: 'pages', clear: 'Clear', copy: 'Copy text', localStatus: 'Your text is processed only in this browser.', clearStatus: 'The input was cleared.', noCopy: 'There is no text to copy.', copied: 'Text copied.', copyFailed: 'Could not copy. Select the text and copy it manually.', quick: 'QUICK CALCULATIONS', q1: '400-character pages', q2: 'Characters without spaces', q3: 'Lines including breaks', guideEyebrow: 'HOW TO READ THE NUMBERS', guideTitle: 'Choose the number<br>that fits the job.', g1: 'Characters', g1p: 'Counts the text as entered. Spaces and line breaks count as one character.', g2: 'No spaces', g2p: 'Removes spaces and line breaks. Useful for report and application limits.', g3: 'Pages', g3p: 'Divides characters without spaces by 400 for a manuscript-page estimate.', faq: 'FAQ', faqTitle: 'Short and exact.', faq1: 'Is my text saved?', faq1p: 'No. This page counts your text in the browser and never sends it to a server. It disappears when you close the page.', faq2: 'How are pages calculated?', faq2p: 'The estimate uses 400-character manuscript pages and ignores spaces.', faq3: 'Does it work on phones?', faq3p: 'Yes. Open it in a mobile browser, then paste or type your text.', footerCount: 'Character counter', footerOwner: 'About' },
  zh: { title: '字数统计｜文章与作文长度快速检查', desc: '粘贴文章即可免费查看字数、不含空格字数、行数和400字稿纸页数。', brand: '日语工具册', count: '字数统计', guide: '使用说明', use: '免费使用', eyebrow: '写作工具 / 免费', hero: '字数，<br><span>马上看清。</span>', lede: '报告、作文、申请文和社交媒体。粘贴文字后，立即得到需要的数字。', panel: '字数统计', local: '浏览器本地处理', placeholder: '请在这里粘贴文章', sample: '粘贴文章后会自动统计字数。', all: '字', noSpace: '不含空格', lines: '行', pages: '稿纸页', clear: '清空', copy: '复制文章', localStatus: '内容只在此浏览器中处理。', clearStatus: '输入框已清空。', noCopy: '没有可复制的文字。', copied: '文字已复制。', copyFailed: '无法复制，请手动选择文字后复制。', quick: '常用计算', q1: '400字稿纸换算', q2: '不含空格字数', q3: '包含换行的行数', guideEyebrow: 'HOW TO READ THE NUMBERS', guideTitle: '根据用途，<br>选择要看的数字。', g1: '字数', g1p: '按输入内容统计，空格和换行也算作一个字符。', g2: '不含空格', g2p: '排除空格和换行，适合检查报告与申请文的长度。', g3: '稿纸页数', g3p: '将不含空格的字数除以400，估算所需稿纸页数。', faq: '常见问题', faqTitle: '简洁，准确。', faq1: '输入内容会被保存吗？', faq1p: '不会。本页只在浏览器中统计，不会把内容发送到服务器，关闭页面后内容也会消失。', faq2: '稿纸页数如何计算？', faq2p: '以每页400字为标准，并使用不含空格的字数估算。', faq3: '手机上可以使用吗？', faq3p: '可以。在手机浏览器打开后粘贴或输入文字即可。', footerCount: '字数统计', footerOwner: '关于本站' },
  ko: { title: '글자 수 세기 | 원고지·리포트 글자 수 확인', desc: '텍스트를 붙여 넣으면 글자 수, 공백 제외 글자 수, 줄 수와 400자 원고지 페이지를 무료로 확인합니다.', brand: '일본어 도구 노트', count: '글자 수', guide: '사용법', use: '무료 사용', eyebrow: '글쓰기 도구 / 무료', hero: '글자 수를<br><span>바로 확인하세요.</span>', lede: '리포트, 에세이, 지원서와 SNS 글. 텍스트를 붙여 넣으면 필요한 숫자를 바로 보여줍니다.', panel: '글자 수 세기', local: '브라우저에서 처리', placeholder: '여기에 텍스트를 붙여 넣으세요', sample: '텍스트를 붙여 넣으면 글자 수를 자동으로 셉니다.', all: '글자', noSpace: '공백 제외', lines: '줄', pages: '원고지', clear: '지우기', copy: '텍스트 복사', localStatus: '입력 내용은 이 브라우저 안에서만 처리됩니다.', clearStatus: '입력란을 지웠습니다.', noCopy: '복사할 텍스트가 없습니다.', copied: '텍스트를 복사했습니다.', copyFailed: '복사하지 못했습니다. 텍스트를 선택해 직접 복사하세요.', quick: '자주 쓰는 계산', q1: '400자 원고지 환산', q2: '공백 제외 글자 수', q3: '줄바꿈 포함 줄 수', guideEyebrow: 'HOW TO READ THE NUMBERS', guideTitle: '용도에 맞는<br>숫자를 고르세요.', g1: '글자 수', g1p: '입력한 텍스트를 그대로 셉니다. 공백과 줄바꿈도 한 글자로 계산합니다.', g2: '공백 제외', g2p: '공백과 줄바꿈을 제외합니다. 리포트와 지원서 분량 확인에 유용합니다.', g3: '원고지', g3p: '공백을 제외한 글자 수를 400으로 나누어 페이지를 추정합니다.', faq: '자주 묻는 질문', faqTitle: '짧고 정확하게.', faq1: '입력한 글이 저장되나요?', faq1p: '아니요. 브라우저 안에서만 계산하며 서버로 전송하지 않습니다. 페이지를 닫으면 사라집니다.', faq2: '원고지 페이지는 어떻게 계산하나요?', faq2p: '400자 원고지를 기준으로 공백을 제외한 글자 수를 계산합니다.', faq3: '스마트폰에서도 쓸 수 있나요?', faq3p: '네. 모바일 브라우저에서 열고 텍스트를 붙여 넣으면 됩니다.', footerCount: '글자 수 세기', footerOwner: '사이트 정보' }
};

const input = document.querySelector('#textInput');
const countAll = document.querySelector('#countAll');
const countNoSpace = document.querySelector('#countNoSpace');
const countLines = document.querySelector('#countLines');
const countPages = document.querySelector('#countPages');
const status = document.querySelector('#status');
let currentLanguage = localStorage.getItem('site-language') || 'ja';
const currentCopy = () => PACKS[currentLanguage] || PACKS.en;
const setText = (selector, key) => { const element = document.querySelector(selector); if (element) element.textContent = currentCopy()[key]; };
const setHtml = (selector, key) => { const element = document.querySelector(selector); if (element) element.innerHTML = currentCopy()[key]; };

function applyLanguage() {
  const strings = currentCopy();
  document.documentElement.lang = currentLanguage;
  document.title = strings.title;
  document.querySelector('meta[name="description"]')?.setAttribute('content', strings.desc);
  const select = document.querySelector('#languageSelect');
  if (select) select.value = currentLanguage;
  [['header .brand span:last-child','brand'],['.nav-links a:nth-child(1)','count'],['.nav-links a:nth-child(2)','guide'],['.nav-links a:nth-child(3)','use'],['.tool-hero .eyebrow','eyebrow'],['.panel-head > span:first-child','panel'],['.local-badge','local'],['.stats div:nth-child(1) span','all'],['.stats div:nth-child(2) span','noSpace'],['.stats div:nth-child(3) span','lines'],['.stats div:nth-child(4) span','pages'],['#clearButton','clear'],['#copyButton','copy'],['.quick-label','quick'],['.quick-links a:nth-child(2)','q1'],['.quick-links a:nth-child(3)','q2'],['.quick-links a:nth-child(4)','q3'],['.guide .eyebrow','guideEyebrow'],['.guide-grid article:nth-child(1) h3','g1'],['.guide-grid article:nth-child(1) p','g1p'],['.guide-grid article:nth-child(2) h3','g2'],['.guide-grid article:nth-child(2) p','g2p'],['.guide-grid article:nth-child(3) h3','g3'],['.guide-grid article:nth-child(3) p','g3p'],['.faq .eyebrow','faq'],['.faq-list details:nth-child(1) summary','faq1'],['.faq-list details:nth-child(1) p','faq1p'],['.faq-list details:nth-child(2) summary','faq2'],['.faq-list details:nth-child(2) p','faq2p'],['.faq-list details:nth-child(3) summary','faq3'],['.faq-list details:nth-child(3) p','faq3p'],['.site-footer > span','brand'],['.site-footer a:nth-child(1)','footerCount'],['.site-footer a:nth-child(2)','footerOwner']].forEach(([selector,key]) => setText(selector,key));
  setHtml('h1','hero'); setHtml('.guide h2','guideTitle'); setHtml('.faq h2','faqTitle');
  input.placeholder = strings.placeholder;
  input.setAttribute('aria-label', strings.panel);
  if (!input.dataset.userEdited) input.value = strings.sample;
  status.textContent = strings.localStatus;
  updateCounts();
}

function updateCounts() {
  const value = input.value;
  const withoutWhitespace = value.replace(/\s/g, '');
  const locale = currentLanguage === 'ja' ? 'ja-JP' : currentLanguage === 'zh' ? 'zh-CN' : currentLanguage === 'ko' ? 'ko-KR' : 'en-US';
  countAll.textContent = value.length.toLocaleString(locale);
  countNoSpace.textContent = withoutWhitespace.length.toLocaleString(locale);
  countLines.textContent = value ? String(value.split(/\r?\n/).length) : '0';
  countPages.textContent = withoutWhitespace ? String(Math.ceil(withoutWhitespace.length / 400)) : '0';
}

input.addEventListener('input', () => { input.dataset.userEdited = '1'; updateCounts(); });
document.querySelector('#clearButton').addEventListener('click', () => { input.value = ''; input.dataset.userEdited = '1'; updateCounts(); input.focus(); status.textContent = currentCopy().clearStatus; });
document.querySelector('#copyButton').addEventListener('click', async () => {
  if (!input.value) { status.textContent = currentCopy().noCopy; return; }
  try { await navigator.clipboard.writeText(input.value); status.textContent = currentCopy().copied; status.classList.add('is-success'); } catch { status.textContent = currentCopy().copyFailed; }
});
document.querySelector('#languageSelect').addEventListener('change', (event) => { currentLanguage = event.target.value; localStorage.setItem('site-language', currentLanguage); applyLanguage(); });
applyLanguage();
reportVisit();

