const COMMON_API = 'https://form-lens-api.hurukigeoetym.workers.dev';
function reportVisit() { fetch(`${COMMON_API}/api/events`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ site: 'kanji-quiz', eventName: 'page_view' }) }).catch(() => {}); }

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
  questionNumber.textContent = `QUESTION ${String(index + 1).padStart(2, '0')}`;
  input.value = '';
  input.disabled = false;
  checkButton.disabled = false;
  nextButton.disabled = true;
  feedback.textContent = '読みを入力して答え合わせしてください。';
  feedback.className = 'feedback';
  input.focus();
}

checkButton.addEventListener('click', () => {
  const answer = input.value.trim().replace(/\s/g, '');
  if (!answer) { feedback.textContent = '読みを入力してください。'; return; }
  const correct = answer === questions[index][1];
  if (correct) { score += 1; feedback.textContent = `正解。${questions[index][0]}は「${questions[index][1]}」と読みます。`; feedback.className = 'feedback is-success'; }
  else { feedback.textContent = `答えは「${questions[index][1]}」。もう一度覚えておきましょう。`; feedback.className = 'feedback is-wrong'; }
  scoreLabel.textContent = `SCORE ${score}`;
  input.disabled = true;
  checkButton.disabled = true;
  nextButton.disabled = false;
});
nextButton.addEventListener('click', () => { index = (index + 1) % questions.length; renderQuestion(); });
input.addEventListener('keydown', (event) => { if (event.key === 'Enter') checkButton.click(); });
renderQuestion();
reportVisit();

