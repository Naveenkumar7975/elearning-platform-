// ---------- helpers ----------
const $app = document.getElementById('app');
const $nav = document.getElementById('nav');

const session = {
  get token() { return localStorage.getItem('token'); },
  get user() { try { return JSON.parse(localStorage.getItem('user')); } catch { return null; } },
  save(d) {
    localStorage.setItem('token', d.token);
    localStorage.setItem('user', JSON.stringify({ username: d.username, role: d.role }));
  },
  clear() { localStorage.removeItem('token'); localStorage.removeItem('user'); },
};

// Escape user-provided text before putting it into innerHTML (prevents XSS).
const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function errorText(d) {
  if (!d) return '';
  if (typeof d === 'string') return d;
  if (d.detail) return d.detail;
  return Object.entries(d).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`).join(' | ');
}

async function api(path, method = 'GET', body) {
  const headers = { 'Content-Type': 'application/json' };
  if (session.token) headers['Authorization'] = 'Token ' + session.token;
  const res = await fetch('/api' + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (res.status === 401 && session.token) { session.clear(); location.reload(); }
  if (!res.ok) throw new Error(errorText(data) || 'Request failed');
  return data;
}

let flashTimer;
function flash(msg, ok = true) {
  const el = document.getElementById('flash');
  el.textContent = msg;
  el.className = 'flash ' + (ok ? 'ok' : 'err');
  el.hidden = false;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => { el.hidden = true; }, 3500);
}

// ---------- views ----------
function renderNav() {
  const u = session.user;
  $nav.innerHTML = u ? `
    <a href="#" data-action="courses">All Courses</a>
    <a href="#" data-action="mine">${u.role === 'instructor' ? 'My Teaching' : 'My Learning'}</a>
    <span class="who">${esc(u.username)} (${esc(u.role)})</span>
    <a href="#" data-action="logout">Logout</a>` : '';
}

function authView(mode = 'login') {
  const reg = mode === 'register';
  $app.innerHTML = `
    <div class="panel auth">
      <h2>${reg ? 'Create account' : 'Welcome back'}</h2>
      <form data-form="${mode}">
        <label>Username</label><input name="username" required>
        <label>Password</label><input name="password" type="password" minlength="6" required>
        ${reg ? `<label>I am a</label>
          <select name="role"><option value="student">Student</option><option value="instructor">Instructor</option></select>` : ''}
        <button type="submit">${reg ? 'Register' : 'Login'}</button>
      </form>
      <p class="muted">${reg ? 'Already have an account?' : 'New here?'}
        <a href="#" data-action="switch-auth" data-mode="${reg ? 'login' : 'register'}">${reg ? 'Login' : 'Register'}</a></p>
    </div>`;
}

function courseCard(c) {
  const bar = c.is_enrolled
    ? `<div class="bar"><span style="width:${Number(c.progress_percent)}%"></span></div>
       <div class="muted">${Number(c.progress_percent)}% complete</div>` : '';
  return `<div class="card">
    <h3>${esc(c.title)}</h3>
    <p class="muted">by ${esc(c.instructor_name)} &middot; ${Number(c.lesson_count)} lessons</p>
    <p>${esc(c.description)}</p>${bar}
    <button data-action="open" data-id="${c.id}">View course</button>
  </div>`;
}

async function coursesView() {
  const courses = await api('/courses/');
  $app.innerHTML = `<h1>All Courses</h1>` +
    (courses.length ? `<div class="grid">${courses.map(courseCard).join('')}</div>`
                    : `<p class="muted">No courses yet. Instructors can create one from "My Teaching".</p>`);
}

async function mineView() {
  const u = session.user;
  const courses = await api('/courses/mine/');
  const create = u.role === 'instructor' ? `
    <div class="panel"><h2>Create a course</h2>
      <form data-form="course">
        <label>Title</label><input name="title" required>
        <label>Description</label><textarea name="description" rows="3"></textarea>
        <button type="submit">Create course</button>
      </form></div>` : '';
  $app.innerHTML = `<h1>${u.role === 'instructor' ? 'My Teaching' : 'My Learning'}</h1>${create}` +
    (courses.length ? `<div class="grid">${courses.map(courseCard).join('')}</div>`
                    : `<p class="muted">Nothing here yet.</p>`);
}

async function courseView(id) {
  const c = await api(`/courses/${id}/`);
  const u = session.user;
  const done = new Set(c.completed_lesson_ids);

  const lessons = c.lessons.map(l => {
    if (!c.can_access) return `<div class="lesson"><h3>${esc(l.title)}</h3><p class="muted">Enroll to unlock.</p></div>`;
    const video = l.video_url ? `<p><a href="${esc(l.video_url)}" target="_blank" rel="noopener noreferrer">Watch video</a></p>` : '';
    const btn = (!c.is_owner && !done.has(l.id))
      ? `<button class="secondary" data-action="complete" data-id="${l.id}" data-course="${c.id}">Mark complete</button>` : '';
    return `<div class="lesson ${done.has(l.id) ? 'done' : ''}">
      <h3>${esc(l.title)}</h3><pre>${esc(l.content)}</pre>${video}${btn}</div>`;
  }).join('') || '<p class="muted">No lessons yet.</p>';

  const enroll = (!c.is_owner && !c.is_enrolled)
    ? `<button data-action="enroll" data-id="${c.id}">Enroll</button>` : '';
  const progress = c.is_enrolled
    ? `<div class="bar"><span style="width:${Number(c.progress_percent)}%"></span></div>
       <div class="muted">${Number(c.progress_percent)}% complete</div>` : '';
  const quizBtn = c.can_access ? `<button data-action="quiz" data-id="${c.id}">Take quiz</button>` : '';

  const ownerTools = c.is_owner ? `
    <div class="panel"><h2>Add a lesson</h2>
      <form data-form="lesson" data-course="${c.id}">
        <label>Title</label><input name="title" required>
        <label>Content</label><textarea name="content" rows="4"></textarea>
        <div class="row">
          <div><label>Video link (optional)</label><input name="video_url" type="url" placeholder="https://..."></div>
          <div><label>Order</label><input name="order" type="number" min="0" value="0"></div>
        </div>
        <button type="submit">Add lesson</button>
      </form></div>
    <div class="panel"><h2>Add a quiz question</h2>
      <form data-form="question" data-course="${c.id}">
        <label>Question</label><input name="text" required>
        <div class="row"><div><label>Option A</label><input name="option_a" required></div>
          <div><label>Option B</label><input name="option_b" required></div></div>
        <div class="row"><div><label>Option C</label><input name="option_c" required></div>
          <div><label>Option D</label><input name="option_d" required></div></div>
        <label>Correct option</label>
        <select name="correct_option"><option>A</option><option>B</option><option>C</option><option>D</option></select>
        <button type="submit">Add question</button>
      </form></div>` : '';

  $app.innerHTML = `
    <div class="panel">
      <h1>${esc(c.title)}</h1>
      <p class="muted">by ${esc(c.instructor_name)}</p>
      <p>${esc(c.description)}</p>${progress}${enroll} ${quizBtn}
    </div>
    <div class="panel"><h2>Lessons</h2>${lessons}</div>
    <div id="quiz-area"></div>
    ${ownerTools}`;
}

async function quizView(id) {
  const qs = await api(`/courses/${id}/quiz/`);
  const area = document.getElementById('quiz-area');
  if (!qs.length) { area.innerHTML = '<div class="panel"><p class="muted">No quiz questions yet.</p></div>'; return; }
  area.innerHTML = `<div class="panel"><h2>Quiz</h2>
    <form data-form="quiz" data-course="${id}">
      ${qs.map((q, i) => `<div class="question"><strong>${i + 1}. ${esc(q.text)}</strong>
        ${['a', 'b', 'c', 'd'].map(k => `<label><input type="radio" name="q_${q.id}" value="${k.toUpperCase()}" required>
          ${k.toUpperCase()}. ${esc(q['option_' + k])}</label>`).join('')}</div>`).join('')}
      <button type="submit">Submit answers</button>
      <div class="result" id="quiz-result"></div>
    </form></div>`;
  area.scrollIntoView({ behavior: 'smooth' });
}

// ---------- events ----------
document.addEventListener('click', async e => {
  const el = e.target.closest('[data-action]');
  if (!el) return;
  e.preventDefault();
  const { action, id } = el.dataset;
  try {
    if (action === 'courses') await coursesView();
    else if (action === 'mine') await mineView();
    else if (action === 'logout') { session.clear(); start(); }
    else if (action === 'open') await courseView(id);
    else if (action === 'enroll') { await api(`/courses/${id}/enroll/`, 'POST'); flash('Enrolled!'); await courseView(id); }
    else if (action === 'complete') { await api(`/lessons/${id}/complete/`, 'POST'); flash('Lesson completed'); await courseView(el.dataset.course); }
    else if (action === 'quiz') await quizView(id);
    else if (action === 'switch-auth') authView(el.dataset.mode);
  } catch (err) { flash(err.message, false); }
});

document.addEventListener('submit', async e => {
  const form = e.target.closest('[data-form]');
  if (!form) return;
  e.preventDefault();
  const f = Object.fromEntries(new FormData(form));
  const cid = form.dataset.course;
  try {
    switch (form.dataset.form) {
      case 'login':
      case 'register': {
        const d = await api('/' + form.dataset.form + '/', 'POST', f);
        session.save(d);
        start();
        break;
      }
      case 'course':
        await api('/courses/', 'POST', f);
        flash('Course created');
        await mineView();
        break;
      case 'lesson':
        f.order = Number(f.order || 0);
        await api(`/courses/${cid}/lessons/`, 'POST', f);
        flash('Lesson added');
        await courseView(cid);
        break;
      case 'question':
        await api(`/courses/${cid}/questions/`, 'POST', f);
        flash('Question added');
        await courseView(cid);
        break;
      case 'quiz': {
        const answers = {};
        form.querySelectorAll('input[type=radio]:checked').forEach(r => { answers[r.name.replace('q_', '')] = r.value; });
        const res = await api(`/courses/${cid}/submit-quiz/`, 'POST', { answers });
        document.getElementById('quiz-result').textContent = `Score: ${res.score} / ${res.total}`;
        break;
      }
    }
  } catch (err) { flash(err.message, false); }
});

function start() {
  renderNav();
  if (session.user) coursesView().catch(err => flash(err.message, false));
  else authView('login');
}
start();
