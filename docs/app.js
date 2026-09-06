const examples = {
  distance: {
    sentence: 'レーザーで壁までの距離を<span>はかった</span>。',
    candidates: ['測った', '計った', '量った', '図った'],
  },
  time: {
    sentence: '駅まで何分かかるか時間を<span>はかった</span>。',
    candidates: ['計った', '測った', '量った', '図った'],
  },
  weight: {
    sentence: '発送前に荷物の重さを<span>はかった</span>。',
    candidates: ['量った', '測った', '計った', '図った'],
  },
  improve: {
    sentence: '工程を見直し、作業効率の向上を<span>はかった</span>。',
    candidates: ['図った', '測った', '計った', '量った'],
  },
};

const sentence = document.querySelector('#demoSentence');
const stack = document.querySelector('#candidateStack');
const tabs = document.querySelectorAll('.demo-tab');

function renderExample(key) {
  const example = examples[key];
  if (!example || !sentence || !stack) return;

  sentence.innerHTML = example.sentence;
  stack.innerHTML = example.candidates.map((candidate, index) => `
    <div class="candidate ${index === 0 ? 'selected' : ''}">
      <span class="rank">${index + 1}</span>
      <${index === 0 ? 'strong' : 'span'}>${candidate}</${index === 0 ? 'strong' : 'span'}>
      ${index === 0 ? '<span class="match">文脈に一致</span>' : ''}
    </div>
  `).join('');
}

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((item) => {
      item.classList.remove('active');
      item.setAttribute('aria-selected', 'false');
    });
    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    renderExample(tab.dataset.example);
  });
});

const reveals = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  reveals.forEach((item) => observer.observe(item));
} else {
  reveals.forEach((item) => item.classList.add('visible'));
}
