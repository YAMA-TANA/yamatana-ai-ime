const COMMON_API = 'https://form-lens-api.hurukigeoetym.workers.dev';
function reportVisit() { fetch(`${COMMON_API}/api/events`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ site: 'kanji-quiz', eventName: 'page_view' }) }).catch(() => {}); }

const PACKS = {
  ja: { title: '難読漢字クイズ｜読めそうで読めない漢字の読み方', desc: '躑躅、紫陽花、蒲公英など、読めそうで読めない難読漢字をクイズで確認。読み方と意味を一覧でも見られます。', brand: '漢字の読み場', navQuiz: 'クイズ', navList: '読み方一覧', navTry: '挑戦する', eyebrow: '漢字クイズ / 無料', hero: '読めそうで、<br><span>読めない。</span>', lede: '身近な植物、食べもの、自然の言葉。知っているのに読めない漢字を、1問ずつ確かめます。', start: 'クイズを始める', hint: 'この漢字、なんと読む？', placeholder: 'ひらがなで入力', aria: '漢字の読みを入力', check: '答え合わせ', next: '次の問題', prompt: '読みを入力して答え合わせしてください。', empty: '読みを入力してください。', correct: '正解。{{kanji}}は「{{answer}}」と読みます。', wrong: '答えは「{{answer}}」。もう一度覚えておきましょう。', question: 'QUESTION', score: 'SCORE', listEyebrow: 'READING LIST', listTitle: '今日の難読漢字、<br>10語。', listIntro: 'クイズに出る漢字の読み方と意味をまとめています。', tipsEyebrow: 'LEARN BY CONTEXT', tipsTitle: '読み方は、<br>言葉の中で覚える。', tip1: '植物の名前は、季節と一緒に覚える', tip2: '食べものは、漢字の由来を知る', tip3: '読めなかった漢字を、あとで一覧に戻る', footerQuiz: 'クイズ', footerList: '読み方一覧' },
  en: { title: 'Kanji Reading Quiz | Japanese characters that fool you', desc: 'Test tricky Japanese kanji such as tsutsuji and ajisai, then browse their readings and meanings in one list.', brand: 'Kanji Reading Room', navQuiz: 'Quiz', navList: 'Reading list', navTry: 'Try it', eyebrow: 'KANJI QUIZ / FREE', hero: 'Looks familiar,<br><span>reads differently.</span>', lede: 'Plants, food and nature words you may know but cannot read. Check one tricky kanji at a time.', start: 'Start the quiz', hint: 'How do you read this kanji?', placeholder: 'Type in hiragana', aria: 'Kanji reading answer', check: 'Check answer', next: 'Next question', prompt: 'Type a reading and check your answer.', empty: 'Please type a reading first.', correct: 'Correct. {{kanji}} is read “{{answer}}”.', wrong: 'The answer is “{{answer}}”. Keep it in your memory.', question: 'QUESTION', score: 'SCORE', listEyebrow: 'READING LIST', listTitle: '10 tricky kanji<br>for today.', listIntro: 'Browse the readings and meanings used in the quiz.', tipsEyebrow: 'LEARN BY CONTEXT', tipsTitle: 'Remember readings<br>inside real words.', tip1: 'Learn plant names with their seasons', tip2: 'Look up the story behind food kanji', tip3: 'Return to the list after a missed reading', footerQuiz: 'Quiz', footerList: 'Reading list' },
  zh: { title: '日语难读汉字测验｜读起来意外的汉字', desc: '用测验学习躑躅、紫陽花、蒲公英等日语难读汉字，并查看读音和含义。', brand: '汉字读法场', navQuiz: '测验', navList: '读法列表', navTry: '开始挑战', eyebrow: '汉字测验 / 免费', hero: '看起来熟悉，<br><span>读法不一样。</span>', lede: '植物、食物和自然词汇。一次确认一个“认识却不会读”的日语汉字。', start: '开始测验', hint: '这个汉字怎么读？', placeholder: '请输入平假名', aria: '汉字读音答案', check: '检查答案', next: '下一题', prompt: '输入读音后检查答案。', empty: '请先输入读音。', correct: '正确。{{kanji}}读作“{{answer}}”。', wrong: '答案是“{{answer}}”。再记一次吧。', question: '题目', score: '得分', listEyebrow: 'READING LIST', listTitle: '今天的难读汉字<br>10个。', listIntro: '整理测验中出现的读音和含义。', tipsEyebrow: 'LEARN BY CONTEXT', tipsTitle: '把读法放进<br>词语中记住。', tip1: '结合季节记植物名称', tip2: '了解食物汉字的由来', tip3: '答错后回到列表再次确认', footerQuiz: '测验', footerList: '读法列表' },
  ko: { title: '일본어 한자 읽기 퀴즈 | 알 것 같지만 어려운 한자', desc: '躑躅, 紫陽花, 蒲公英처럼 읽기 어려운 일본어 한자를 퀴즈와 목록으로 확인하세요.', brand: '한자 읽기장', navQuiz: '퀴즈', navList: '읽기 목록', navTry: '도전하기', eyebrow: '한자 퀴즈 / 무료', hero: '익숙해 보여도,<br><span>읽기는 어렵다.</span>', lede: '식물, 음식과 자연에 관한 단어. 알고 있지만 읽기 어려운 한자를 하나씩 확인합니다.', start: '퀴즈 시작', hint: '이 한자는 어떻게 읽을까요?', placeholder: '히라가나로 입력', aria: '한자 읽기 답변', check: '정답 확인', next: '다음 문제', prompt: '읽는 법을 입력하고 정답을 확인하세요.', empty: '먼저 읽는 법을 입력하세요.', correct: '정답입니다. {{kanji}}는 “{{answer}}”라고 읽습니다.', wrong: '정답은 “{{answer}}”입니다. 다시 기억해 두세요.', question: '문제', score: '점수', listEyebrow: 'READING LIST', listTitle: '오늘의 어려운 한자<br>10개.', listIntro: '퀴즈에 나오는 한자의 읽는 법과 뜻을 모았습니다.', tipsEyebrow: 'LEARN BY CONTEXT', tipsTitle: '읽는 법을<br>단어 속에서 기억하세요.', tip1: '식물 이름을 계절과 함께 익히기', tip2: '음식 한자의 유래 알아보기', tip3: '틀린 한자는 목록으로 돌아가 다시 보기', footerQuiz: '퀴즈', footerList: '읽기 목록' }
};
let currentLanguage = localStorage.getItem('site-language') || 'ja';
const currentCopy = () => PACKS[currentLanguage] || PACKS.en;
const tr = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{{${name}}}`, value), currentCopy()[key]);

const questions = [
  ['躑躅', 'つつじ'], ['紫陽花', 'あじさい'], ['蒲公英', 'たんぽぽ'], ['山茶花', 'さざんか'], ['百日紅', 'さるすべり'],
  ['海月', 'くらげ'], ['河豚', 'ふぐ'], ['土竜', 'もぐら'], ['蝸牛', 'かたつむり'], ['五月雨', 'さみだれ']
];
let index = 0;
let score = 0;
const word = document.querySelector('#kanjiWord');
const input = document.querySelector('#answerInput');
const feedback = document.querySelector('#quizFeedback');
const checkButton = document.querySelector('#checkButton');
const nextButton = document.querySelector('#nextButton');
const questionNumber = document.querySelector('#questionNumber');
const scoreLabel = document.querySelector('#scoreLabel');

function renderQuestion() {
  word.textContent = questions[index][0];
  questionNumber.textContent = `${currentCopy().question} ${String(index + 1).padStart(2, '0')}`;
  scoreLabel.textContent = `${currentCopy().score} ${score}`;
  input.value = '';
  input.disabled = false;
  checkButton.disabled = false;
  nextButton.disabled = true;
  feedback.textContent = currentCopy().prompt;
  feedback.className = 'feedback';
  input.focus();
}

function applyLanguage() {
  const strings = currentCopy();
  document.documentElement.lang = currentLanguage;
  document.title = strings.title;
  document.querySelector('meta[name="description"]')?.setAttribute('content', strings.desc);
  const select = document.querySelector('#languageSelect');
  if (select) select.value = currentLanguage;
  [['header .brand span:last-child','brand'],['.nav-links a:nth-child(1)','navQuiz'],['.nav-links a:nth-child(2)','navList'],['.nav-links a:nth-child(3)','navTry'],['.quiz-hero .eyebrow','eyebrow'],['.hero-copy .lede','lede'],['.hero-copy .button','start'],['.hint','hint'],['#checkButton','check'],['#nextButton','next'],['.list-section .eyebrow','listEyebrow'],['.section-head > p:last-child','listIntro'],['.tips .eyebrow','tipsEyebrow'],['.tip-list > div:nth-child(1) p','tip1'],['.tip-list > div:nth-child(2) p','tip2'],['.tip-list > div:nth-child(3) p','tip3'],['.site-footer > span','brand'],['.site-footer a:nth-child(1)','footerQuiz'],['.site-footer a:nth-child(2)','footerList']].forEach(([selector,key]) => { const element = document.querySelector(selector); if (element) element.textContent = strings[key]; });
  document.querySelector('.hero-copy h1').innerHTML = strings.hero;
  document.querySelector('.section-head h2').innerHTML = strings.listTitle;
  document.querySelector('.tips h2').innerHTML = strings.tipsTitle;
  document.querySelector('.quiz-card .hint').textContent = strings.hint;
  input.placeholder = strings.placeholder;
  input.setAttribute('aria-label', strings.aria);
  renderQuestion();
}

checkButton.addEventListener('click', () => {
  const answer = input.value.trim().replace(/\s/g, '');
  if (!answer) { feedback.textContent = currentCopy().empty; return; }
  const correct = answer === questions[index][1];
  if (correct) { score += 1; feedback.textContent = tr('correct', { kanji: questions[index][0], answer: questions[index][1] }); feedback.className = 'feedback is-success'; }
  else { feedback.textContent = tr('wrong', { answer: questions[index][1] }); feedback.className = 'feedback is-wrong'; }
  scoreLabel.textContent = `${currentCopy().score} ${score}`;
  input.disabled = true;
  checkButton.disabled = true;
  nextButton.disabled = false;
});
nextButton.addEventListener('click', () => { index = (index + 1) % questions.length; renderQuestion(); });
input.addEventListener('keydown', (event) => { if (event.key === 'Enter') checkButton.click(); });
document.querySelector('#languageSelect').addEventListener('change', (event) => { currentLanguage = event.target.value; localStorage.setItem('site-language', currentLanguage); applyLanguage(); });
applyLanguage();
reportVisit();

