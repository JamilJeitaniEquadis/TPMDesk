/* Project planner: one standard plan -> checks -> Excel with a RACI sheet and/or a Gantt sheet.
   Runs alone (portal) or inside the TPM Desk (iframe). Nothing is stored: the exported Excel carries
   the plan in a hidden sheet, and "Open a saved plan" reads it back. */
(() => {
'use strict';
const $ = s => document.querySelector(s);
const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
const uid = () => Math.random().toString(36).slice(2, 9);

/* ---------- dates: 'YYYY-MM-DD' strings, day numbers in UTC (no DST surprises) ---------- */
const dn = s => { if (!/^\d{4}-\d{2}-\d{2}$/.test(s || '')) return null; const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d) / 864e5; };
const ds = n => new Date(n * 864e5).toISOString().slice(0, 10);
const todayN = () => { const t = new Date(); return Date.UTC(t.getFullYear(), t.getMonth(), t.getDate()) / 864e5; };
const monday = n => n - ((new Date(n * 864e5).getUTCDay() + 6) % 7);
const fmt = s => s ? s.split('-').reverse().join('/') : '';

/* ---------- export wording ---------- */
const ST = ['ns', 'ot', 'ar', 'bl', 'co'];
const L = {
  en: { st: { ns: 'Not Started', ot: 'On Track', ar: 'At Risk', bl: 'Blocked', co: 'Completed' },
        raci: 'RACI', gantt: 'Gantt', task: 'Phase / Task', status: 'Status', R: 'Responsible (R)', A: 'Accountable (A)',
        C: 'Consulted (C)', I: 'Informed (I)', comment: 'Comment', resp: 'Responsible', start: 'Start', end: 'End', days: 'Days',
        pm: 'Project manager', updated: 'updated', done: 'done', roles: 'Roles', code: 'Code', role: 'Role', name: 'Name', side: 'Side',
        legend: ['R - Responsible: does the work', 'A - Accountable: owns the task and approves it (one per task)',
                 'C - Consulted: gives input before', 'I - Informed: kept up to date after'],
        glegend: 'Blue: on track · Green: completed · Grey: not started · Red: late or blocked · Amber: milestone · Today is highlighted', locale: 'en-GB' },
  fr: { st: { ns: 'Non démarré', ot: 'En cours', ar: 'À risque', bl: 'Bloqué', co: 'Terminé' },
        raci: 'RACI', gantt: 'Gantt', task: 'Phase / Tâche', status: 'Statut', R: 'Réalise (R)', A: 'Valide (A)',
        C: 'Consulté (C)', I: 'Informé (I)', comment: 'Commentaire', resp: 'Responsable', start: 'Début', end: 'Fin', days: 'Jours',
        pm: 'Chef de projet', updated: 'mis à jour le', done: 'terminées', roles: 'Rôles', code: 'Code', role: 'Rôle', name: 'Nom', side: 'Côté',
        legend: ['R - Réalise : fait le travail', 'A - Valide : porte la tâche et la valide (un seul par tâche)',
                 'C - Consulté : donne son avis avant', 'I - Informé : tenu au courant après'],
        glegend: 'Bleu : en cours · Vert : terminé · Gris : non démarré · Rouge : en retard ou bloqué · Ambre : jalon · Aujourd’hui est surligné', locale: 'fr-FR' },
};

/* ---------- state ---------- */
let S = null, prevStart = null;
const codes = s => String(s || '').split(/[,;\s]+/).map(x => x.trim().toUpperCase()).filter(Boolean);
const newTask = (o = {}) => ({ id: uid(), name: '', status: 'ns', r: [], a: '', c: [], i: [], start: '', end: '', note: '', milestone: false, ...o });
function fromTemplate(tp, start) {
  const s0 = dn(start);
  return {
    v: 1, project: { client: '', name: '', pm: '', start, lang: 'en', scale: 'week' },
    roles: window.PLANNER_ROLES.map(r => ({ id: uid(), name: '', ...r })),
    phases: tp.phases.map(p => ({ id: uid(), name: p.name, tasks: p.tasks.map(x => newTask({
      name: x.name, r: codes(x.r), a: codes(x.a)[0] || '', c: codes(x.c), i: codes(x.i), milestone: !!x.milestone,
      start: ds(s0 + x.d), end: ds(s0 + x.d + (x.milestone ? 0 : x.n - 1)) })) })),
  };
}

/* ---------- rendering ---------- */
function seg(id, val, on) {
  document.querySelectorAll('#' + id + ' button').forEach(b => {
    b.setAttribute('aria-pressed', b.dataset.v === val);
    b.onclick = () => { on(b.dataset.v); seg(id, b.dataset.v, on); refresh(); };
  });
}
function renderProject() {
  const p = S.project;
  [['pClient', 'client'], ['pName', 'name'], ['pPm', 'pm'], ['pStart', 'start']].forEach(([id, k]) => {
    const i = $('#' + id); i.value = p[k] || ''; i.dataset.k = 'p:' + k;
    i.oninput = () => { p[k] = i.value.trim(); if (k === 'start') offerShift(); refresh(); };
  });
  prevStart = p.start;
  seg('pLang', p.lang, v => p.lang = v);
  seg('pScale', p.scale, v => p.scale = v);
}
function offerShift() {
  const a = dn(prevStart), b = dn(S.project.start), has = allTasks().some(t => t.start);
  const box = $('#shift');
  if (a == null || b == null || a === b || !has) { box.classList.remove('on'); return; }
  const d = b - a;
  $('#shiftTxt').textContent = 'The start moved by ' + Math.abs(d) + ' day' + (Math.abs(d) > 1 ? 's' : '') + (d > 0 ? ' later' : ' earlier') + '. Move every task with it?';
  box.classList.add('on');
  $('#shiftGo').onclick = () => { allTasks().forEach(t => { if (t.start) t.start = ds(dn(t.start) + d); if (t.end) t.end = ds(dn(t.end) + d); });
    prevStart = S.project.start; box.classList.remove('on'); renderPhases(); refresh(); };
  $('#shiftNo').onclick = () => { prevStart = S.project.start; box.classList.remove('on'); };
}
function renderRoles() {
  const tb = $('#roles'); tb.innerHTML = '';
  S.roles.forEach((r, i) => {
    const tr = el('tr');
    const inp = (k, ph, w) => { const td = el('td'), x = el('input'); x.value = r[k] || ''; x.placeholder = ph; x.dataset.k = 'r:' + r.id + ':' + k; if (w) x.style.minWidth = w;
      x.oninput = () => { r[k] = k === 'code' ? x.value.trim().toUpperCase() : x.value; if (k === 'code') renderPhases(); refresh(); }; td.appendChild(x); tr.appendChild(td); };
    inp('code', 'EPM'); inp('title', 'Equadis project manager', '240px'); inp('name', 'Person', '160px');
    const tdS = el('td'), sel = el('select'); ['Client', 'Equadis', 'Partner'].forEach(v => { const o = el('option', null, v); o.value = v; sel.appendChild(o); });
    sel.value = r.side || 'Equadis'; sel.onchange = () => { r.side = sel.value; refresh(); }; tdS.appendChild(sel); tr.appendChild(tdS);
    const tdX = el('td'), x = el('button', 'icon del', '✕'); x.title = 'Remove this role'; x.setAttribute('aria-label', 'Remove role ' + (r.code || ''));
    x.onclick = () => { S.roles.splice(i, 1); renderRoles(); renderPhases(); refresh(); }; tdX.appendChild(x); tr.appendChild(tdX);
    tb.appendChild(tr);
  });
}
const roleCodes = () => S.roles.map(r => r.code).filter(Boolean);
function pickLabel(btn, v, multi) {
  btn.innerHTML = ''; const arr = multi ? v : (v ? [v] : []);
  btn.appendChild(arr.length ? document.createTextNode(arr.join(', ')) : el('span', 'ph', multi ? 'none' : 'choose'));
}
function picker(task, key, multi) {
  const b = el('button', 'pick'); b.type = 'button'; b.dataset.k = 't:' + task.id + ':' + key;
  pickLabel(b, task[key], multi);
  b.onclick = e => { e.stopPropagation(); openMenu(b, task, key, multi); };
  return b;
}
function openMenu(btn, task, key, multi) {
  const m = $('#menu'); m.innerHTML = '';
  S.roles.filter(r => r.code).forEach(r => {
    const l = el('label'), c = el('input'); c.type = multi ? 'checkbox' : 'radio'; c.name = 'pickone';
    c.checked = multi ? task[key].includes(r.code) : task[key] === r.code;
    c.onchange = () => {
      if (multi) task[key] = S.roles.map(x => x.code).filter(cd => cd && (cd === r.code ? c.checked : task[key].includes(cd)));
      else { task[key] = r.code; m.hidden = true; }
      pickLabel(btn, task[key], multi); btn.classList.remove('miss'); refresh();
    };
    l.appendChild(c); l.appendChild(el('code', null, r.code)); l.appendChild(el('span', 't', r.title + (r.name ? ' · ' + r.name : '')));
    m.appendChild(l);
  });
  if (!multi && task[key]) { const l = el('label'), c = el('input'); c.type = 'radio'; c.name = 'pickone';
    c.onchange = () => { task[key] = ''; m.hidden = true; pickLabel(btn, '', false); refresh(); };
    l.appendChild(c); l.appendChild(el('span', 't', 'Nobody')); m.appendChild(l); }
  if (!m.children.length) m.appendChild(el('p', 'note', 'Add roles in step 2 first.'));
  const r = btn.getBoundingClientRect(); m.hidden = false;
  m.style.left = Math.min(r.left, innerWidth - m.offsetWidth - 8) + 'px';
  m.style.top = (r.bottom + m.offsetHeight + 8 > innerHeight ? Math.max(8, r.top - m.offsetHeight - 4) : r.bottom + 4) + 'px';
  const f = m.querySelector('input'); if (f) f.focus();
}
document.addEventListener('click', e => { const m = $('#menu'); if (!m.hidden && !m.contains(e.target)) m.hidden = true; });
document.addEventListener('keydown', e => { if (e.key === 'Escape') $('#menu').hidden = true; });
window.addEventListener('scroll', () => { $('#menu').hidden = true; }, true);

function renderPhases() {
  const box = $('#phases'); box.innerHTML = '';
  S.phases.forEach((p, pi) => {
    const ph = el('div', 'phase'); ph.dataset.id = p.id;
    const head = el('div', 'phead');
    const nm = el('input'); nm.value = p.name; nm.placeholder = 'Phase name'; nm.dataset.k = 'ph:' + p.id; nm.setAttribute('aria-label', 'Phase name');
    nm.oninput = () => { p.name = nm.value; refresh(); };
    const info = el('span', 'note'); info.dataset.info = p.id;
    head.append(nm, info,
      iconBtn('↑', 'Move the phase up', () => move(S.phases, pi, -1)), iconBtn('↓', 'Move the phase down', () => move(S.phases, pi, 1)),
      iconBtn('✕', 'Remove the phase and its tasks', () => { if (!p.tasks.length || confirm('Remove "' + (p.name || 'this phase') + '" and its ' + p.tasks.length + ' task(s)?')) { S.phases.splice(pi, 1); renderPhases(); refresh(); } }, 'del'));
    ph.appendChild(head);
    if (p.tasks.length) {
      const wrap = el('div', 'scroll'), tb = el('table', 'tasks');
      const thr = el('tr'); ['Task', 'Status', 'R', 'A', 'C', 'I', 'Start', 'End', 'Days', '◆', 'Comment', ''].forEach(h => thr.appendChild(el('th', null, h)));
      const th = el('thead'); th.appendChild(thr); tb.appendChild(th);
      const body = el('tbody');
      p.tasks.forEach((t, ti) => body.appendChild(taskRow(p, t, ti)));
      tb.appendChild(body); wrap.appendChild(tb); ph.appendChild(wrap);
    }
    const add = el('button', 'btn ghost sm add', '+ Add a task');
    add.onclick = () => { const last = p.tasks[p.tasks.length - 1]; const s = last && last.end ? ds(dn(last.end) + 1) : S.project.start;
      p.tasks.push(newTask({ start: s, end: s })); renderPhases(); refresh(); focusKey('t:' + p.tasks[p.tasks.length - 1].id + ':name'); };
    ph.appendChild(add); box.appendChild(ph);
  });
}
function iconBtn(txt, title, fn, cls) { const b = el('button', 'icon' + (cls ? ' ' + cls : ''), txt); b.type = 'button'; b.title = title; b.setAttribute('aria-label', title); b.onclick = fn; return b; }
function move(arr, i, d) { const j = i + d; if (j < 0 || j >= arr.length) return; [arr[i], arr[j]] = [arr[j], arr[i]]; renderPhases(); refresh(); }
function taskRow(p, t, ti) {
  const tr = el('tr'), td = c => { const x = el('td'); x.appendChild(c); tr.appendChild(x); return x; };
  const name = el('input'); name.value = t.name; name.placeholder = 'What has to be done'; name.dataset.k = 't:' + t.id + ':name';
  name.oninput = () => { t.name = name.value; refresh(); }; td(name).className = 'name';
  const st = el('select'); ST.forEach(k => { const o = el('option', null, L.en.st[k]); o.value = k; st.appendChild(o); });
  st.value = t.status; st.onchange = () => { t.status = st.value; refresh(); }; td(st);
  td(picker(t, 'r', true)); td(picker(t, 'a', false)); td(picker(t, 'c', true)); td(picker(t, 'i', true));
  const s = el('input'), e = el('input'), n = el('input'); s.type = e.type = 'date'; n.type = 'number'; n.min = 1;
  s.dataset.k = 't:' + t.id + ':start'; e.dataset.k = 't:' + t.id + ':end';
  const days = () => { const a = dn(t.start), b = dn(t.end); n.value = a != null && b != null && b >= a ? b - a + 1 : ''; };
  s.value = t.start; e.value = t.end; days(); e.disabled = t.milestone; n.disabled = t.milestone;
  s.oninput = () => { const len = dn(t.end) != null && dn(t.start) != null ? dn(t.end) - dn(t.start) : 0; t.start = s.value;
    if (t.milestone) t.end = t.start; else if (dn(t.start) != null) t.end = ds(dn(t.start) + Math.max(0, len)); e.value = t.end; days(); refresh(); };
  e.oninput = () => { t.end = e.value; days(); refresh(); };
  n.oninput = () => { const k = parseInt(n.value, 10); if (k >= 1 && dn(t.start) != null) { t.end = ds(dn(t.start) + k - 1); e.value = t.end; refresh(); } };
  td(s); td(e); td(n).className = 'num';
  const m = el('input'); m.type = 'checkbox'; m.className = 'ms'; m.checked = t.milestone; m.title = 'Milestone'; m.setAttribute('aria-label', 'Milestone');
  m.onchange = () => { t.milestone = m.checked; if (m.checked) { t.end = t.start; e.value = t.end; } e.disabled = n.disabled = m.checked; days(); refresh(); }; td(m);
  const note = el('input'); note.value = t.note; note.placeholder = 'Optional'; note.oninput = () => { t.note = note.value; }; td(note).style.minWidth = '160px';
  const a = el('td', 'acts');
  a.append(iconBtn('↑', 'Move up', () => move(p.tasks, ti, -1)), iconBtn('↓', 'Move down', () => move(p.tasks, ti, 1)),
    iconBtn('⧉', 'Duplicate', () => { p.tasks.splice(ti + 1, 0, newTask({ ...JSON.parse(JSON.stringify(t)), id: uid() })); renderPhases(); refresh(); }),
    iconBtn('✕', 'Remove', () => { p.tasks.splice(ti, 1); renderPhases(); refresh(); }, 'del'));
  tr.appendChild(a);
  return tr;
}
function focusKey(k) { const x = document.querySelector('[data-k="' + k + '"]'); if (x) { x.scrollIntoView({ block: 'center', behavior: 'smooth' }); setTimeout(() => x.focus(), 250); } }
const allTasks = () => S.phases.flatMap(p => p.tasks);

/* ---------- checks: nothing forgotten ---------- */
function checks() {
  const out = [], err = (txt, k) => out.push({ lvl: 'err', txt, k }), wrn = (txt, k) => out.push({ lvl: 'wrn', txt, k });
  const p = S.project;
  if (!p.client) err('Client name', 'p:client');
  if (!p.name) err('Project name', 'p:name');
  if (!p.pm) err('Project manager', 'p:pm');
  if (dn(p.start) == null) err('Project start date', 'p:start');
  const seen = {};
  S.roles.forEach(r => { if (!r.code) err('A role has no code', 'r:' + r.id + ':code'); else if (seen[r.code]) err('Role code ' + r.code + ' is used twice', 'r:' + r.id + ':code'); seen[r.code] = 1; });
  const known = new Set(roleCodes()), used = new Set();
  if (!allTasks().length) err('The plan has no task yet', null);
  S.phases.forEach(ph => {
    const pn = ph.name || 'Unnamed phase';
    if (!ph.name) err('A phase has no name', 'ph:' + ph.id);
    if (!ph.tasks.length) wrn(pn + ' has no task: it will be left out', 'ph:' + ph.id);
    ph.tasks.forEach((t, i) => {
      const tn = (t.name || 'Task ' + (i + 1)) + ' (' + pn + ')';
      if (!t.name) err('Task ' + (i + 1) + ' of ' + pn + ' has no name', 't:' + t.id + ':name');
      if (!t.r.length) err(tn + ': who does it (R)?', 't:' + t.id + ':r');
      if (!t.a) err(tn + ': who owns it (A)?', 't:' + t.id + ':a');
      if (dn(t.start) == null) err(tn + ': start date', 't:' + t.id + ':start');
      if (!t.milestone && dn(t.end) == null) err(tn + ': end date', 't:' + t.id + ':end');
      if (dn(t.start) != null && dn(t.end) != null && dn(t.end) < dn(t.start)) err(tn + ': ends before it starts', 't:' + t.id + ':end');
      if (dn(t.start) != null && dn(p.start) != null && dn(t.start) < dn(p.start)) wrn(tn + ' starts before the project', 't:' + t.id + ':start');
      [...t.r, t.a, ...t.c, ...t.i].filter(Boolean).forEach(c => { used.add(c); if (!known.has(c)) err(tn + ': role ' + c + ' is not in the roles list', 't:' + t.id + ':r'); });
    });
  });
  S.roles.forEach(r => { if (r.code && used.has(r.code) && !r.name.trim()) wrn(r.code + ' (' + (r.title || 'role') + ') has no person\'s name', 'r:' + r.id + ':name'); });
  return out;
}
function renderChecks() {
  const list = checks(), box = $('#checks'); box.innerHTML = '';
  document.querySelectorAll('.miss').forEach(x => x.classList.remove('miss'));
  const errs = list.filter(c => c.lvl === 'err');
  if (!list.length) { const d = el('div', 'allgood', '✓ Everything is filled in. Ready to export.'); box.appendChild(d); }
  else {
    const p = el('p', 'note', errs.length ? errs.length + ' thing' + (errs.length > 1 ? 's' : '') + ' to fill in before export' + (list.length > errs.length ? ', and ' + (list.length - errs.length) + ' to look at' : '') + '. Click one to go there.'
                                         : list.length + ' thing' + (list.length > 1 ? 's' : '') + ' to look at. You can still export.');
    p.style.margin = '0 0 6px'; box.appendChild(p);
    const ul = el('ul', 'checks');
    list.slice(0, 40).forEach(c => { const li = el('li', c.lvl), tag = el('span', 'tag', c.lvl === 'err' ? 'Missing' : 'Check'), b = el('button', null, c.txt);
      b.onclick = () => c.k && focusKey(c.k); li.append(tag, b); ul.appendChild(li);
      if (c.lvl === 'err' && c.k) { const x = document.querySelector('[data-k="' + c.k + '"]'); if (x) x.classList.add('miss'); } });
    if (list.length > 40) ul.appendChild(el('li', 'note', '… and ' + (list.length - 40) + ' more'));
    box.appendChild(ul);
  }
  const go = $('#xGo'); go.textContent = errs.length ? 'Fill in ' + errs.length + ' thing' + (errs.length > 1 ? 's' : '') + ' first' : 'Export Excel';
  go.dataset.blocked = errs.length ? '1' : '';
}

/* ---------- preview ---------- */
const barCls = (t, today) => t.milestone ? 'ms' : t.status === 'co' ? 'co' : (t.status === 'bl' || (dn(t.end) != null && dn(t.end) < today)) ? 'late' : t.status === 'ns' ? 'ns' : 'ot';
function renderPreview() {
  const box = $('#preview'); box.innerHTML = '';
  const ts = allTasks().filter(t => dn(t.start) != null && dn(t.end || t.start) != null);
  if (!ts.length) { box.appendChild(el('p', 'note', 'Dates appear here as you fill them in.')); return; }
  const a = Math.min(...ts.map(t => dn(t.start))), b = Math.max(...ts.map(t => dn(t.end || t.start))) + 1, span = Math.max(1, b - a);
  const pc = n => ((n - a) / span * 100) + '%', today = todayN(), loc = L[S.project.lang].locale;
  const wrap = el('div', 'gwrap');
  const head = el('div', 'grow'); head.appendChild(el('div')); const mo = el('div', 'months');
  for (let d = a; d < b; d++) { const dt = new Date(d * 864e5); if (d === a || dt.getUTCDate() === 1) {
    const s = el('span', null, dt.toLocaleDateString(loc, { month: 'short', year: '2-digit', timeZone: 'UTC' })); s.style.left = pc(d); mo.appendChild(s); } }
  head.appendChild(mo); wrap.appendChild(head);
  S.phases.forEach(p => {
    const pt = p.tasks.filter(t => dn(t.start) != null); if (!pt.length) return;
    const r = el('div', 'grow ph'); r.appendChild(el('div', 'lbl', p.name || 'Phase'));
    const tr = el('div', 'track'), pa = Math.min(...pt.map(t => dn(t.start))), pb = Math.max(...pt.map(t => dn(t.end || t.start))) + 1;
    const bar = el('div', 'bar'); bar.style.cssText = 'left:' + pc(pa) + ';width:' + ((pb - pa) / span * 100) + '%;background:var(--bar-ph);height:6px;top:4px';
    tr.appendChild(bar); r.appendChild(tr); wrap.appendChild(r);
    pt.forEach(t => {
      const row = el('div', 'grow'); const l = el('div', 'lbl', (t.milestone ? '◆ ' : '') + (t.name || '…')); l.title = t.name; l.style.paddingLeft = '14px'; row.appendChild(l);
      const k = el('div', 'track'), c = barCls(t, today);
      if (t.milestone) { const d = el('div', 'dia'); d.style.left = 'calc(' + pc(dn(t.start) + 0.5) + ')'; k.appendChild(d); }
      else { const br = el('div', 'bar'); br.style.cssText = 'left:' + pc(dn(t.start)) + ';width:' + ((dn(t.end) - dn(t.start) + 1) / span * 100) + '%;background:var(--bar-' + c + ')'; k.appendChild(br); }
      row.appendChild(k); wrap.appendChild(row);
    });
  });
  if (today >= a && today < b) { const tl = el('div', 'today'); tl.style.left = 'calc(240px + (100% - 240px) * ' + ((today - a) / span) + ')'; wrap.appendChild(tl); }
  box.appendChild(wrap);
}

let tick = null;
function refresh() {
  clearTimeout(tick);
  tick = setTimeout(() => {
    renderChecks(); renderPreview();
    const n = allTasks().length; $('#planSum').textContent = S.phases.length + ' phase' + (S.phases.length > 1 ? 's' : '') + ' · ' + n + ' task' + (n !== 1 ? 's' : '');
    S.phases.forEach(p => { const i = document.querySelector('[data-info="' + p.id + '"]'); if (!i) return;
      const d = p.tasks.filter(t => dn(t.start) != null); i.textContent = p.tasks.length + ' task' + (p.tasks.length !== 1 ? 's' : '') +
        (d.length ? ' · ' + fmt(ds(Math.min(...d.map(t => dn(t.start))))) + ' → ' + fmt(ds(Math.max(...d.map(t => dn(t.end || t.start))))) : ''); });
  }, 120);
}
function renderAll() { renderProject(); renderRoles(); renderPhases(); refresh(); $('#shift').classList.remove('on'); }

/* ---------- Excel ---------- */
const NAVY = 'FF112032', PH = 'FFE3E9EF', WHITE = 'FFFFFFFF', GRID = 'FFC7D0D8';
const FILL = { 1: 'FF4472C4', 2: 'FF2E9E6B', 3: 'FF112032', 4: 'FFA9B4BF', 5: 'FFC0504D', 6: 'FFD9A945' };
const STFILL = { co: ['FFDFF6EA', 'FF0F7A55'], ot: ['FFDCE6F5', 'FF2F5597'], ar: ['FFF5EBD8', 'FF8A5E10'], bl: ['FFF4E1DD', 'FF9E3A2C'], ns: ['FFEDF0F3', 'FF5A6B7C'] };
const colL = n => { let s = ''; for (n++; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + (n - 1) % 26) + s; return s; };
const xd = s => { const n = dn(s); return n == null ? null : new Date(n * 864e5); };
const solid = argb => ({ type: 'pattern', pattern: 'solid', fgColor: { argb } });
const thin = { style: 'thin', color: { argb: GRID } }, box = { top: thin, left: thin, bottom: thin, right: thin };
const safeName = s => String(s || '').replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim();

function phasesForExport() { return S.phases.filter(p => p.tasks.length); }

function sheetRaci(wb, W) {
  const ws = wb.addWorksheet(W.raci, { views: [{ state: 'frozen', ySplit: 4, showGridLines: false }] });
  ws.columns = [{ width: 52 }, { width: 15 }, { width: 18 }, { width: 14 }, { width: 20 }, { width: 24 }, { width: 40 }];
  ws.mergeCells('A1:G1'); const t = ws.getCell('A1'); t.value = W.raci + ' - ' + S.project.client + ' / ' + S.project.name;
  t.font = { bold: true, size: 16, color: { argb: NAVY } };
  ws.getCell('A2').value = W.pm + ': ' + S.project.pm + ' · ' + W.updated + ' ' + fmt(ds(todayN()));
  ws.getCell('A2').font = { color: { argb: 'FF5A6B7C' } };
  const hr = ws.getRow(4); hr.values = [W.task, W.status, W.R, W.A, W.C, W.I, W.comment];
  hr.eachCell(c => { c.fill = solid(NAVY); c.font = { bold: true, color: { argb: WHITE } }; c.alignment = { vertical: 'middle', wrapText: true }; c.border = box; }); hr.height = 22;
  let r = 5; const rows = {}, list = '"' + ST.map(k => W.st[k]).join(',') + '"';
  phasesForExport().forEach(p => {
    const first = r + 1, last = r + p.tasks.length, n = p.tasks.length, done = p.tasks.filter(x => x.status === 'co').length;
    const row = ws.getRow(r); row.getCell(1).value = p.name;
    row.getCell(2).value = { formula: 'COUNTIF(B' + first + ':B' + last + ',"' + W.st.co + '")&" / ' + n + ' ' + W.done + '"', result: done + ' / ' + n + ' ' + W.done };
    for (let c = 1; c <= 7; c++) { const x = row.getCell(c); x.fill = solid(PH); x.font = { bold: true, color: { argb: NAVY } }; x.border = box; }
    rows[p.id] = r; r++;
    p.tasks.forEach(tk => {
      const row = ws.getRow(r);
      row.values = [tk.name, W.st[tk.status], tk.r.join(', '), tk.a, tk.c.join(', '), tk.i.join(', '), tk.note];
      row.getCell(1).alignment = { indent: 1, wrapText: true, vertical: 'middle' };
      for (let c = 1; c <= 7; c++) { row.getCell(c).border = box; if (c > 1) row.getCell(c).alignment = { vertical: 'middle', wrapText: c === 7 }; }
      row.getCell(2).dataValidation = { type: 'list', allowBlank: true, formulae: [list] };
      rows[tk.id] = r; r++;
    });
  });
  const end = r - 1;
  ws.addConditionalFormatting({ ref: 'B5:B' + end, rules: ST.map((k, i) => ({ type: 'cellIs', operator: 'equal', priority: i + 1, formulae: ['"' + W.st[k] + '"'],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: STFILL[k][0] } }, font: { color: { argb: STFILL[k][1] }, bold: true } } })) });
  r += 1;
  const used = new Set(allTasks().flatMap(x => [...x.r, x.a, ...x.c, ...x.i]).filter(Boolean));
  const roles = S.roles.filter(x => x.code && (used.has(x.code) || x.name.trim()));
  const rh = ws.getRow(r); rh.values = [W.roles + ' - ' + W.role, W.code, W.name, W.side];
  [1, 2, 3, 4].forEach(c => { const x = rh.getCell(c); x.fill = solid(NAVY); x.font = { bold: true, color: { argb: WHITE } }; x.border = box; }); r++;
  roles.forEach(x => { const row = ws.getRow(r); row.values = [x.title, x.code, x.name, x.side]; [1, 2, 3, 4].forEach(c => row.getCell(c).border = box); r++; });
  r++; W.legend.forEach(l => { ws.getCell('A' + r).value = l; ws.getCell('A' + r).font = { color: { argb: 'FF5A6B7C' }, size: 10 }; r++; });
  ws.pageSetup = { orientation: 'landscape', paperSize: 9, fitToPage: true, fitToWidth: 1, fitToHeight: 0 };
  return rows;
}

