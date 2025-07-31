// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

const pdfStates = {};

document.addEventListener('DOMContentLoaded', () => {
  const pdfElements = document.querySelectorAll('[data-pdf-url]');
  pdfElements.forEach(el => {
    const pdfIndex = el.dataset.pdfIndex;
    const url = el.dataset.pdfUrl;
    const canvas = document.getElementById('pdf-canvas-' + pdfIndex);
    const context = canvas.getContext('2d');

    pdfStates[pdfIndex] = {
      pdfDoc: null,
      pageNum: 1,
      pageRendering: false,
      pageNumPending: null,
      scale: 3.0,
      canvas: canvas,
      context: context
    };

    pdfjsLib.getDocument(url).promise.then(function (pdfDoc_) {
      pdfStates[pdfIndex].pdfDoc = pdfDoc_;
      document.getElementById('page-count-' + pdfIndex).textContent = pdfDoc_.numPages;
      renderPage(pdfIndex, pdfStates[pdfIndex].pageNum);
    });

    // Click for prev/next:
    canvas.addEventListener('click', function (e) {
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;

      if (clickX < rect.width / 2) {
        prevPage(pdfIndex);
      } else {
        nextPage(pdfIndex);
      }
    });

    // Swipe for prev/next:
    let touchStartX = 0;

    canvas.addEventListener('touchstart', function (e) {
      touchStartX = e.changedTouches[0].screenX;
    });

    canvas.addEventListener('touchend', function (e) {
      const touchEndX = e.changedTouches[0].screenX;
      const diff = touchEndX - touchStartX;

      if (Math.abs(diff) > 50) {
        if (diff > 0) {
          prevPage(pdfIndex);
        } else {
          nextPage(pdfIndex);
        }
      }
    });
  });

  // Scroll and animation for boxes:
  if (window.innerWidth <= 782) {
    const firstBox = document.querySelector('.schedule-box');
    if (firstBox) {
      firstBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
      firstBox.classList.add('highlight');
    }
  }

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        entry.target.classList.add('lift');
      } else {
        entry.target.classList.remove('lift');
      }
    });
  }, {
    threshold: 0.15,
    rootMargin: '-25% 0px -25% 0px'
  });

  document.querySelectorAll('.schedule-box').forEach(box => {
    observer.observe(box);
  });

  // Modal behavior
  const modal = document.getElementById("welcomeModal");
  const span = document.querySelector(".close");
  const link = document.getElementById("showWelcomeLink");

  if (window.SHOW_WELCOME === true) {
    modal.style.display = "flex";
  } else {
    modal.style.display = "none";
  }

  span.onclick = () => {
    modal.style.display = "none";
  };

  window.onclick = (event) => {
    if (event.target == modal) {
      modal.style.display = "none";
    }
  };

  link.onclick = (e) => {
    e.preventDefault();
    modal.style.display = "flex";
  };
});

function renderPage(pdfIndex, num) {
  const state = pdfStates[pdfIndex];
  state.pageRendering = true;

  state.pdfDoc.getPage(num).then(function (page) {
    const viewport = page.getViewport({ scale: state.scale });
    state.canvas.height = viewport.height;
    state.canvas.width = viewport.width;

    const renderContext = {
      canvasContext: state.context,
      viewport: viewport
    };

    const renderTask = page.render(renderContext);

    renderTask.promise.then(function () {
      state.pageRendering = false;

      if (state.pageNumPending !== null) {
        renderPage(pdfIndex, state.pageNumPending);
        state.pageNumPending = null;
      }
    });

    document.getElementById('page-num-' + pdfIndex).textContent = num;
  });
}

function queueRenderPage(pdfIndex, num) {
  const state = pdfStates[pdfIndex];
  if (state.pageRendering) {
    state.pageNumPending = num;
  } else {
    renderPage(pdfIndex, num);
  }
}

function prevPage(pdfIndex) {
  const state = pdfStates[pdfIndex];
  if (state.pageNum <= 1) return;
  state.pageNum--;
  queueRenderPage(pdfIndex, state.pageNum);
}

function nextPage(pdfIndex) {
  const state = pdfStates[pdfIndex];
  if (state.pageNum >= state.pdfDoc.numPages) return;
  state.pageNum++;
  queueRenderPage(pdfIndex, state.pageNum);
}

function zoomIn(pdfIndex) {
  const state = pdfStates[pdfIndex];
  state.scale = Math.min(state.scale + 0.2, 3.0);
  queueRenderPage(pdfIndex, state.pageNum);
}

function zoomOut(pdfIndex) {
  const state = pdfStates[pdfIndex];
  state.scale = Math.max(state.scale - 0.2, 0.5);
  queueRenderPage(pdfIndex, state.pageNum);
}

console.log(`Modal state seen by browser: `, window.SHOW_WELCOME);
