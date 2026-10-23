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
const ST = ['ns', 'ot', 'ar', 'wc', 'bl', 'co'];      // wc: waiting on the client, since a date
const L = {
  en: { st: { ns: 'Not Started', ot: 'On Track', ar: 'At Risk', wc: 'Waiting on Client', bl: 'Blocked', co: 'Completed' }, since: 'Waiting on the client since',
        raci: 'RACI', gantt: 'Gantt', task: 'Phase / Task', status: 'Status', R: 'Responsible (R)', A: 'Accountable (A)',
        C: 'Consulted (C)', I: 'Informed (I)', comment: 'Comment', resp: 'Responsible', start: 'Start', end: 'End', days: 'Days',
        pm: 'Project manager', updated: 'updated', done: 'done', roles: 'Roles', code: 'Code', role: 'Role', name: 'Name', side: 'Side',
        legend: ['R - Responsible: does the work', 'A - Accountable: owns the task and approves it (one per task)',
                 'C - Consulted: gives input before', 'I - Informed: kept up to date after'],
        glegend: 'Blue: on track · Green: completed · Grey: not started · Red: late or blocked · Violet: waiting on the client · Amber: milestone · Today is highlighted', locale: 'en-GB',
        tk: 'Task', scope: 'Scope', overview: 'Overview', tracker: 'Tracker', id: 'ID', phase: 'Phase', detail: 'Detail', owner: 'Owner', due: 'Due',
        overdue: 'Overdue', daysLeft: 'Days left', notes: 'Notes', tasks: 'Tasks', pctDone: '% done', daysTo: 'Days to', theEnd: 'the end' },
  fr: { st: { ns: 'Non démarré', ot: 'En cours', ar: 'À risque', wc: 'En attente client', bl: 'Bloqué', co: 'Terminé' }, since: 'En attente du client depuis le',
        raci: 'RACI', gantt: 'Gantt', task: 'Phase / Tâche', status: 'Statut', R: 'Réalise (R)', A: 'Valide (A)',
        C: 'Consulté (C)', I: 'Informé (I)', comment: 'Commentaire', resp: 'Responsable', start: 'Début', end: 'Fin', days: 'Jours',
        pm: 'Chef de projet', updated: 'mis à jour le', done: 'terminées', roles: 'Rôles', code: 'Code', role: 'Rôle', name: 'Nom', side: 'Côté',
        legend: ['R - Réalise : fait le travail', 'A - Valide : porte la tâche et la valide (un seul par tâche)',
                 'C - Consulté : donne son avis avant', 'I - Informé : tenu au courant après'],
        glegend: 'Bleu : en cours · Vert : terminé · Gris : non démarré · Rouge : en retard ou bloqué · Violet : en attente du client · Ambre : jalon · Aujourd’hui est surligné', locale: 'fr-FR',
        tk: 'Tâche', scope: 'Périmètre', overview: 'Vue d’ensemble', tracker: 'Suivi', id: 'ID', phase: 'Phase', detail: 'Détail', owner: 'Responsable', due: 'Échéance',
        overdue: 'En retard', daysLeft: 'Jours restants', notes: 'Notes', tasks: 'Tâches', pctDone: '% terminé', daysTo: 'Jours avant', theEnd: 'la fin' },
};