function sheetGantt(wb, W, raciRows) {
  const today = todayN(), week = S.project.scale !== 'day';
  const ts = allTasks().filter(t => dn(t.start) != null);
  const a0 = Math.min(...ts.map(t => dn(t.start))), b0 = Math.max(...ts.map(t => dn(t.end || t.start)));
  const step = week ? 7 : 1, first = week ? monday(a0) : a0;
  const ncol = Math.min(week ? 104 : 200, Math.floor((b0 - first) / step) + (week ? 2 : 3));
  const C0 = 6;                                                        // timeline starts at column G
  const ws = wb.addWorksheet(W.gantt, { views: [{ state: 'frozen', xSplit: C0, ySplit: 5, showGridLines: false }] });
  ws.columns = [{ width: 46 }, { width: 14 }, { width: 14 }, { width: 11 }, { width: 11 }, { width: 6 }].concat(Array.from({ length: ncol }, () => ({ width: week ? 4.2 : 3.2 })));
  const lastL = colL(C0 + ncol - 1);
  ws.mergeCells('A1:' + lastL + '1'); const t = ws.getCell('A1'); t.value = W.gantt + ' - ' + S.project.client + ' / ' + S.project.name;
  t.font = { bold: true, size: 16, color: { argb: NAVY } };
  ws.getCell('A2').value = W.pm + ': ' + S.project.pm + ' · ' + W.updated + ' ' + fmt(ds(today)); ws.getCell('A2').font = { color: { argb: 'FF5A6B7C' } };
  ws.getCell('A3').value = W.glegend; ws.getCell('A3').font = { color: { argb: 'FF5A6B7C' }, size: 10 };
  const loc = W.locale, hr = ws.getRow(5);
  [W.task, W.status, W.resp, W.start, W.end, W.days].forEach((v, i) => { const c = hr.getCell(i + 1); c.value = v; });
  let mStart = null, mKey = null;
  for (let k = 0; k <= ncol; k++) {
    const d = first + k * step, key = k < ncol ? new Date(d * 864e5).toISOString().slice(0, 7) : null;
    if (key !== mKey) {
      if (mKey != null) { const a = colL(C0 + mStart), b = colL(C0 + k - 1); if (a !== b) ws.mergeCells(a + '4:' + b + '4');
        const c = ws.getCell(a + '4'); c.value = new Date(dn(mKey + '-01') * 864e5).toLocaleDateString(loc, { month: 'short', year: '2-digit', timeZone: 'UTC' });
        c.font = { bold: true, color: { argb: WHITE } }; c.fill = solid(NAVY); c.alignment = { horizontal: 'center' }; }
      mStart = k; mKey = key;
    }
    if (k < ncol) { const c = hr.getCell(C0 + k + 1); c.value = new Date(d * 864e5); c.numFmt = week ? 'dd/mm' : 'dd'; c.alignment = { horizontal: 'center', textRotation: week ? 90 : 0 }; }
  }
  hr.height = week ? 40 : 20;
  hr.eachCell(c => { c.font = { bold: true, color: { argb: WHITE } }; c.fill = solid(NAVY); c.border = box; if (!c.alignment) c.alignment = { vertical: 'middle' }; });
  const st = W.st, cell = (k, r) => colL(C0 + k) + r, H = k => colL(C0 + k) + '$5';
  const inner = r => 'IF($B' + r + '="' + st.co + '",2,IF(OR($B' + r + '="' + st.bl + '",$E' + r + '<TODAY()),5,IF($B' + r + '="' + st.ns + '",4,1)))';
  const inRange = (r, k) => week ? 'AND($D' + r + '<=' + H(k) + '+6,$E' + r + '>=' + H(k) + ')' : 'AND($D' + r + '<=' + H(k) + ',$E' + r + '>=' + H(k) + ')';
  const hit = (a, b, d) => week ? (a <= d + 6 && b >= d) : (a <= d && b >= d);
  const code = tk => tk.milestone ? 6 : tk.status === 'co' ? 2 : (tk.status === 'bl' || dn(tk.end || tk.start) < today) ? 5 : tk.status === 'ns' ? 4 : 1;
  let r = 6;
  const ref = (key, col, val) => raciRows && raciRows[key] ? { formula: W.raci + '!' + col + raciRows[key], result: val } : val;
  phasesForExport().forEach(p => {
    const pr = r, f = r + 1, l = r + p.tasks.length, row = ws.getRow(pr);
    const dts = p.tasks.filter(x => dn(x.start) != null), pa = dts.length ? Math.min(...dts.map(x => dn(x.start))) : null, pb = dts.length ? Math.max(...dts.map(x => dn(x.end || x.start))) : null;
    row.getCell(1).value = ref(p.id, 'A', p.name);
    if (raciRows) { const dn_ = p.tasks.filter(x => x.status === 'co').length; row.getCell(2).value = ref(p.id, 'B', dn_ + ' / ' + p.tasks.length + ' ' + W.done); }
    row.getCell(4).value = { formula: 'IF(COUNT(D' + f + ':D' + l + ')=0,"",MIN(D' + f + ':D' + l + '))', result: pa != null ? new Date(pa * 864e5) : '' };
    row.getCell(5).value = { formula: 'IF(COUNT(E' + f + ':E' + l + ')=0,"",MAX(E' + f + ':E' + l + '))', result: pb != null ? new Date(pb * 864e5) : '' };
    row.getCell(6).value = { formula: 'IF(OR(D' + pr + '="",E' + pr + '=""),"",E' + pr + '-D' + pr + '+1)', result: pa != null ? pb - pa + 1 : '' };
    for (let k = 0; k < ncol; k++) row.getCell(C0 + k + 1).value = { formula: 'IF(OR($D' + pr + '="",$E' + pr + '=""),"",IF(' + inRange(pr, k) + ',3,""))', result: pa != null && hit(pa, pb, first + k * step) ? 3 : '' };
    for (let c = 1; c <= 6; c++) { const x = row.getCell(c); x.fill = solid(PH); x.font = { bold: true, color: { argb: NAVY } }; x.border = box; }
    r++;
    p.tasks.forEach(tk => {
      const row = ws.getRow(r), a = dn(tk.start), b = dn(tk.end || tk.start);
      row.getCell(1).value = ref(tk.id, 'A', (tk.milestone && !raciRows ? '◆ ' : '') + tk.name);
      row.getCell(2).value = ref(tk.id, 'B', st[tk.status]);
      row.getCell(3).value = ref(tk.id, 'C', tk.r.join(', '));
      row.getCell(4).value = xd(tk.start); row.getCell(5).value = xd(tk.end || tk.start);
      row.getCell(6).value = { formula: 'IF(OR(D' + r + '="",E' + r + '=""),"",E' + r + '-D' + r + '+1)', result: a != null ? b - a + 1 : '' };
      const val = tk.milestone ? '6' : inner(r);
      for (let k = 0; k < ncol; k++) row.getCell(C0 + k + 1).value = { formula: 'IF(OR($D' + r + '="",$E' + r + '=""),"",IF(' + inRange(r, k) + ',' + val + ',""))', result: a != null && hit(a, b, first + k * step) ? code(tk) : '' };
      row.getCell(1).alignment = { indent: 1, vertical: 'middle' };
      if (!raciRows) row.getCell(2).dataValidation = { type: 'list', allowBlank: true, formulae: ['"' + ST.map(k => st[k]).join(',') + '"'] };
      for (let c = 1; c <= 6; c++) row.getCell(c).border = box;
      r++;
    });
  });
  const end = r - 1;
  [4, 5].forEach(c => { for (let i = 6; i <= end; i++) ws.getCell(i, c).numFmt = 'dd/mm/yyyy'; });
  for (let i = 6; i <= end; i++) for (let k = 0; k < ncol; k++) { const c = ws.getCell(i, C0 + k + 1); c.border = { left: { style: 'hair', color: { argb: GRID } }, bottom: { style: 'hair', color: { argb: GRID } } }; }
  const tl = colL(C0) + '6:' + lastL + end, H0 = colL(C0);
  const rules = [1, 2, 3, 4, 5, 6].map((v, i) => ({ type: 'cellIs', operator: 'equal', priority: i + 1, formulae: [String(v)],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: FILL[v] } }, font: { color: { argb: FILL[v] } } } }));
  rules.push({ type: 'expression', priority: 7, formulae: [week ? 'AND(' + H0 + '$5<=TODAY(),TODAY()<' + H0 + '$5+7)' : H0 + '$5=TODAY()'],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: 'FFFFF2CC' } } } });
  if (!week) rules.push({ type: 'expression', priority: 8, formulae: ['WEEKDAY(' + H0 + '$5,2)>5'], style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: 'FFF2F2F2' } } } });
  ws.addConditionalFormatting({ ref: tl, rules });
  ws.addConditionalFormatting({ ref: H0 + '5:' + lastL + '5', rules: [{ type: 'expression', priority: 1, formulae: [week ? 'AND(' + H0 + '$5<=TODAY(),TODAY()<' + H0 + '$5+7)' : H0 + '$5=TODAY()'],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: 'FFD9A945' } }, font: { color: { argb: NAVY }, bold: true } } }] });
  ws.addConditionalFormatting({ ref: 'B6:B' + end, rules: ST.map((k, i) => ({ type: 'cellIs', operator: 'equal', priority: i + 1, formulae: ['"' + st[k] + '"'],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: STFILL[k][0] } }, font: { color: { argb: STFILL[k][1] }, bold: true } } })) });
  ws.pageSetup = { orientation: 'landscape', paperSize: 9, fitToPage: true, fitToWidth: 1, fitToHeight: 0 };
}

