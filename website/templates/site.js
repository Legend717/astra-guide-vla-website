/* Progressive enhancements. The report, tables and video links work without JS. */
document.documentElement.classList.add('js');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function setupFigures() {
  const dialog = document.querySelector('.image-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  document.querySelectorAll('a[data-zoom]').forEach(link => {
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey) return;
      event.preventDefault();
      const image = dialog.querySelector('img');
      image.src = link.href;
      image.alt = link.querySelector('img')?.alt || 'Expanded report figure';
      dialog.showModal();
    });
  });
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
}

function setupMechanism() {
  const board = document.querySelector('.mechanism');
  if (!board) return;
  const play = document.getElementById('motion-play');
  const next = document.getElementById('motion-next');
  const previous = document.getElementById('motion-prev');
  const caption = document.getElementById('phase-caption');
  let phase = 0;
  let scenario = 'budget';
  let timer = null;
  const total = 18;
  const names = ['Reach', 'Grasp', 'Transport', 'Place'];
  // One shared storyboard clock advances both rows. Durations are explanatory,
  // not measurements. Each row terminates on its own illustrated success feedback.
  // A monitor interrupts execution; a separate Astra authorization permits resumption.
  const baselineSteps = [0,0,0,16,16,32,32,48,48,64,64,80,80,96,96,100,100,100];
  const harnessSteps = [0,0,0,16,32,48,64,80,96,100,100,100,100,100,100,100,100,100];
  const monitorSteps = [0,0,0,16,32,48,64,64,80,96,100,100,100,100,100,100,100,100];
  function renderLane(kind, controls, state, status) {
    const lane = board.querySelector(`[data-lane="${kind}"]`);
    const index = controls <= 16 ? 0 : controls <= 48 ? 1 : controls < 100 ? 2 : 3;
    lane.dataset.state = state;
    lane.dataset.controls = String(controls);
    lane.querySelector('.lane-status').textContent = status;
    lane.querySelector('.lane-counter').textContent = `${controls} / 100 controls`;
    lane.querySelectorAll('.stage-card').forEach((card, number) => {
      card.classList.toggle('current', number === index);
      card.classList.toggle('completed', number < index);
      card.querySelector('.current-marker').textContent = state === 'done' ? 'FINISHED' : state === 'authorized' ? 'AUTHORIZED' : state === 'review' ? 'PAUSED HERE' : 'CURRENT STEP';
      if (number === index) card.setAttribute('aria-current', 'step');
      else card.removeAttribute('aria-current');
    });
    lane.querySelector('.lane-position').textContent = state === 'done' ? 'Success feedback received · episode ended' : `${names[index]} · ${status}`;
  }
  function render() {
    const early = scenario === 'monitor';
    const h = (early ? monitorSteps : harnessSteps)[phase];
    const b = baselineSteps[phase];
    const baseReview = phase >= 4 && phase <= 14 && phase % 2 === 0;
    const bs = phase < 3 ? 'ready' : phase >= 16 ? 'done' : baseReview ? 'review' : 'execute';
    const hs = phase < 3 ? 'ready' : phase >= (early ? 11 : 10) ? 'done' : early && phase === 7 ? 'authorized' : early && phase === 6 || !early && phase === 9 ? 'review' : 'execute';
    const status = {ready:'Ready',execute:'VLA executing',review:'Waiting for Astra',authorized:'New budget authorized',done:'✓ Task complete'};
    renderLane('baseline', b, bs, status[bs]);
    renderLane('harness', h, hs, status[hs]);
    board.dataset.phase = String(phase);
    board.dataset.scenario = scenario;
    const renewed = early && phase >= 7;
    document.getElementById('budget-label').textContent = renewed ? 'New interval · executed / authorized' : 'Initial interval · executed / authorized';
    document.getElementById('budget-value').textContent = renewed ? `${h - 64} / 40 controls` : `${h} / 100 controls`;
    let title, description;
    if (phase === 0) {
      title = 'Press Play both to start together';
      description = 'Both start together, but finish independently. Follow each bold marker: blue executes, amber pauses for Astra, and green marks a completed task.';
    } else if (phase === 1) {
      title = 'Same subgoal, same starting scene';
      description = 'Astra interprets task history and selects the grounded subgoal. Both rows illustrate placing the same block on the target.';
    } else if (phase === 2) {
      title = 'Choose how often to review';
      description = 'Top: review after each action chunk. Bottom: authorize a 100-control budget with a selected gripper-change monitor.';
    } else if (phase === 3) {
      title = 'Both robots begin executing';
      description = 'Each VLA executes its first 16-control chunk using current observations. Both rows are moving together.';
    } else if (early && phase === 6) {
      title = 'A monitor brings the lower row back early';
      description = 'The selected gripper event prompts earlier review at 64 controls. The lower row pauses for Astra instead of using the rest of its budget.';
    } else if (early && phase === 7) {
      title = 'Astra authorizes a new execution interval';
      description = 'After reviewing the event, Astra keeps the subgoal and explicitly authorizes 40 more controls. The lower robot is still at 64; it resumes on the next step.';
    } else if (early && phase === 8) {
      title = 'Our harness resumes with the new budget';
      description = 'The lower robot executes 16 newly authorized controls, reaching 80 in total. The upper row is paused for another per-chunk review.';
    } else if (!early && phase === 9) {
      title = 'The lower row reaches its budget';
      description = 'The final placement action uses the last of the 100-control budget and triggers review. A full budget alone does not mean success; environment feedback determines the outcome.';
    } else if (hs === 'done' && bs !== 'done') {
      title = 'Our harness has finished. The upper row continues.';
      description = `Illustrated environment feedback confirms success for our harness. Its episode has ended; it is not waiting for the other row. Per-chunk review has reached ${b} controls and still has work to do.`;
    } else if (phase === 16) {
      title = 'Per-chunk review finishes too';
      description = 'The upper row now receives illustrated success feedback. Both tasks are complete. Fewer review pauses let our harness finish earlier in this schematic; the spacing does not encode a measured speedup.';
    } else if (phase === 17) {
      title = 'Later: reflect after the episode';
      description = 'After official episode feedback, Astra may revise advice for later episodes. VLA weights remain fixed. Replay to compare the two review schedules.';
    } else if (hs === 'execute' && bs === 'review') {
      title = 'Top waits. Bottom keeps executing.';
      description = `The upper robot pauses at ${b} controls for another Astra check. The lower robot reaches ${h} controls within its existing budget, using fresh observations.`;
    } else if (hs === 'execute') {
      title = 'The upper row resumes after review';
      description = `Both rows are executing again. Per-chunk review has reached ${b} controls; budgeted execution has reached ${h}.`;
    } else {
      title = 'Astra reviews before more execution';
      description = 'Execution resumes only after Astra grants a new budget. A terminal environment result ends that row independently.';
    }
    document.getElementById('phase-title').textContent = title;
    caption.textContent = description;
    document.getElementById('phase-number').textContent = `Step ${phase + 1} / ${total}`;
    const progress = document.getElementById('comparison-progress');
    progress.max = total - 1;
    progress.value = phase;
    previous.disabled = phase === 0;
    next.disabled = phase === total - 1;
    board.querySelectorAll('.feedback-node').forEach(node => {
      node.classList.toggle('active', node.dataset.node === 'review' && hs === 'review' || node.dataset.node === 'correction' && hs === 'authorized' || node.dataset.node === 'experience' && phase === 17);
    });
  }
  function stop() {
    clearInterval(timer);
    timer = null;
    play.textContent = phase === total - 1 ? 'Replay both' : 'Play both';
    play.setAttribute('aria-label', phase === total - 1 ? 'Replay both comparison rows' : 'Play both comparison rows');
    play.setAttribute('aria-pressed', 'false');
    board.dataset.playing = 'false';
  }
  function start() {
    if (timer) { stop(); return; }
    if (phase === total - 1) phase = 0;
    render();
    play.textContent = 'Pause both';
    play.setAttribute('aria-label','Pause both comparison rows');
    play.setAttribute('aria-pressed','true');
    board.dataset.playing = 'true';
    timer = setInterval(() => {
      phase++;
      render();
      if (phase === total - 1) stop();
    }, 2000);
  }
  play.addEventListener('click', start);
  next.addEventListener('click', () => { phase = Math.min(phase + 1,total - 1); stop(); render(); });
  previous.addEventListener('click', () => { phase = Math.max(phase - 1,0); stop(); render(); });
  document.getElementById('motion-reset').addEventListener('click', () => { phase = 0; stop(); render(); });
  board.querySelectorAll('button[data-scenario]').forEach(button => button.addEventListener('click', () => {
    scenario = button.dataset.scenario;
    phase = 0;
    stop();
    board.querySelectorAll('button[data-scenario]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    render();
  }));
  reducedMotion.addEventListener('change', () => { if (reducedMotion.matches) stop(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  if ('IntersectionObserver' in window) new IntersectionObserver(entries => {
    if (!entries[0].isIntersecting) stop();
  }, {threshold:0}).observe(board);
  // Deliberate start: readers see the introduction before either row moves.
  render();
}

async function setupVideos() {
  const video = document.getElementById('demo-video');
  if (!video) return;
  let videos;
  try {
    const response = await fetch('assets/videos.json');
    if (!response.ok) throw new Error('Video metadata unavailable');
    videos = await response.json();
  } catch (_) {
    // Plain MP4 links remain functional if metadata cannot be loaded.
    document.getElementById('video-chapters').textContent = 'Use the task links to open each video.';
    return;
  }
  let selected = 0;
  const tabs = [...document.querySelectorAll('[data-video]')];
  const chapters = document.getElementById('video-chapters');
  let pendingSeek = null;
  const timeLabel = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}.${Math.round(seconds % 1 * 10)}`;
  function stage() {
    const item = videos[selected];
    const segment = item.segments.filter(entry => entry.time <= video.currentTime + .001).at(-1);
    document.getElementById('video-stage').textContent = segment?.label || 'Reset / demonstration';
    chapters.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === segment?.mode)));
  }
  function select(index) {
    const item = videos[index];
    video.pause();
    pendingSeek = null;
    selected = index;
    video.preload = 'none';
    video.src = `assets/videos/${item.slug}.mp4`;
    video.poster = `assets/videos/${item.slug}-reset.jpg`;
    video.setAttribute('aria-label', `${item.task} episode ${item.episode} rollout`);
    video.playbackRate = Number(document.getElementById('video-speed').value);
    document.getElementById('demo-suite').textContent = item.suite;
    document.getElementById('demo-task').textContent = item.task;
    document.getElementById('demo-description').textContent = item.description;
    document.getElementById('demo-goal').textContent = `“${item.goal}”`;
    document.getElementById('demo-episode').textContent = `Episode ${item.episode}`;
    document.getElementById('demo-interventions').textContent = `${item.interventions} direct intervention${item.interventions === 1 ? '' : 's'}`;
    document.getElementById('video-download').href = video.src;
    tabs.forEach((tab, number) => tab.setAttribute('aria-current', String(number === index)));
    chapters.replaceChildren();
    item.chapters.forEach(chapter => {
      const button = document.createElement('button');
      const time = document.createElement('time');
      button.type = 'button';
      button.dataset.mode = chapter.mode;
      button.textContent = chapter.label;
      button.setAttribute('aria-label', `${chapter.label}, ${timeLabel(chapter.time)}, frame ${chapter.frame}`);
      time.textContent = timeLabel(chapter.time);
      button.append(time);
      button.addEventListener('click', () => {
        if (video.readyState >= 1) video.currentTime = chapter.time;
        else { pendingSeek = chapter.time; video.preload = 'auto'; video.load(); }
      });
      chapters.append(button);
    });
    stage();
  }
  tabs.forEach(tab => tab.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey) return;
    event.preventDefault();
    select(Number(tab.dataset.video));
  }));
  video.addEventListener('loadedmetadata', () => {
    video.playbackRate = Number(document.getElementById('video-speed').value);
    if (pendingSeek !== null) { video.currentTime = pendingSeek; pendingSeek = null; }
  });
  video.addEventListener('timeupdate', stage);
  video.addEventListener('seeked', stage);
  document.getElementById('video-speed').addEventListener('change', event => { video.playbackRate = Number(event.target.value); });
  select(0);
}

function setupResults() {
  document.querySelectorAll('.suite-filter button').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.suite-filter button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    document.querySelectorAll('#task-table tbody tr').forEach(row => { row.hidden = button.dataset.suite !== 'all' && row.dataset.suite !== button.dataset.suite; });
  }));
}

function setupContents() {
  const sidebar = document.querySelector('.report-sidebar');
  if (!sidebar) return;
  const details = sidebar.querySelector('details');
  const narrow = matchMedia('(max-width:767px)');
  details.open = !narrow.matches;
  narrow.addEventListener('change', () => { details.open = !narrow.matches; });
  sidebar.querySelectorAll('nav a').forEach(link => link.addEventListener('click', () => { if (narrow.matches) details.open = false; }));
  if (!('IntersectionObserver' in window)) return;
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      sidebar.querySelectorAll('nav a').forEach(link => link.setAttribute('aria-current', String(link.hash === `#${entry.target.id}`)));
    }
  }, {rootMargin: '-90px 0px -60% 0px'});
  document.querySelectorAll('.report-content h2[id], .report-content h3[id]').forEach(heading => observer.observe(heading));
}

setupFigures();
setupMechanism();
setupVideos();
setupResults();
setupContents();
