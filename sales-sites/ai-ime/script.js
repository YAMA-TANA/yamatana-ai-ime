const status = document.querySelector('#demoStatus');
const input = document.querySelector('#imeInput');
const candidates = [...document.querySelectorAll('.candidate')];
const rankButton = document.querySelector('#rankButton');

function chooseCandidate(button) {
  candidates.forEach((candidate) => candidate.classList.remove('is-selected'));
  button.classList.add('is-selected');
  status.textContent = `「${input.value || 'だいごい'}」を「${button.dataset.candidate}」として選択しました。`;
  status.classList.add('is-success');
}

candidates.forEach((button) => button.addEventListener('click', () => chooseCandidate(button)));
rankButton.addEventListener('click', () => {
  rankButton.textContent = '候補を更新';
  status.textContent = `「${input.value || 'だいごい'}」の候補を文脈順に表示しています。`;
  status.classList.remove('is-success');
});

