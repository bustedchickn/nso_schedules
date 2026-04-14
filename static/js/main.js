const PDF_WORKER_SRC = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
const pdfStates = {};

document.addEventListener('DOMContentLoaded', () => {
  setupPdfViewers();
  setupScheduleAnimations();
  setupWelcomeModal();
  setupNavigationSound();
});

function setupPdfViewers() {
  const pdfElements = document.querySelectorAll('[data-pdf-url]');
  if (!pdfElements.length) {
    return;
  }

  if (!window.pdfjsLib) {
    pdfElements.forEach((el) => showPdfError(el.dataset.pdfIndex));
    return;
  }

  window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDF_WORKER_SRC;

  pdfElements.forEach((el) => {
    const pdfIndex = el.dataset.pdfIndex;
    const url = el.dataset.pdfUrl;
    const canvas = document.getElementById(`pdf-canvas-${pdfIndex}`);

    if (!canvas) {
      return;
    }

    const context = canvas.getContext('2d');
    pdfStates[pdfIndex] = {
      pdfDoc: null,
      pageNum: 1,
      pageRendering: false,
      pageNumPending: null,
      scale: 3.0,
      canvas,
      context,
    };

    window.pdfjsLib.getDocument(url).promise
      .then((pdfDoc) => {
        pdfStates[pdfIndex].pdfDoc = pdfDoc;
        const pageCount = document.getElementById(`page-count-${pdfIndex}`);
        if (pageCount) {
          pageCount.textContent = pdfDoc.numPages;
        }
        renderPage(pdfIndex, pdfStates[pdfIndex].pageNum);
      })
      .catch(() => showPdfError(pdfIndex));

    canvas.addEventListener('click', (event) => {
      const rect = canvas.getBoundingClientRect();
      const clickX = event.clientX - rect.left;

      if (clickX < rect.width / 2) {
        prevPage(pdfIndex);
      } else {
        nextPage(pdfIndex);
      }
    });

    let touchStartX = 0;

    canvas.addEventListener('touchstart', (event) => {
      touchStartX = event.changedTouches[0].screenX;
    }, { passive: true });

    canvas.addEventListener('touchend', (event) => {
      const touchEndX = event.changedTouches[0].screenX;
      const diff = touchEndX - touchStartX;

      if (Math.abs(diff) <= 50) {
        return;
      }

      if (diff > 0) {
        prevPage(pdfIndex);
      } else {
        nextPage(pdfIndex);
      }
    }, { passive: true });
  });

  document.querySelectorAll('[data-pdf-action]').forEach((button) => {
    button.addEventListener('click', () => {
      if (button.dataset.pdfAction === 'prev') {
        prevPage(button.dataset.pdfIndex);
      } else {
        nextPage(button.dataset.pdfIndex);
      }
    });
  });
}

function showPdfError(pdfIndex) {
  const canvas = document.getElementById(`pdf-canvas-${pdfIndex}`);
  const error = document.getElementById(`pdf-error-${pdfIndex}`);
  const controls = document.getElementById(`pdf-controls-${pdfIndex}`);

  if (canvas) {
    canvas.hidden = true;
  }
  if (error) {
    error.hidden = false;
  }
  if (controls) {
    controls.hidden = true;
  }
}

function renderPage(pdfIndex, num) {
  const state = pdfStates[pdfIndex];
  if (!state || !state.pdfDoc) {
    return;
  }

  state.pageRendering = true;

  state.pdfDoc.getPage(num)
    .then((page) => {
      const viewport = page.getViewport({ scale: state.scale });
      state.canvas.height = viewport.height;
      state.canvas.width = viewport.width;

      return page.render({
        canvasContext: state.context,
        viewport,
      }).promise;
    })
    .then(() => {
      state.pageRendering = false;

      if (state.pageNumPending !== null) {
        renderPage(pdfIndex, state.pageNumPending);
        state.pageNumPending = null;
      }
    })
    .catch(() => showPdfError(pdfIndex));

  const pageNum = document.getElementById(`page-num-${pdfIndex}`);
  if (pageNum) {
    pageNum.textContent = `Page ${num}`;
  }
}

function queueRenderPage(pdfIndex, num) {
  const state = pdfStates[pdfIndex];
  if (!state || !state.pdfDoc) {
    return;
  }

  if (state.pageRendering) {
    state.pageNumPending = num;
  } else {
    renderPage(pdfIndex, num);
  }
}

function prevPage(pdfIndex) {
  const state = pdfStates[pdfIndex];
  if (!state || !state.pdfDoc || state.pageNum <= 1) {
    return;
  }

  state.pageNum -= 1;
  queueRenderPage(pdfIndex, state.pageNum);
}

function nextPage(pdfIndex) {
  const state = pdfStates[pdfIndex];
  if (!state || !state.pdfDoc || state.pageNum >= state.pdfDoc.numPages) {
    return;
  }

  state.pageNum += 1;
  queueRenderPage(pdfIndex, state.pageNum);
}

function zoomIn(pdfIndex) {
  const state = pdfStates[pdfIndex];
  if (!state) {
    return;
  }

  state.scale = Math.min(state.scale + 0.2, 3.0);
  queueRenderPage(pdfIndex, state.pageNum);
}

function zoomOut(pdfIndex) {
  const state = pdfStates[pdfIndex];
  if (!state) {
    return;
  }

  state.scale = Math.max(state.scale - 0.2, 0.5);
  queueRenderPage(pdfIndex, state.pageNum);
}

function setupScheduleAnimations() {
  if (window.innerWidth <= 782) {
    const firstBox = document.querySelector('.schedule-box');
    if (firstBox) {
      firstBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
      firstBox.classList.add('highlight');
    }
  }

  const boxes = document.querySelectorAll('.schedule-box');
  if (!('IntersectionObserver' in window)) {
    boxes.forEach((box) => box.classList.add('in-view'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        entry.target.classList.add('lift');
      } else {
        entry.target.classList.remove('lift');
      }
    });
  }, {
    threshold: 0.15,
    rootMargin: '-25% 0px -25% 0px',
  });

  boxes.forEach((box) => observer.observe(box));
}

function setupWelcomeModal() {
  const modal = document.getElementById('welcomeModal');
  const closeButton = document.querySelector('.close');
  const link = document.getElementById('showWelcomeLink');

  if (!modal || !closeButton || !link) {
    return;
  }

  const openModal = () => {
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
  };

  const closeModal = () => {
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
  };

  if (window.SHOW_WELCOME === true) {
    openModal();
  }

  closeButton.addEventListener('click', closeModal);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeModal();
    }
  });
  link.addEventListener('click', (event) => {
    event.preventDefault();
    openModal();
  });
}

function setupNavigationSound() {
  if (!window.CLICK_SOUND_URL) {
    return;
  }

  const clickSound = new Audio(window.CLICK_SOUND_URL);
  document.querySelectorAll('.top-nav a').forEach((link) => {
    link.addEventListener('click', () => {
      clickSound.currentTime = 0;
      clickSound.volume = 0.3;
      clickSound.play().catch(() => {});
    });
  });
}