/* ---------- state ---------- */
let S = null, prevStart = null;
const codes = s => String(s || '').split(/[,;\s]+/).map(x => x.trim().toUpperCase()).filter(Boolean);
const newTask = (o = {}) => ({ id: uid(), name: '', status: 'ns', r: [], a: '', c: [], i: [], start: '', end: '', note: '', milestone: false, ...o });
/* day k of a template: calendar day, or k-th working day (Monday to Friday) for workdays templates */
function addWorkdays(n, k) {
  const wd = x => (new Date(x * 864e5).getUTCDay() + 6) % 7;     // 0 Monday ... 6 Sunday
  while (wd(n) > 4) n++;
  for (let i = 0; i < k; i++) { n++; while (wd(n) > 4) n++; }
  return n;
}
/* Scope sheet: lines of the overview (label, value) and tables pasted from Excel. Templates without one get two lines. */
const SCOPE0 = { fields: [['Objective', 'Objectif', 'What the project delivers'], ['Key dates', 'Dates clés', 'Go-live, milestones']], tables: [] };
function scopeOf(sc, pick) {
  return { fields: sc.fields.map(f => ({ id: uid(), label: pick([f[0], f[1]]), value: '', hint: f[2] || '' })),
           tables: sc.tables.map(x => ({ id: uid(), name: pick(x.name), cols: x.cols.map(pick), rows: [] })) };
}
function fromTemplate(tp, start, lang) {
  const s0 = dn(start), fr = lang === 'fr';
  const pick = v => Array.isArray(v) ? v[fr ? 1 : 0] : v;
  const day = k => tp.workdays ? addWorkdays(s0, k) : s0 + k;
  return {
    v: 1, id: uid() + uid(), project: { client: '', name: '', pm: '', start, lang: fr ? 'fr' : 'en', scale: 'week' },
    sheets: (tp.sheets || ['raci', 'gantt']).slice(), scope: scopeOf(tp.scope || SCOPE0, pick),
    roles: window.PLANNER_ROLES.map(r => ({ id: uid(), name: '', ...r })),
    phases: tp.phases.map(p => ({ id: uid(), name: pick(p.name), tasks: p.tasks.map(x => newTask({
      name: pick(x.name), r: codes(x.r), a: codes(x.a)[0] || '', c: codes(x.c), i: codes(x.i), milestone: !!x.milestone, note: pick(x.note) || '',
      start: ds(day(x.d)), end: ds(day(x.d + (x.milestone ? 0 : x.n - 1))) })) })),
  };
}
/* plans saved before the Scope and Tracker sheets */
function upgrade(o) {
  if (!Array.isArray(o.sheets)) o.sheets = ['raci', 'gantt'];
  if (!o.scope) o.scope = scopeOf(SCOPE0, v => v[o.project && o.project.lang === 'fr' ? 1 : 0]);
  return o;
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
/* tab-separated lines (copied from Excel) -> rows of n cells */
const tsv = (txt, n) => txt.replace(/\r/g, '').split('\n').filter(l => l.trim()).map(l => { const c = l.split('\t').map(x => x.trim()); while (c.length < n) c.push(''); return c.slice(0, n); });
function renderScope() {
  const card = $('#cScope'), on = S.sheets.includes('scope'); card.hidden = !on; if (!on) return;
  const fb = $('#scFields'); fb.innerHTML = '';
  S.scope.fields.forEach((f, i) => {
    const tr = el('tr'), lb = el('input'), va = el('input');
    lb.value = f.label; lb.placeholder = 'Line'; lb.oninput = () => { f.label = lb.value; refresh(); };
    va.value = f.value; va.placeholder = f.hint || 'Value'; va.dataset.k = 'sc:' + f.id; va.oninput = () => { f.value = va.value; refresh(); };
    const a = el('td'); a.appendChild(lb); const b = el('td'); b.appendChild(va); b.style.width = '70%';
    const x = el('td'); x.appendChild(iconBtn('✕', 'Remove this line', () => { S.scope.fields.splice(i, 1); renderScope(); refresh(); }, 'del'));
    tr.append(a, b, x); fb.appendChild(tr);
  });
  const tb = $('#scTables'); tb.innerHTML = '';
  S.scope.tables.forEach(t => {
    const box = el('div', 'phase'), head = el('div', 'phead');
    head.append(el('strong', null, t.name), el('span', 'note', t.rows.length + ' row' + (t.rows.length !== 1 ? 's' : '')));
    head.lastChild.style.marginLeft = 'auto';
    const paste = el('button', 'btn ghost sm', 'Paste from Excel'), area = el('textarea');
    area.hidden = true; area.rows = 3; area.placeholder = 'Copy the rows in Excel (' + t.cols.join(', ') + '), then paste here'; area.style.cssText = 'width:calc(100% - 20px); margin:8px 10px 0';
    paste.onclick = () => { area.hidden = !area.hidden; if (!area.hidden) area.focus(); };
    area.oninput = () => { const rows = tsv(area.value, t.cols.length); area.value = ''; if (!rows.length) return; t.rows.push(...rows); renderScope(); refresh(); };
    head.appendChild(paste); box.appendChild(head); box.appendChild(area);
    if (t.rows.length) {
      const wrap = el('div', 'scroll'), tab = el('table'), thr = el('tr');
      t.cols.concat('').forEach(c => thr.appendChild(el('th', null, c))); const th = el('thead'); th.appendChild(thr); tab.appendChild(th);
      const body = el('tbody');
      t.rows.forEach((row, ri) => { const tr = el('tr');
        row.forEach((v, ci) => { const td = el('td'), x = el('input'); x.value = v; x.setAttribute('aria-label', t.cols[ci]); x.oninput = () => { row[ci] = x.value; }; td.appendChild(x); tr.appendChild(td); });
        const td = el('td'); td.appendChild(iconBtn('✕', 'Remove this row', () => { t.rows.splice(ri, 1); renderScope(); refresh(); }, 'del')); tr.appendChild(td);
        body.appendChild(tr); });
      tab.appendChild(body); wrap.appendChild(tab); wrap.style.padding = '6px 6px 0'; box.appendChild(wrap);
    }
    const add = el('button', 'btn ghost sm add', '+ Add a row');
    add.onclick = () => { t.rows.push(t.cols.map(() => '')); renderScope(); refresh(); };
    box.appendChild(add); tb.appendChild(box);
  });
}
/* step numbers follow the cards on screen */
function numberSteps() { let n = 0; document.querySelectorAll('.card.step').forEach(c => { if (!c.hidden) c.querySelector('h2 > b').textContent = ++n; }); }
function renderSheets() {
  [['xScope', 'scope'], ['xRaci', 'raci'], ['xTracker', 'tracker'], ['xGantt', 'gantt']].forEach(([id, k]) => {
    const c = $('#' + id); c.checked = S.sheets.includes(k);
    c.onchange = () => { S.sheets = ['scope', 'raci', 'tracker', 'gantt'].filter(x => x === k ? c.checked : S.sheets.includes(x));
      $('#xOut').textContent = ''; renderScope(); numberSteps(); refresh(); };
  });
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
  st.value = t.status;
  const since = el('input'); since.type = 'date'; since.title = 'Waiting on the client since'; since.setAttribute('aria-label', 'Waiting on the client since');
  since.className = 'since'; since.value = t.since || ''; since.hidden = t.status !== 'wc'; since.dataset.k = 't:' + t.id + ':since';
  since.oninput = () => { t.since = since.value; refresh(); };
  st.onchange = () => { t.status = st.value;
    if (t.status === 'wc' && !t.since) { t.since = ds(todayN()); since.value = t.since; }   // waiting starts today unless told otherwise
    since.hidden = t.status !== 'wc'; refresh(); };
  const stCell = td(st); stCell.appendChild(since);
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
  if (S.sheets.includes('scope')) S.scope.fields.forEach(f => { if (f.label && !f.value.trim()) wrn('Scope: ' + f.label + ' is empty', 'sc:' + f.id); });
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
      if (t.status === 'wc' && dn(t.since) == null) err(tn + ': waiting on the client since when?', 't:' + t.id + ':since');
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
const barCls = (t, today) => t.milestone ? 'ms' : t.status === 'co' ? 'co' : t.status === 'wc' ? 'wc' : (t.status === 'bl' || (dn(t.end) != null && dn(t.end) < today)) ? 'late' : t.status === 'ns' ? 'ns' : 'ot';
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
function renderAll() { renderProject(); renderSheets(); renderScope(); renderRoles(); renderPhases(); numberSteps(); refresh(); $('#shift').classList.remove('on'); }

/* ---------- Excel ---------- */
/* Equadis look: navy and green (change them here for the whole Excel) */
const NAVY = 'FF112032', GREEN = 'FF58EA9D', DKGREEN = 'FF0F7A55', SOFT = 'FF5A6B7C', PH = 'FFE3E9EF', WHITE = 'FFFFFFFF', GRID = 'FFC7D0D8';
const FILL = { 1: 'FF2F5D8A', 2: 'FF58EA9D', 3: 'FF112032', 4: 'FFC7D0D8', 5: 'FFC0504D', 6: 'FFD9A945', 7: 'FF8B5CF6' };
const STFILL = { co: ['FFDFF6EA', 'FF0F7A55'], ot: ['FFDCE6F5', 'FF2F5597'], ar: ['FFF5EBD8', 'FF8A5E10'], bl: ['FFF4E1DD', 'FF9E3A2C'], ns: ['FFEDF0F3', 'FF5A6B7C'], wc: ['FFF1ECFE', 'FF5B3FC4'] };
const colL = n => { let s = ''; for (n++; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + (n - 1) % 26) + s; return s; };
const xd = s => { const n = dn(s); return n == null ? null : new Date(n * 864e5); };
const solid = argb => ({ type: 'pattern', pattern: 'solid', fgColor: { argb } });
const thin = { style: 'thin', color: { argb: GRID } }, box = { top: thin, left: thin, bottom: thin, right: thin };
const safeName = s => String(s || '').replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim();

function phasesForExport() { return S.phases.filter(p => p.tasks.length); }

/* rows 1-3 of every sheet: the Equadis band, the title, the project manager in green */
function brand(ws, last, title, W) {
  ws.mergeCells('A1:' + last + '1'); const b = ws.getCell('A1');
  b.value = { richText: [{ text: 'equadis', font: { bold: true, size: 15, color: { argb: GREEN } } },
                         { text: '     Project Manager Desk', font: { size: 11, color: { argb: WHITE } } }] };
  b.fill = solid(NAVY); b.alignment = { vertical: 'middle', indent: 1 }; ws.getRow(1).height = 28;
  ws.mergeCells('A2:' + last + '2'); const t = ws.getCell('A2'); t.value = title;
  t.font = { bold: true, size: 16, color: { argb: NAVY } }; t.alignment = { vertical: 'bottom' }; ws.getRow(2).height = 26;
  ws.getCell('A3').value = { richText: [{ text: W.pm + ' : ', font: { color: { argb: SOFT } } },
    { text: S.project.pm || '-', font: { bold: true, color: { argb: DKGREEN } } },
    { text: '     ' + W.updated + ' ' + fmt(ds(todayN())), font: { color: { argb: SOFT } } }] };
}
const headLine = row => row.eachCell(c => { c.border = Object.assign({}, c.border || {}, { bottom: { style: 'medium', color: { argb: GREEN } } }); });

function sheetRaci(wb, W) {
  const ws = wb.addWorksheet(W.raci, { views: [{ state: 'frozen', ySplit: 4, showGridLines: false }] });
  ws.columns = [{ width: 52 }, { width: 15 }, { width: 18 }, { width: 14 }, { width: 20 }, { width: 24 }, { width: 40 }];
  brand(ws, 'G', W.raci + ' - ' + S.project.client + ' / ' + S.project.name, W);
  const hr = ws.getRow(4); hr.values = [W.task, W.status, W.R, W.A, W.C, W.I, W.comment];
  hr.eachCell(c => { c.fill = solid(NAVY); c.font = { bold: true, color: { argb: WHITE } }; c.alignment = { vertical: 'middle', wrapText: true }; c.border = box; }); hr.height = 22; headLine(hr);
  let r = 5; const rows = {}, list = '"' + ST.map(k => W.st[k]).join(',') + '"';
  phasesForExport().forEach(p => {
    const first = r + 1, last = r + p.tasks.length, n = p.tasks.length, done = p.tasks.filter(x => x.status === 'co').length;
    const row = ws.getRow(r); row.getCell(1).value = p.name;
    row.getCell(2).value = { formula: 'COUNTIF(B' + first + ':B' + last + ',"' + W.st.co + '")&" / ' + n + ' ' + W.done + '"', result: done + ' / ' + n + ' ' + W.done };
    for (let c = 1; c <= 7; c++) { const x = row.getCell(c); x.fill = solid(PH); x.font = { bold: true, color: { argb: NAVY } }; x.border = box; }
    rows[p.id] = r; r++;
    p.tasks.forEach(tk => {
      const row = ws.getRow(r);
      const wait = tk.status === 'wc' && tk.since ? W.since + ' ' + fmt(tk.since) : '';
      row.values = [tk.name, W.st[tk.status], tk.r.join(', '), tk.a, tk.c.join(', '), tk.i.join(', '), [wait, tk.note].filter(Boolean).join(' · ')];
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

const navyHead = row => { row.eachCell(c => { c.fill = solid(NAVY); c.font = { bold: true, color: { argb: WHITE } }; c.alignment = { vertical: 'middle', wrapText: true }; c.border = box; }); row.height = 22; headLine(row); };
const sref = (name, col, r) => "'" + name.replace(/'/g, "''") + "'!" + col + r;

function sheetScope(wb, W) {
  const sc = S.scope, ncol = Math.max(4, ...sc.tables.map(x => x.cols.length)), last = colL(ncol - 1);
  const ws = wb.addWorksheet(W.scope, { views: [{ showGridLines: false }] });
  ws.columns = Array.from({ length: ncol }, (_, i) => ({ width: i ? 26 : 30 }));
  brand(ws, last, W.scope + ' - ' + S.project.client + ' / ' + S.project.name, W);
  let r = 5;
  const section = txt => { ws.mergeCells('A' + r + ':' + last + r); const c = ws.getCell('A' + r); c.value = txt;
    c.font = { bold: true, size: 13, color: { argb: NAVY } }; c.border = { bottom: { style: 'medium', color: { argb: GREEN } } }; ws.getRow(r).height = 22; r += 1; };
  const fields = sc.fields.filter(f => f.label || f.value.trim());
  if (fields.length) {
    section(W.overview);
    fields.forEach(f => {
      ws.mergeCells('B' + r + ':' + last + r);
      const a = ws.getCell('A' + r), b = ws.getCell('B' + r); a.value = f.label; b.value = f.value;
      a.font = { bold: true, color: { argb: NAVY } }; a.fill = solid(PH); a.border = box; a.alignment = { vertical: 'top', wrapText: true };
      b.border = box; b.alignment = { vertical: 'top', wrapText: true };
      ws.getRow(r).height = Math.max(18, Math.ceil(f.value.length / (26 * (ncol - 1) * 1.1)) * 15); r++;
    });
    r++;
  }
  sc.tables.forEach(x => {
    const rows = x.rows.filter(v => v.some(c => String(c).trim()));
    section(x.name + ' (' + rows.length + ')');
    const hr = ws.getRow(r); hr.values = x.cols; navyHead(hr); r++;
    rows.forEach(v => { const row = ws.getRow(r); row.values = v; x.cols.forEach((_, i) => { const c = row.getCell(i + 1); c.border = box; c.alignment = { vertical: 'top', wrapText: true }; }); r++; });
    r++;
  });
  ws.pageSetup = { orientation: 'landscape', paperSize: 9, fitToPage: true, fitToWidth: 1, fitToHeight: 0 };
}

/* Tracker: one row per task, the counts on top, overdue and days left worked out by Excel every day */
function sheetTracker(wb, W, raciRows) {
  const ws = wb.addWorksheet(W.tracker, { views: [{ state: 'frozen', ySplit: 7, showGridLines: false }] });
  ws.columns = [{ width: 7 }, { width: 24 }, { width: 50 }, { width: 34 }, { width: 18 }, { width: 11 }, { width: 11 }, { width: 18 }, { width: 11 }, { width: 11 }, { width: 34 }];
  brand(ws, 'K', W.tracker + ' - ' + S.project.client + ' / ' + S.project.name, W);
  const st = W.st, today = todayN(), people = c => { const x = S.roles.find(r => r.code === c); return x && x.name.trim() ? x.name.trim() : c; };
  const hr = ws.getRow(7); hr.values = [W.id, W.phase, W.tk, W.detail, W.owner, W.start, W.due, W.status, W.overdue, W.daysLeft, W.notes]; navyHead(hr);
  let r = 8; const rows = {}, list = '"' + ST.map(k => st[k]).join(',') + '"';
  const late = tk => tk.status !== 'co' && dn(tk.end || tk.start) != null && dn(tk.end || tk.start) < today;
  phasesForExport().forEach((p, pi) => p.tasks.forEach((tk, ti) => {
    const row = ws.getRow(r), due = dn(tk.end || tk.start);
    row.getCell(1).value = (pi + 1) + '.' + (ti + 1);
    row.getCell(2).value = p.name; row.getCell(3).value = (tk.milestone ? '◆ ' : '') + tk.name; row.getCell(4).value = tk.note || '';
    row.getCell(5).value = tk.r.map(people).join(', ');
    row.getCell(6).value = xd(tk.start); row.getCell(7).value = xd(tk.end || tk.start);
    row.getCell(8).value = raciRows && raciRows[tk.id] ? { formula: sref(W.raci, 'B', raciRows[tk.id]), result: st[tk.status] } : st[tk.status];
    if (!raciRows) row.getCell(8).dataValidation = { type: 'list', allowBlank: true, formulae: [list] };
    row.getCell(9).value = { formula: 'IF(AND(H' + r + '<>"' + st.co + '",G' + r + '<>"",G' + r + '<TODAY()),"' + W.overdue + '","")', result: late(tk) ? W.overdue : '' };
    row.getCell(10).value = { formula: 'IF(OR(H' + r + '="' + st.co + '",G' + r + '=""),"",G' + r + '-TODAY())', result: tk.status === 'co' || due == null ? '' : due - today };
    row.getCell(11).value = tk.status === 'wc' && tk.since ? W.since + ' ' + fmt(tk.since) : '';
    for (let c = 1; c <= 11; c++) { const x = row.getCell(c); x.border = box; x.alignment = { vertical: 'top', wrapText: [3, 4, 11].includes(c), horizontal: [1, 9, 10].includes(c) ? 'center' : undefined }; }
    [6, 7].forEach(c => row.getCell(c).numFmt = 'dd/mm/yyyy'); row.getCell(10).numFmt = '0';
    rows[tk.id] = r; r++;
  }));
  const end = Math.max(8, r - 1), H = 'H8:H' + end, all = allTasks(), n = all.length, cnt = k => all.filter(x => x.status === k).length;
  /* the counts, rows 4-5 */
  const ms = phasesForExport().flatMap(p => p.tasks).filter(x => x.milestone && rows[x.id]).sort((a, b) => dn(a.start) - dn(b.start));
  const goal = ms[ms.length - 1], goalRow = goal ? rows[goal.id] : null;
  const lastDay = Math.max(...all.map(x => dn(x.end || x.start)).filter(x => x != null));
  const kpi = [
    [W.tasks, { formula: 'COUNTA(C8:C' + end + ')', result: n }],
    [st.co, { formula: 'COUNTIF(' + H + ',"' + st.co + '")', result: cnt('co') }],
    [st.ot, { formula: 'COUNTIF(' + H + ',"' + st.ot + '")', result: cnt('ot') }],
    [st.ar, { formula: 'COUNTIF(' + H + ',"' + st.ar + '")', result: cnt('ar') }],
    [st.ns, { formula: 'COUNTIF(' + H + ',"' + st.ns + '")', result: cnt('ns') }],
    [st.wc, { formula: 'COUNTIF(' + H + ',"' + st.wc + '")', result: cnt('wc') }],
    [st.bl, { formula: 'COUNTIF(' + H + ',"' + st.bl + '")', result: cnt('bl') }],
    [W.overdue, { formula: 'COUNTIF(I8:I' + end + ',"' + W.overdue + '")', result: all.filter(late).length }],
    [W.pctDone, { formula: 'IF(B5=0,0,C5/B5)', result: n ? cnt('co') / n : 0 }],
    [W.daysTo + ' ' + (goal ? goal.name : W.theEnd), goalRow ? { formula: 'G' + goalRow + '-TODAY()', result: dn(goal.start) - today }
      : { formula: 'MAX(G8:G' + end + ')-TODAY()', result: isFinite(lastDay) ? lastDay - today : 0 }],
  ];
  kpi.forEach(([label, val], i) => {
    const a = ws.getCell(4, i + 2), b = ws.getCell(5, i + 2); a.value = label; b.value = val;
    a.font = { bold: true, size: 9, color: { argb: SOFT } }; a.alignment = { horizontal: 'center', vertical: 'bottom', wrapText: true }; a.fill = solid(PH);
    b.font = { bold: true, size: 16, color: { argb: i === 7 || i === 6 ? 'FF9E3A2C' : i === 1 ? DKGREEN : NAVY } }; b.alignment = { horizontal: 'center' };
    a.border = box; b.border = box; b.numFmt = i === 8 ? '0%' : '0';
  });
  ws.getRow(4).height = 30; ws.getRow(5).height = 26;
  ws.autoFilter = 'A7:K' + end;
  ws.addConditionalFormatting({ ref: H, rules: ST.map((k, i) => ({ type: 'cellIs', operator: 'equal', priority: i + 1, formulae: ['"' + st[k] + '"'],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: STFILL[k][0] } }, font: { color: { argb: STFILL[k][1] }, bold: true } } })) });
  ws.addConditionalFormatting({ ref: 'I8:I' + end, rules: [{ type: 'cellIs', operator: 'equal', priority: 1, formulae: ['"' + W.overdue + '"'],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: STFILL.bl[0] } }, font: { color: { argb: STFILL.bl[1] }, bold: true } } }] });
  ws.addConditionalFormatting({ ref: 'J8:J' + end, rules: [{ type: 'expression', priority: 1, formulae: ['AND(ISNUMBER(J8),J8<0)'],
    style: { font: { color: { argb: STFILL.bl[1] }, bold: true } } }] });
  ws.pageSetup = { orientation: 'landscape', paperSize: 9, fitToPage: true, fitToWidth: 1, fitToHeight: 0 };
  return rows;
}

/* src: the sheet the Gantt reads its names and statuses from (RACI, else Tracker), so a status is changed in one place */
function sheetGantt(wb, W, src) {
  const today = todayN(), week = S.project.scale !== 'day';
  const ts = allTasks().filter(t => dn(t.start) != null);
  const a0 = Math.min(...ts.map(t => dn(t.start))), b0 = Math.max(...ts.map(t => dn(t.end || t.start)));
  const step = week ? 7 : 1, first = week ? monday(a0) : a0;
  const ncol = Math.min(week ? 104 : 200, Math.floor((b0 - first) / step) + (week ? 2 : 3));
  const C0 = 6;                                                        // timeline starts at column G
  const ws = wb.addWorksheet(W.gantt, { views: [{ state: 'frozen', xSplit: C0, ySplit: 5, showGridLines: false }] });
  ws.columns = [{ width: 46 }, { width: 14 }, { width: 14 }, { width: 11 }, { width: 11 }, { width: 6 }].concat(Array.from({ length: ncol }, () => ({ width: week ? 4.2 : 3.2 })));
  const lastL = colL(C0 + ncol - 1);
  brand(ws, lastL, W.gantt + ' - ' + S.project.client + ' / ' + S.project.name, W);
  const loc = W.locale, hr = ws.getRow(5);
  [W.task, W.status, W.resp, W.start, W.end, W.days].forEach((v, i) => { const c = hr.getCell(i + 1); c.value = v; });
  let mStart = null, mKey = null;
  for (let k = 0; k <= ncol; k++) {
    const d = first + k * step, key = k < ncol ? new Date(d * 864e5).toISOString().slice(0, 7) : null;
    if (key !== mKey) {
      if (mKey != null) { const a = colL(C0 + mStart), b = colL(C0 + k - 1); if (a !== b) ws.mergeCells(a + '4:' + b + '4');
        const c = ws.getCell(a + '4'); c.value = new Date(dn(mKey + '-01') * 864e5).toLocaleDateString(loc, { month: 'short', year: '2-digit', timeZone: 'UTC' });
        c.font = { bold: true, color: { argb: GREEN } }; c.fill = solid(NAVY); c.alignment = { horizontal: 'center' }; }
      mStart = k; mKey = key;
    }
    if (k < ncol) { const c = hr.getCell(C0 + k + 1); c.value = new Date(d * 864e5); c.numFmt = week ? 'dd/mm' : 'dd'; c.alignment = { horizontal: 'center', textRotation: week ? 90 : 0 }; }
  }
  hr.height = week ? 40 : 20;
  hr.eachCell(c => { c.font = { bold: true, color: { argb: WHITE } }; c.fill = solid(NAVY); c.border = box; if (!c.alignment) c.alignment = { vertical: 'middle' }; }); headLine(hr);
  const st = W.st, cell = (k, r) => colL(C0 + k) + r, H = k => colL(C0 + k) + '$5';
  const inner = r => 'IF($B' + r + '="' + st.co + '",2,IF($B' + r + '="' + st.wc + '",7,IF(OR($B' + r + '="' + st.bl + '",$E' + r + '<TODAY()),5,IF($B' + r + '="' + st.ns + '",4,1))))';
  const inRange = (r, k) => week ? 'AND($D' + r + '<=' + H(k) + '+6,$E' + r + '>=' + H(k) + ')' : 'AND($D' + r + '<=' + H(k) + ',$E' + r + '>=' + H(k) + ')';
  const hit = (a, b, d) => week ? (a <= d + 6 && b >= d) : (a <= d && b >= d);
  const code = tk => tk.milestone ? 6 : tk.status === 'co' ? 2 : tk.status === 'wc' ? 7 : (tk.status === 'bl' || dn(tk.end || tk.start) < today) ? 5 : tk.status === 'ns' ? 4 : 1;
  let r = 6;
  const ref = (key, f, val) => src && src.rows[key] ? { formula: sref(src.sheet, src.cols[f], src.rows[key]), result: val } : val;
  phasesForExport().forEach(p => {
    const pr = r, f = r + 1, l = r + p.tasks.length, row = ws.getRow(pr);
    const dts = p.tasks.filter(x => dn(x.start) != null), pa = dts.length ? Math.min(...dts.map(x => dn(x.start))) : null, pb = dts.length ? Math.max(...dts.map(x => dn(x.end || x.start))) : null;
    row.getCell(1).value = ref(p.id, 'name', p.name);
    if (src && src.rows[p.id]) { const dn_ = p.tasks.filter(x => x.status === 'co').length; row.getCell(2).value = ref(p.id, 'status', dn_ + ' / ' + p.tasks.length + ' ' + W.done); }
    row.getCell(4).value = { formula: 'IF(COUNT(D' + f + ':D' + l + ')=0,"",MIN(D' + f + ':D' + l + '))', result: pa != null ? new Date(pa * 864e5) : '' };
    row.getCell(5).value = { formula: 'IF(COUNT(E' + f + ':E' + l + ')=0,"",MAX(E' + f + ':E' + l + '))', result: pb != null ? new Date(pb * 864e5) : '' };
    row.getCell(6).value = { formula: 'IF(OR(D' + pr + '="",E' + pr + '=""),"",E' + pr + '-D' + pr + '+1)', result: pa != null ? pb - pa + 1 : '' };
    for (let k = 0; k < ncol; k++) row.getCell(C0 + k + 1).value = { formula: 'IF(OR($D' + pr + '="",$E' + pr + '=""),"",IF(' + inRange(pr, k) + ',3,""))', result: pa != null && hit(pa, pb, first + k * step) ? 3 : '' };
    for (let c = 1; c <= 6; c++) { const x = row.getCell(c); x.fill = solid(PH); x.font = { bold: true, color: { argb: NAVY } }; x.border = box; }
    r++;
    p.tasks.forEach(tk => {
      const row = ws.getRow(r), a = dn(tk.start), b = dn(tk.end || tk.start);
      row.getCell(1).value = ref(tk.id, 'name', (tk.milestone && !(src && src.mark) ? '◆ ' : '') + tk.name);
      row.getCell(2).value = ref(tk.id, 'status', st[tk.status]);
      row.getCell(3).value = ref(tk.id, 'resp', src && src.cols.resp === 'E' ? tk.r.map(c => { const x = S.roles.find(y => y.code === c); return x && x.name.trim() ? x.name.trim() : c; }).join(', ') : tk.r.join(', '));
      row.getCell(4).value = xd(tk.start); row.getCell(5).value = xd(tk.end || tk.start);
      row.getCell(6).value = { formula: 'IF(OR(D' + r + '="",E' + r + '=""),"",E' + r + '-D' + r + '+1)', result: a != null ? b - a + 1 : '' };
      const val = tk.milestone ? '6' : inner(r);
      for (let k = 0; k < ncol; k++) row.getCell(C0 + k + 1).value = { formula: 'IF(OR($D' + r + '="",$E' + r + '=""),"",IF(' + inRange(r, k) + ',' + val + ',""))', result: a != null && hit(a, b, first + k * step) ? code(tk) : '' };
      row.getCell(1).alignment = { indent: 1, vertical: 'middle' };
      if (!src) row.getCell(2).dataValidation = { type: 'list', allowBlank: true, formulae: ['"' + ST.map(k => st[k]).join(',') + '"'] };
      for (let c = 1; c <= 6; c++) row.getCell(c).border = box;
      r++;
    });
  });
  const end = r - 1;
  ws.getCell('A' + (end + 2)).value = W.glegend; ws.getCell('A' + (end + 2)).font = { color: { argb: SOFT }, size: 10 };
  [4, 5].forEach(c => { for (let i = 6; i <= end; i++) ws.getCell(i, c).numFmt = 'dd/mm/yyyy'; });
  for (let i = 6; i <= end; i++) for (let k = 0; k < ncol; k++) { const c = ws.getCell(i, C0 + k + 1); c.border = { left: { style: 'hair', color: { argb: GRID } }, bottom: { style: 'hair', color: { argb: GRID } } }; }
  const tl = colL(C0) + '6:' + lastL + end, H0 = colL(C0);
  const rules = [1, 2, 3, 4, 5, 6, 7].map((v, i) => ({ type: 'cellIs', operator: 'equal', priority: i + 1, formulae: [String(v)],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: FILL[v] } }, font: { color: { argb: FILL[v] } } } }));
  rules.push({ type: 'expression', priority: 8, formulae: [week ? 'AND(' + H0 + '$5<=TODAY(),TODAY()<' + H0 + '$5+7)' : H0 + '$5=TODAY()'],
    style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: 'FFFFF2CC' } } } });
  if (!week) rules.push({ type: 'expression', priority: 9, formulae: ['WEEKDAY(' + H0 + '$5,2)>5'], style: { fill: { type: 'pattern', pattern: 'solid', bgColor: { argb: 'FFF2F2F2' } } } });
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
  if (opts.scope) sheetScope(wb, W);
  const raciRows = opts.raci ? sheetRaci(wb, W) : null;
  const trackRows = opts.tracker ? sheetTracker(wb, W, raciRows) : null;
  if (opts.gantt) sheetGantt(wb, W, raciRows ? { sheet: W.raci, rows: raciRows, cols: { name: 'A', status: 'B', resp: 'C' } }
    : trackRows ? { sheet: W.tracker, rows: trackRows, mark: true, cols: { name: 'C', status: 'H', resp: 'E' } } : null);
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
  const opts = sheetOpts(), W = L[S.project.lang], on = Object.keys(opts).filter(k => opts[k]);
  if (!on.length) { out.className = 'status ko'; out.textContent = 'Tick at least one sheet.'; return; }
  try {
    const kind = on.length > 1 ? 'Planning' : W[on[0]];
    const name = safeName(S.project.client + ' - ' + S.project.name + ' - ' + kind + ' ' + ds(todayN()).split('-').reverse().join('')) + '.xlsx';
    await saveFile(await buildWorkbook(opts), name);
    out.className = 'status ok'; out.textContent = 'Saved ' + name;
  } catch (e) { out.className = 'status ko'; out.textContent = 'Export failed: ' + (e && e.message || e); }
};
function sheetOpts() { const o = {}; ['scope', 'raci', 'tracker', 'gantt'].forEach(k => o[k] = S.sheets.includes(k)); if (!allTasks().some(t => dn(t.start) != null)) o.gantt = false; return o; }

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
    if (!o.id) o.id = uid() + uid();
    S = upgrade(o); S.file = null; renderAll(); note.textContent = 'Opened ' + f.name;
  } catch (err) { note.textContent = 'Could not open ' + f.name + ': ' + (err.message || err); }
};