async function buildWorkbook(opts) {
  const W = L[S.project.lang];
  const wb = new ExcelJS.Workbook(); wb.creator = 'TPM Desk - Project planner'; wb.created = new Date();
  wb.calcProperties.fullCalcOnLoad = true;
  const raciRows = opts.raci ? sheetRaci(wb, W) : null;
  if (opts.gantt) sheetGantt(wb, W, raciRows);
  const data = wb.addWorksheet('_plan', { state: 'veryHidden' }), js = JSON.stringify(S);
  for (let i = 0, r = 1; i < js.length; i += 30000, r++) data.getCell('A' + r).value = js.slice(i, i + 30000);
  return wb.xlsx.writeBuffer();
}

async function saveFile(buf, name) {
  const type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', file = new File([buf], name, { type });
  try { const host = window.parent !== window && window.parent.claude;           // inside the desk on claude.ai
    if (host && typeof host.use === 'function') { const dl = await host.use('downloads').catch(() => null); if (dl) { await dl.save({ filename: name, data: file }); return; } } } catch (e) { /* not reachable: plain download */ }
  const a = document.createElement('a'); a.href = URL.createObjectURL(file); a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

$('#xGo').onclick = async () => {
  const out = $('#xOut'); out.className = 'status';
  if ($('#xGo').dataset.blocked) { $('#cCheck').scrollIntoView({ behavior: 'smooth' }); const f = checks().find(c => c.lvl === 'err' && c.k); if (f) focusKey(f.k); return; }
  const opts = { raci: $('#xRaci').checked, gantt: $('#xGantt').checked };
  if (!opts.raci && !opts.gantt) { out.className = 'status ko'; out.textContent = 'Tick RACI, Gantt or both.'; return; }
  try {
    const kind = opts.raci && opts.gantt ? 'Planning RACI' : opts.raci ? 'RACI' : 'Gantt';
    const name = safeName(S.project.client + ' - ' + S.project.name + ' - ' + kind + ' ' + ds(todayN()).split('-').reverse().join('')) + '.xlsx';
    await saveFile(await buildWorkbook(opts), name);
    out.className = 'status ok'; out.textContent = 'Saved ' + name;
  } catch (e) { out.className = 'status ko'; out.textContent = 'Export failed: ' + (e && e.message || e); }
};
$('#xRaci').onchange = $('#xGantt').onchange = () => { $('#xOut').textContent = ''; };

/* ---------- open a saved plan (the planner's Excel, or a .json) ---------- */
$('#openBtn').onclick = () => $('#openFile').click();
$('#openFile').onchange = async e => {
  const f = e.target.files[0]; e.target.value = ''; if (!f) return;
  const note = $('#openNote');
  try {
    let js;
    if (/\.json$/i.test(f.name)) js = await f.text();
    else {
      const wb = new ExcelJS.Workbook(); await wb.xlsx.load(await f.arrayBuffer());
      const ws = wb.getWorksheet('_plan'); if (!ws) throw new Error('this Excel was not made by the planner');
      js = ''; ws.eachRow(r => { js += String(r.getCell(1).value || ''); });
    }
    const o = JSON.parse(js); if (!o || o.v !== 1 || !Array.isArray(o.phases)) throw new Error('unknown plan format');
    S = o; renderAll(); note.textContent = 'Opened ' + f.name;
  } catch (err) { note.textContent = 'Could not open ' + f.name + ': ' + (err.message || err); }
};

/* ---------- templates ---------- */
const sel = $('#tpl');
window.PLANNER_TEMPLATES.forEach(tp => { const o = el('option', null, tp.name + ' - ' + tp.note); o.value = tp.id; sel.appendChild(o); });
sel.value = 'interface';
$('#tplGo').onclick = () => {
  const tp = window.PLANNER_TEMPLATES.find(x => x.id === sel.value);
  const filled = allTasks().some(t => t.name);
  if (filled && !confirm('Replace the current plan with the "' + tp.name + '" template? Project details are kept.')) return;
  const keep = S && S.project;
  S = fromTemplate(tp, (keep && keep.start) || ds(monday(todayN())));
  if (keep) Object.assign(S.project, keep);
  renderAll();
};
$('#phaseAdd').onclick = () => { S.phases.push({ id: uid(), name: '', tasks: [] }); renderPhases(); refresh(); focusKey('ph:' + S.phases[S.phases.length - 1].id); };
$('#roleAdd').onclick = () => { S.roles.push({ id: uid(), code: '', title: '', name: '', side: 'Equadis' }); renderRoles(); refresh(); focusKey('r:' + S.roles[S.roles.length - 1].id + ':code'); };

/* ---------- inside the desk: follow its light / dark theme ---------- */
try {
  const pd = window.parent !== window && window.parent.document.documentElement;
  if (pd) { const sync = () => { const t = pd.getAttribute('data-theme'); if (t) document.documentElement.setAttribute('data-theme', t); else document.documentElement.removeAttribute('data-theme'); };
    sync(); new MutationObserver(sync).observe(pd, { attributes: true, attributeFilter: ['data-theme'] }); document.querySelector('main').style.paddingTop = '8px'; }
} catch (e) { /* another origin: keep the system theme */ }

S = fromTemplate(window.PLANNER_TEMPLATES.find(x => x.id === 'interface'), ds(monday(todayN())));
renderAll();
})();
