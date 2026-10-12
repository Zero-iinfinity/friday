// Friday — try.js
// Flow: POST prompt -> server returns {status: "clarify", questions} or {status: "ok", operations, download_url}
(function () {
  const form = document.getElementById('tryForm');
  if (!form) return;

  const promptEl = document.getElementById('prompt');
  const genBtn = document.getElementById('genBtn');
  const resetBtn = document.getElementById('resetBtn');
  const clarifyBox = document.getElementById('clarify');
  const clarifyFields = document.getElementById('clarifyFields');
  const steps = Array.from(document.querySelectorAll('#pipeline li'));
  const viewport = document.getElementById('viewport');
  const viewportText = document.getElementById('viewportText');
  const errorEl = document.getElementById('tryError');
  const resultEl = document.getElementById('result');
  const opsEl = document.getElementById('ops');
  const msgEl = document.getElementById('resultMsg');
  const downloadBtn = document.getElementById('downloadBtn');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
  const btnLabel = genBtn.innerHTML;

  let timer = null;

  // Prefill from ?prompt= or example chips
  const qp = new URLSearchParams(window.location.search).get('prompt');
  if (qp) promptEl.value = qp;
  document.getElementById('examplePrompts').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-prompt]');
    if (!chip) return;
    promptEl.value = chip.dataset.prompt;
    promptEl.focus();
  });

  function setSteps(activeIndex, state) {
    steps.forEach((li, i) => {
      li.classList.remove('active', 'done', 'fail');
      if (i < activeIndex) li.classList.add('done');
      else if (i === activeIndex) li.classList.add(state || 'active');
    });
  }
  function clearSteps() { steps.forEach((li) => li.classList.remove('active', 'done', 'fail')); }

  // Fake progress while the request is in flight (real status comes from the response)
  function startProgress() {
    let i = 0;
    setSteps(0);
    timer = setInterval(() => { i = Math.min(i + 1, steps.length - 1); setSteps(i); }, 1400);
  }
  function stopProgress() { clearInterval(timer); timer = null; }

  function showError(text) {
    errorEl.textContent = text;
    errorEl.hidden = false;
    resultEl.hidden = true;
  }

  function renderClarify(questions) {
    clarifyFields.innerHTML = '';
    questions.forEach((q) => {
      const label = document.createElement('label');
      label.textContent = q.text;
      const input = document.createElement('input');
      input.type = 'text';
      input.dataset.qid = q.id;
      input.required = true;
      label.appendChild(input);
      clarifyFields.appendChild(label);
    });
    clarifyBox.hidden = false;
    genBtn.innerHTML = 'Continue <span class="arrow" aria-hidden="true">→</span>';
    clarifyFields.querySelector('input')?.focus();
  }

  function collectAnswers() {
    const answers = {};
    clarifyFields.querySelectorAll('input').forEach((i) => { answers[i.dataset.qid] = i.value.trim(); });
    return answers;
  }

  const FORMAT_LABELS = { step: 'STEP', stl: 'STL', fcstd: 'FreeCAD (.FCStd)', json: 'JSON' };

  function renderResult(data) {
    opsEl.textContent = JSON.stringify(data.operations || [], null, 2);
    msgEl.textContent = data.message || '';

    let list = document.getElementById('downloadList');
    if (!list) {
      list = document.createElement('div');
      list.id = 'downloadList';
      list.style.cssText = 'display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;';
      downloadBtn.insertAdjacentElement('afterend', list);
    }
    list.innerHTML = '';

    const files = data.downloads || {};
    const keys = Object.keys(files);

    if (keys.length) {
      downloadBtn.hidden = true;
      keys.forEach((k) => {
        const a = document.createElement('a');
        a.href = files[k];
        a.download = '';
        a.className = downloadBtn.className;
        a.textContent = 'Download ' + (FORMAT_LABELS[k] || k.toUpperCase());
        list.appendChild(a);
      });
    } else if (data.download_url) {
      downloadBtn.href = data.download_url;
      downloadBtn.hidden = false;
    } else {
      downloadBtn.hidden = true;
    }

    viewport.classList.add('ready');
    viewportText.textContent = data.preview_text || 'Model generated.';
    resultEl.hidden = false;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const prompt = promptEl.value.trim();
    if (!prompt) { showError('Please describe the part you want first.'); promptEl.focus(); return; }

    const answering = !clarifyBox.hidden;
    const payload = { prompt };
    if (answering) {
      payload.answers = collectAnswers();
      if (Object.values(payload.answers).some((v) => !v)) { showError('Please answer all the questions.'); return; }
    }

    errorEl.hidden = true;
    resultEl.hidden = true;
    viewport.classList.remove('ready');
    viewportText.textContent = 'Working on it…';
    genBtn.disabled = true;
    startProgress();

    try {
      const res = await fetch(form.dataset.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      stopProgress();

      if (!res.ok || data.status === 'error') {
        setSteps(0, 'fail');
        viewportText.textContent = 'Something went wrong.';
        showError(data.message || 'The server could not generate a model. Please try again.');
        return;
      }
      if (data.status === 'clarify') {
        setSteps(0, 'active');
        viewportText.textContent = 'Friday needs a bit more detail.';
        renderClarify(data.questions || []);
        return;
      }
      // success
      clarifyBox.hidden = true;
      genBtn.innerHTML = btnLabel;
      setSteps(steps.length);
      renderResult(data);
    } catch (err) {
      stopProgress();
      setSteps(0, 'fail');
      viewportText.textContent = 'Something went wrong.';
      showError('Network error. Check your connection and try again.');
    } finally {
      genBtn.disabled = false;
    }
  });

  resetBtn.addEventListener('click', () => {
    stopProgress();
    form.reset();
    clarifyBox.hidden = true;
    clarifyFields.innerHTML = '';
    genBtn.innerHTML = btnLabel;
    clearSteps();
    errorEl.hidden = true;
    resultEl.hidden = true;
    viewport.classList.remove('ready');
    viewportText.textContent = 'Your model will show up here.';
  });
})();