/* ---------- templates ---------- */
const sel = $('#tpl');
window.PLANNER_TEMPLATES.forEach(tp => { const o = el('option', null, tp.name + ' - ' + tp.note); o.value = tp.id; sel.appendChild(o); });
sel.value = 'product';
$('#tplGo').onclick = () => {
  const tp = window.PLANNER_TEMPLATES.find(x => x.id === sel.value);
  const filled = allTasks().some(t => t.name);
  if (filled && !confirm('Replace the current plan with the "' + tp.name + '" template? Project details are kept.')) return;
  const keep = S && S.project;
  S = fromTemplate(tp, (keep && keep.start) || ds(monday(todayN())), keep && keep.lang); S.file = null;
  if (keep) Object.assign(S.project, keep);
  renderAll();
};
$('#scAdd').onclick = () => { S.scope.fields.push({ id: uid(), label: '', value: '', hint: '' }); renderScope(); refresh(); };
$('#phaseAdd').onclick = () => { S.phases.push({ id: uid(), name: '', tasks: [] }); renderPhases(); refresh(); focusKey('ph:' + S.phases[S.phases.length - 1].id); };
$('#roleAdd').onclick = () => { S.roles.push({ id: uid(), code: '', title: '', name: '', side: 'Equadis' }); renderRoles(); refresh(); focusKey('r:' + S.roles[S.roles.length - 1].id + ':code'); };

