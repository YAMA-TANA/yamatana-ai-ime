const input = document.querySelector('#specimenInput');
const specimen = document.querySelector('#liveSpecimen');
const buttons = [...document.querySelectorAll('.style-button')];

input.addEventListener('input', () => { specimen.textContent = input.value || '文字を入力'; });
buttons.forEach((button) => button.addEventListener('click', () => {
  buttons.forEach((item) => item.classList.remove('is-active'));
  button.classList.add('is-active');
  specimen.className = `live-specimen ${button.dataset.style}`;
}));

