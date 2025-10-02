// frontend/src/js/script.js
// Анимация букв
function initNexusAnimation() {
  console.log('nexusAnimation loaded');
  const title = "NEXUS AI";
  const container = document.getElementById('nexusText');
  container.innerHTML = '';
  [...title].forEach((ch, i) => {
    const span = document.createElement('span');
    span.textContent = ch === ' ' ? '\u00A0' : ch;
    span.style.animationDelay = (i * 0.06) + 's';
    container.appendChild(span);
  });
}

// Параллакс
function initParallax() {
  console.log('parallax loaded');
  const center = document.querySelector('.center');
  const imgWrap = document.getElementById('nexusIllustration');
  const bubbleL = document.getElementById('bubble-left');
  const bubbleR = document.getElementById('bubble-right');
  const neuralLayer = document.querySelector('.neural.parallax-layer');

  document.addEventListener('mousemove', (e) => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const nx = (e.clientX - w / 2) / (w / 2);
    const ny = (e.clientY - h / 2) / (h / 2);
    const tx = nx * 8;
    const ty = ny * 8;
    const rx = ny * 6;
    const ry = -nx * 10;
    imgWrap.style.transform = `perspective(900px) translate3d(${tx}px, ${ty}px, 0) rotateX(${rx}deg) rotateY(${ry}deg)`;
    bubbleL.style.transform = `translate3d(${nx * -18}px, ${ny * -8}px, 0)`;
    bubbleR.style.transform = `translate3d(${nx * 18}px, ${ny * 8}px, 0)`;

    // Движение для нейронной сети (медленнее, для глубины)
    if (neuralLayer) {
      neuralLayer.style.transform = `translate3d(${nx * -6}px, ${ny * -4}px, 0) scale(1.02)`;
    }
  });
}

// Карусель
function initCarousel() {
  console.log('carousel loaded');
  const slides = document.querySelectorAll('.slide');
  const dotsContainer = document.getElementById('carouselDots');
  let slideIndex = 0;

  // Создание dots
  slides.forEach((slide, index) => {
    const dot = document.createElement('div');
    dot.classList.add('dot');
    dot.dataset.index = index;
    dot.addEventListener('click', () => showSlide(index));
    dotsContainer.appendChild(dot);
  });
  const dots = dotsContainer.querySelectorAll('.dot');

  function showSlide(i) {
    slideIndex = i;
    slides.forEach(s => s.classList.remove('active'));
    dots.forEach(d => d.classList.remove('active'));
    slides[i].classList.add('active');
    dots[i].classList.add('active');
  }

  document.getElementById('prevBtn').addEventListener('click', () => {
    slideIndex = (slideIndex - 1 + slides.length) % slides.length;
    showSlide(slideIndex);
  });
  document.getElementById('nextBtn').addEventListener('click', () => {
    slideIndex = (slideIndex + 1) % slides.length;
    showSlide(slideIndex);
  });

  let carouselTimer = setInterval(() => {
    slideIndex = (slideIndex + 1) % slides.length;
    showSlide(slideIndex);
  }, 6000);

  document.querySelector('.carousel').addEventListener('mouseover', () => clearInterval(carouselTimer));
  document.querySelector('.carousel').addEventListener('mouseout', () => carouselTimer = setInterval(() => {
    slideIndex = (slideIndex + 1) % slides.length;
    showSlide(slideIndex);
  }, 6000));

  showSlide(0);
}

// Анализ
function initAnalysis() {
  console.log('analysis loaded');
  function pseudoScoreFromTeam(prefix, count = 5) {
    let s = 0;
    for (let i = 1; i <= count; i++) {
      const nick = document.querySelector(`.p-${prefix}-${i}`)?.value.trim() || '';
      const champEl = document.querySelector(`.p-${prefix}-${i}-champ`);
      const champ = champEl ? champEl.value : '';
      const roleEl = document.querySelector(`.p-${prefix}-${i}-role`);
      const role = roleEl ? roleEl.value : '';
      s += (nick.length * 2) + champ.length + role.length;
    }
    return Math.max(1, s);
  }

  document.getElementById('runAnalysis').addEventListener('click', () => {
    let blueScore = pseudoScoreFromTeam('blue');
    let redScore = pseudoScoreFromTeam('red');

    if (blueScore === 0 && redScore === 0) {
      alert('Заполните хотя бы часть полей команд или нажмите демо в хеде.');
      return;
    }

    const total = blueScore + redScore;
    const pBlue = Math.round((blueScore / total) * 100);
    const pRed = 100 - pBlue;

    const bar = document.getElementById('scoreBar');
    const txt = document.getElementById('scoreText');
    txt.textContent = `Синие ${pBlue}% • Красные ${pRed}%`;
    bar.style.width = pBlue + '%';

    const adv = document.getElementById('adviceBox');
    let lines = [];
    if (Math.abs(pBlue - pRed) < 12) {
      lines.push('Матч близок: совет — фокус на вижн и ротации.');
    } else if (pBlue > pRed) {
      lines.push('Синие имеют преимущество: сохранить объекты и контроль карты.');
    } else {
      lines.push('Красные в фаворитах: агрессивное начало и захват риверов улучшат шансы.');
    }
    adv.innerHTML = lines.map(l => `<div>• ${l}</div>`).join('');
  });
}

function initScrollAnimations() {
  console.log('scrollAnimations loaded');
  const sections = document.querySelectorAll('.animate-on-scroll');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  sections.forEach(section => observer.observe(section));
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
  console.log('script.js loaded');
  initNexusAnimation();
  initParallax();
  initCarousel();
  initAnalysis();
  initScrollAnimations();
});