/* ---------- inside the desk: follow its light / dark theme ---------- */
try {
  const pd = window.parent !== window && window.parent.document.documentElement;
  if (pd) { const sync = () => { const t = pd.getAttribute('data-theme'); if (t) document.documentElement.setAttribute('data-theme', t); else document.documentElement.removeAttribute('data-theme'); };
    sync(); new MutationObserver(sync).observe(pd, { attributes: true, attributeFilter: ['data-theme'] }); document.querySelector('main').style.paddingTop = '8px'; }
} catch (e) { /* another origin: keep the system theme */ }

S = fromTemplate(window.PLANNER_TEMPLATES.find(x => x.id === 'product'), ds(monday(todayN())), 'en');
/* ---------- project archive: a SharePoint folder synced on the laptop, through the TPM Desk's Claude link ----------
   Only when the planner runs inside the desk opened from its folder (file://). On the public portal the
   link refuses the call, and the card offers the SharePoint folder link instead. */
const LINK = 'http://127.0.0.1:8765';
const link = async (path, body) => {
  const r = await fetch(LINK + path, body === undefined ? { headers: { 'X-TPM-Desk': '1' } }
    : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-TPM-Desk': '1' }, body: JSON.stringify(body) });
  const d = await r.json().catch(() => ({})); if (!r.ok) { const e = new Error(d.message || 'The desk link refused.'); e.code = d.code; throw e; } return d;
};
let linked = false, projects = [];
const arOut = (t, ok) => { const o = $('#arOut'); o.textContent = t || ''; o.className = 'status' + (t ? (ok ? ' ok' : ' ko') : ''); };
const planFile = () => S.file || safeName(S.project.client + ' - ' + S.project.name + ' - Planning') + '.xlsx';
const b64of = buf => { const u = new Uint8Array(buf); let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); };
async function archiveRefresh() {
  let d;
  try { d = await link('/archive'); } catch (e) { return; }
  $('#arPick').hidden = !!d.projects; $('#arList').hidden = !d.projects;
  if (!d.projects) { $('#arPath').value = d.archive_dir || ''; $('#arSub').textContent = 'Choose the archive folder'; return; }
  projects = d.projects; $('#arSub').textContent = projects.length + ' project' + (projects.length !== 1 ? 's' : '') + ' · ' + d.archive_dir;
  drawProjects();
}
function drawProjects() {
  const q = $('#arFind').value.trim().toLowerCase(), tb = $('#arRows'); tb.innerHTML = '';
  const list = projects.filter(p => !q || (p.client + ' ' + p.project + ' ' + p.pm).toLowerCase().includes(q));
  if (!list.length) { const tr = el('tr'), td = el('td', 'note', projects.length ? 'No project matches.' : 'No plan saved yet: build one below and press Save to archive.'); td.colSpan = 7; tr.appendChild(td); tb.appendChild(tr); return; }
  list.forEach(p => {
    const tr = el('tr', S && p.id === S.id ? 'cur' : null), pc = p.tasks ? Math.round(p.done / p.tasks * 100) : 0;
    [p.client, p.project, p.pm, (p.start ? fmt(p.start) : '') + (p.end ? ' → ' + fmt(p.end) : '')].forEach(v => tr.appendChild(el('td', null, v)));
    const pr = el('td'), bar = el('span', 'bar100'), fill = el('i'); fill.style.width = pc + '%'; bar.appendChild(fill); pr.append(bar, p.done + ' / ' + p.tasks);
    if (p.waiting) { const w = el('span', 'waiting', ' · ' + p.waiting + ' waiting on client'); pr.appendChild(w); } tr.appendChild(pr);
    tr.appendChild(el('td', 'note', new Date(p.modified * 1000).toLocaleDateString(L[(S && S.project.lang) || 'en'].locale)));
    const a = el('td'), b = el('button', 'btn sm', S && p.id === S.id ? 'Open again' : 'Open'); b.onclick = () => openArchived(p.file); a.appendChild(b); tr.appendChild(a);
    tb.appendChild(tr);
  });
}
async function openArchived(file) {
  const dirty = S && S.project.client && !(projects.find(p => p.id === S.id));   // a plan someone started, never saved
  if (dirty && !confirm('The plan on screen is not saved in the archive. Open "' + file + '" anyway?')) return;
  try {
    const d = await link('/archive/read', { file });
    const raw = Uint8Array.from(atob(d.data), c => c.charCodeAt(0));
    const wb = new ExcelJS.Workbook(); await wb.xlsx.load(raw.buffer);
    const ws = wb.getWorksheet('_plan'); if (!ws) throw new Error('no plan inside');
    let js = ''; ws.eachRow(r => { js += String(r.getCell(1).value || ''); });
    const o = JSON.parse(js); if (!o.id) o.id = uid() + uid();
    S = upgrade(o); S.file = file; renderAll(); drawProjects(); arOut('Opened ' + file, true);
    $('#cProject').scrollIntoView({ behavior: 'smooth' });
  } catch (e) { arOut('Could not open ' + file + ': ' + (e.message || e)); }
}
async function archiveSave(overwrite) {
  if (!S.project.client || !S.project.name) { arOut('Give the client and the project a name first (step 1).'); focusKey(!S.project.client ? 'p:client' : 'p:name'); return; }
  const file = planFile(), out = $('#xOut');
  try {
    const keep = S.file; S.file = null;                          // the file name is not part of the plan itself
    const o = sheetOpts(); if (!o.raci && !o.tracker) o.raci = true;
    const buf = await buildWorkbook(o); S.file = keep;
    await link('/archive/save', { file, data: b64of(buf), id: S.id, overwrite: !!overwrite });
    S.file = file; out.className = 'status ok'; out.textContent = 'Saved in the archive: ' + file;
    archiveRefresh();
  } catch (e) {
    if (e.code === 'exists' && confirm(e.message + ' Replace it with this plan?')) return archiveSave(true);
    out.className = 'status ko'; out.textContent = 'Not saved: ' + (e.message || e);
  }
}
$('#xSave').onclick = () => archiveSave(false);
$('#arUse').onclick = () => link('/archive/folder', { path: $('#arPath').value }).then(() => { arOut('Archive folder saved on this laptop.', true); archiveRefresh(); }).catch(e => arOut(e.message));
$('#arChange').onclick = () => { $('#arPick').hidden = false; $('#arList').hidden = true; $('#arPath').focus(); };
$('#arDir').onclick = () => link('/archive/open', {}).catch(e => arOut(e.message));
$('#arFind').oninput = drawProjects;
$('#arNew').onclick = () => { $('#tpl').focus(); $('#tpl').scrollIntoView({ behavior: 'smooth', block: 'center' }); arOut('Pick a template above, then press Start from this template.', true); };
/* not linked: the SharePoint folder link, kept in this browser only */
const URLKEY = 'planner-archive-url';
const setUrl = v => { const a = $('#arGo'); if (/^https:\/\//i.test(v)) { a.href = v; a.removeAttribute('aria-disabled'); a.style.opacity = ''; } else { a.removeAttribute('href'); a.setAttribute('aria-disabled', 'true'); a.style.opacity = '.5'; } };
try { $('#arUrl').value = localStorage.getItem(URLKEY) || ''; } catch (e) { /* no storage here */ }
setUrl($('#arUrl').value);
$('#arUrl').oninput = () => { const v = $('#arUrl').value.trim(); setUrl(v); try { localStorage.setItem(URLKEY, v); } catch (e) { /* no storage here */ } };
(async () => {
  if (location.protocol !== 'file:' && !(location.protocol === 'about:' && (() => { try { return window.parent.location.protocol === 'file:'; } catch (e) { return false; } })())) return;
  try { const h = await link('/health'); if (!h.archive) return; } catch (e) { return; }
  linked = true; $('#arLinked').hidden = false; $('#arOffline').hidden = true; $('#xSave').hidden = false;
  archiveRefresh();
})();
renderAll();
})();
