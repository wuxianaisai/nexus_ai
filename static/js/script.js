document.addEventListener('DOMContentLoaded', () => {
  console.log('script.js loaded');

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
      if (imgWrap) {
        imgWrap.style.transform = `perspective(900px) translate3d(${tx}px, ${ty}px, 0) rotateX(${rx}deg) rotateY(${ry}deg)`;
      }
      if (bubbleL) {
        bubbleL.style.transform = `translate3d(${nx * -18}px, ${ny * -8}px, 0)`;
      }
      if (bubbleR) {
        bubbleR.style.transform = `translate3d(${nx * 18}px, ${ny * 8}px, 0)`;
      }
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
    const runButton = document.getElementById('runAnalysis');
    const scoreBar = document.getElementById('scoreBar');
    const scoreText = document.getElementById('scoreText');
    const adviceBox = document.getElementById('adviceBox');

    const roleMapping = {
      'Топ': 'TOP',
      'Джунгли': 'JUNGLE',
      'Мид': 'MIDDLE',
      'Бот': 'BOTTOM',
      'Саппорт': 'UTILITY'
    };

    // Загрузка чемпионов
    async function loadChampions() {
      try {
        const response = await fetch('/champions');
        if (!response.ok) throw new Error('Ошибка загрузки чемпионов');
        const champions = await response.json();
        document.querySelectorAll('.champ-select select[class$="-champ"]').forEach(select => {
          select.innerHTML = '<option>Выберите чемпиона...</option>' + champions.map(champ => `<option>${champ}</option>`).join('');
        });
      } catch (error) {
        console.error('Ошибка загрузки чемпионов:', error);
        alert('Не удалось загрузить список чемпионов.');
      }
    }

    // Загрузка ролей
    async function loadRoles() {
      try {
        const response = await fetch('/roles');
        if (!response.ok) throw new Error('Ошибка загрузки ролей');
        const roles = await response.json();
        const roleLabels = {
          'TOP': 'Топ',
          'JUNGLE': 'Джунгли',
          'MIDDLE': 'Мид',
          'BOTTOM': 'Бот',
          'UTILITY': 'Саппорт'
        };
        document.querySelectorAll('.champ-select select[class$="-role"]').forEach(select => {
          select.innerHTML = roles.map(role => `<option>${roleLabels[role] || role}</option>`).join('');
        });
      } catch (error) {
        console.error('Ошибка загрузки ролей:', error);
        alert('Не удалось загрузить список ролей.');
      }
    }

    // Вызов загрузки данных
    loadChampions();
    loadRoles();

    runButton.addEventListener('click', async () => {
      runButton.disabled = true;
      runButton.textContent = 'Анализирую...';

      // Собираем данные формы
      const blueTeam = [];
      const redTeam = [];
      const errors = [];

      // Проверка корректности ника
      function validateNick(nick, team, index) {
        if (!nick) {
          return `Ник для ${team} игрока ${index} не заполнен.`;
        }
        const parts = nick.split('#');
        if (parts.length !== 2 || !parts[0].trim() || !parts[1].trim()) {
          return `Неверный формат ника для ${team} игрока ${index}: ожидается GameName#TAG.`;
        }
        return null;
      }

      // Проверка корректности чемпиона и роли
      function validateChampAndRole(champ, role, team, index) {
        if (champ === 'Выберите чемпиона...') {
          return `Чемпион для ${team} игрока ${index} не выбран.`;
        }
        if (!role || role === 'UNKNOWN') {
          return `Роль для ${team} игрока ${index} не выбрана.`;
        }
        return null;
      }

      // Проверяем синюю команду
      for (let i = 1; i <= 5; i++) {
        const blueNick = document.querySelector(`.p-blue-${i}`).value.trim();
        const blueChamp = document.querySelector(`.p-blue-${i}-champ`).value;
        const blueRoleEl = document.querySelector(`.p-blue-${i}-role`);
        const blueRole = roleMapping[blueRoleEl.value] || 'UNKNOWN';

        const nickError = validateNick(blueNick, 'Blue', i);
        if (nickError) errors.push(nickError);

        const champRoleError = validateChampAndRole(blueChamp, blueRole, 'Blue', i);
        if (champRoleError) errors.push(champRoleError);

        if (!nickError && !champRoleError) {
          const [game_name, tag_line] = blueNick.split('#').map(s => s.trim());
          blueTeam.push({
            game_name,
            tag_line,
            role: blueRole,
            champion: blueChamp
          });
        }
      }

      // Проверяем красную команду
      for (let i = 1; i <= 5; i++) {
        const redNick = document.querySelector(`.p-red-${i}`).value.trim();
        const redChamp = document.querySelector(`.p-red-${i}-champ`).value;
        const redRoleEl = document.querySelector(`.p-red-${i}-role`);
        const redRole = roleMapping[redRoleEl.value] || 'UNKNOWN';

        const nickError = validateNick(redNick, 'Red', i);
        if (nickError) errors.push(nickError);

        const champRoleError = validateChampAndRole(redChamp, redRole, 'Red', i);
        if (champRoleError) errors.push(champRoleError);

        if (!nickError && !champRoleError) {
          const [game_name, tag_line] = redNick.split('#').map(s => s.trim());
          redTeam.push({
            game_name,
            tag_line,
            role: redRole,
            champion: redChamp
          });
        }
      }

      // Если есть ошибки, показываем их
      if (errors.length > 0) {
        alert(errors.join('\n'));
        runButton.disabled = false;
        runButton.textContent = 'Проанализировать';
        return;
      }

      // Отправка на backend
      try {
        const response = await fetch('/predict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ blue_team: blueTeam, red_team: redTeam })
        });
        const result = await response.json();

        if (result.status === 'success') {
          scoreText.textContent = `Синие ${result.blue_win.toFixed(1)}% • Красные ${result.red_win.toFixed(1)}%`;
          scoreBar.style.width = `${result.blue_win}%`;

          const diff = Math.abs(result.blue_win - result.red_win);
          let advice = '';
          if (diff < 12) {
            advice = '• Нормально';
          } else if (result.blue_win > result.red_win) {
            advice = '• Синие.';
          } else {
            advice = '• Красные.';
          }
          adviceBox.innerHTML = `<div>${advice}</div>`;
        } else {
          alert(`Ошибка: ${result.message}`);
        }
      } catch (error) {
        alert(`Ошибка связи с сервером: ${error.message}`);
      } finally {
        runButton.disabled = false;
        runButton.textContent = 'Проанализировать';
      }
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
  initNexusAnimation();
  initParallax();
  initCarousel();
  initAnalysis();
  initScrollAnimations();
});