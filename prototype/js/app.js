/* 云枢智学 · 交互原型（路由 / C 端页面 / 通用交互）
 * 结构：学科 → 课程节点图（线性顺序）→ 点亮；题目与答卷挂学科。
 * 纯前端原型，无服务端逻辑；判分与 AI 点评均为本地模拟。
 *
 * 双端入口：
 *   index.html  → APP_SCOPE = 'student'（学员端，默认）
 *   admin.html  → APP_SCOPE = 'admin'  （管理端，独立页面，与学员端互相跳转）
 * 正式实现中两端是两个独立工程（frontend-student / frontend-admin），原型共用一份脚本仅为了演示方便。
 */

const APP_SCOPE = window.APP_SCOPE === 'admin' ? 'admin' : 'student';

/* ==================== 基础工具 ==================== */

function esc(text) {
  return String(text == null ? '' : text).replace(/[&<>"]/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
  });
}

function pad(n) { return n < 10 ? '0' + n : '' + n; }

function fmtTime(ts) {
  const d = new Date(ts);
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
    ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
}

function toast(msg) {
  const root = document.getElementById('toast-root');
  const box = document.createElement('div');
  box.className = 'toast';
  box.textContent = msg;
  root.appendChild(box);
  setTimeout(function () { box.remove(); }, 2200);
}

function shuffle(list) {
  const arr = list.slice();
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
  }
  return arr;
}

function go(hash) { location.hash = hash; }

function progressBar(rate) {
  return '<div class="progress"><i style="width:' + rate + '%"></i></div>';
}

function statusTag(status, onText, offText) {
  return status
    ? '<span class="tag tag-green">' + (onText || '已上架') + '</span>'
    : '<span class="tag">' + (offText || '已下架') + '</span>';
}

/* ---------------- 弹窗 ---------------- */
let modalOnOk = null;

function openModal(opts) {
  const fieldsHtml = (opts.fields || []).map(function (f) {
    const id = 'mf-' + f.key;
    let control;
    if (f.type === 'select') {
      control = '<select class="select" id="' + id + '">' + f.options.map(function (o) {
        return '<option value="' + esc(o) + '">' + esc(o) + '</option>';
      }).join('') + '</select>';
    } else if (f.type === 'textarea') {
      control = '<textarea class="textarea" id="' + id + '">' + esc(f.value || '') + '</textarea>';
    } else {
      control = '<input class="input" id="' + id + '" value="' + esc(f.value || '') + '" placeholder="' + esc(f.placeholder || '') + '">';
    }
    return '<div class="field"><label>' + esc(f.label) + '</label>' + control + '</div>';
  }).join('');

  document.getElementById('modal-root').innerHTML =
    '<div class="modal-mask" data-act="modal-close-bg">' +
      '<div class="modal">' +
        '<div class="modal-head">' + esc(opts.title) + '</div>' +
        '<div class="modal-body">' + (opts.body || fieldsHtml) + '</div>' +
        '<div class="modal-foot">' +
          '<button class="btn" data-act="modal-close">取消</button>' +
          '<button class="btn btn-primary" data-act="modal-ok">' + esc(opts.okText || '确定') + '</button>' +
        '</div>' +
      '</div>' +
    '</div>';

  modalOnOk = function () {
    const data = {};
    (opts.fields || []).forEach(function (f) {
      const el = document.getElementById('mf-' + f.key);
      data[f.key] = el ? el.value.trim() : '';
    });
    if (opts.onOk) opts.onOk(data);
  };
}

function closeModal() {
  document.getElementById('modal-root').innerHTML = '';
  modalOnOk = null;
  retryState = null;
}

/* ==================== 进度与统计 ==================== */

function courseDone(courseId) {
  return !!state.completedCourses[courseId];
}

/* 学科进度：已点亮 / 上架课程总数 */
function subjectProgress(subjectId) {
  const courses = coursesOfSubject(subjectId).filter(function (c) { return c.status; });
  const total = courses.length;
  if (!total) return { done: 0, total: 0, rate: 0 };
  const done = courses.filter(function (c) { return courseDone(c.id); }).length;
  return { done: done, total: total, rate: Math.round(done / total * 100) };
}

function nextCourse(subjectId) {
  return coursesOfSubject(subjectId).filter(function (c) {
    return c.status && !courseDone(c.id);
  })[0] || null;
}

/* ==================== 判分 ==================== */

const TYPE_LABEL = { judge: '判断题', single: '单选题', multi: '多选题', short: '简答题' };

function optionList(q) {
  if (q.type === 'judge') {
    return [{ k: 'A', t: '正确' }, { k: 'B', t: '错误' }];
  }
  return q.options || [];
}

function displayAnswer(item) {
  if (!item.myAnswer) return '未作答';
  if (item.type === 'judge') return item.myAnswer === 'A' ? '正确' : '错误';
  return item.myAnswer;
}

function answerText(q) {
  if (q.type === 'judge') return q.answer === 'A' ? '正确' : '错误';
  if (q.type === 'multi') return (q.answer || []).join('、');
  return q.answer || '';
}

function gradeQuestion(q, answer) {
  if (q.type === 'short') {
    return {
      qid: q.id, type: q.type, max: q.score, score: null, correct: null,
      myAnswer: answer || '', comment: 'AI 正在对照参考答案判分…', pending: true
    };
  }
  let correct = false;
  if (q.type === 'multi') {
    const mine = Array.isArray(answer) ? answer.slice().sort().join('') : '';
    correct = mine === (q.answer || []).slice().sort().join('');
  } else {
    correct = answer === q.answer;
  }
  return {
    qid: q.id, type: q.type, max: q.score, score: correct ? q.score : 0, correct: correct,
    myAnswer: Array.isArray(answer) ? answer.join('、') : (answer || ''),
    comment: correct ? '回答正确。' : '回答错误，正确答案：' + answerText(q),
    pending: false
  };
}

function shortComment(score, max) {
  const rate = score / max;
  if (rate >= 0.85) return '要点覆盖完整，表述清晰，与参考答案的关键点基本一致，能够结合具体场景展开。';
  if (rate >= 0.6) return '核心要点基本覆盖，但与参考答案相比缺少部分关键机制说明，建议补齐实现层面的描述。';
  if (rate > 0) return '只答到表层概念，参考答案中的关键要点大多未覆盖，建议对照参考解析重新梳理。';
  return '未作答或内容与本题目无关，判为 0 分。';
}

function addWrong(qid, lastScore) {
  const exist = state.wrongBook.find(function (w) { return w.qid === qid; });
  if (exist) {
    exist.times += 1;
    exist.lastScore = lastScore;
  } else {
    state.wrongBook.unshift({ qid: qid, times: 1, lastScore: lastScore, addedAt: Date.now() });
  }
}

function paperScore(paper) {
  let got = 0, max = 0;
  paper.items.forEach(function (it) { got += (it.score || 0); max += it.max; });
  return { got: got, max: max, pct: max ? Math.round(got / max * 100) : 0 };
}

/* ==================== 刷题流程（按学科组卷） ==================== */

function startPractice(subjectId) {
  const qs = questionsOfSubject(subjectId);
  if (!qs.length) { toast('该学科暂无题目'); return; }
  state.draftPaper = {
    subjectId: subjectId,
    questionIds: qs.map(function (q) { return q.id; }),
    answers: {}
  };
  go('#/practice/run/' + subjectId);
}

function submitPaper() {
  const draft = state.draftPaper;
  if (!draft) return;
  const qs = draft.questionIds.map(function (id) { return byId(DB.questions, id); });
  const items = qs.map(function (q) { return gradeQuestion(q, draft.answers[q.id]); });

  // 客观题答错立即进错题本
  items.forEach(function (it) {
    if (it.type !== 'short' && it.correct === false) addWrong(it.qid, it.score);
  });

  const paper = {
    id: 'p' + Date.now(),
    subjectId: draft.subjectId,
    at: Date.now(),
    items: items,
    shortPending: items.some(function (it) { return it.type === 'short'; })
  };
  state.papers.unshift(paper);
  state.draftPaper = null;
  saveState();
  go('#/paper/' + paper.id);

  if (paper.shortPending) {
    setTimeout(function () { finishShortGrading(paper.id); }, 1600);
  }
}

function finishShortGrading(paperId) {
  const paper = byId(state.papers, paperId);
  if (!paper) return;
  paper.items.forEach(function (it) {
    if (it.type !== 'short' || !it.pending) return;
    const q = byId(DB.questions, it.qid);
    const text = (it.myAnswer || '').trim();
    let rate = 0;
    if (text.length > 0) {
      const refLen = Math.max((q && q.answer ? q.answer.length : 40), 24);
      rate = Math.min(text.length / refLen, 1);
      rate = 0.35 + 0.65 * rate;
      rate = rate * (0.9 + Math.random() * 0.15);
    }
    it.score = Math.min(Math.round(rate * it.max), it.max);
    it.pending = false;
    it.comment = shortComment(it.score, it.max);
    // 简答题不进入错题本
  });
  paper.shortPending = false;
  saveState();
  render();
}

/* ==================== AI 面试流程 ==================== */

let ivTimer = null;
let ivDelay = null;

function clearInterviewTimers() {
  if (ivTimer) { clearInterval(ivTimer); ivTimer = null; }
  if (ivDelay) { clearTimeout(ivDelay); ivDelay = null; }
}

function startInterview(subjectId) {
  if (state.interviewUsedToday >= 3) {
    toast('今日面试次数已用完（每日 3 次）');
    return;
  }
  // 资料库召回：原型中以“已切分片段”模拟 RRF 混合检索的召回结果
  const pool = shuffle(interviewQuestionsOfSubject(subjectId)).slice(0, 5);
  if (pool.length < 5) { toast('该学科资料库切片不足 5 条，无法发起面试'); return; }

  state.interviewUsedToday += 1;
  state.draftInterview = {
    subjectId: subjectId,
    source: 'subject',
    questions: pool,
    index: 0,
    phase: 'asking',
    mode: null,
    typed: '',
    followUsed: false,
    followText: '',
    items: [],
    remaining: 15 * 60
  };
  saveState();
  go('#/interview/live');
  ivDelay = setTimeout(function () {
    const d = state.draftInterview;
    if (!d) return;
    d.phase = 'ready';
    render();
  }, 1400);
}

function ivCurrentQuestion() {
  const d = state.draftInterview;
  return d.questions[d.index];
}

function ivSourceName(s) {
  if (!s) return '';
  if (s.project) return '简历 · ' + s.project;
  if (s.project === '') return '简历 · 技能与意向';
  return docName(s.docId);
}

/* 简历面试：题目全部来自简历解析片段，重点覆盖项目经历 */
function startResumeInterview() {
  if (!state.resume || state.resume.status !== 'ready') { toast('请先上传并解析简历'); return; }
  if (state.interviewUsedToday >= 3) { toast('今日面试次数已用完（每日 3 次）'); return; }

  const projectPart = shuffle(DB.resumeSnippets.filter(function (s) { return s.project; })).slice(0, 3);
  const otherPart = shuffle(DB.resumeSnippets.filter(function (s) { return !s.project; })).slice(0, 2);
  const pool = shuffle(projectPart.concat(otherPart));

  state.interviewUsedToday += 1;
  state.draftInterview = {
    subjectId: null,
    source: 'resume',
    resumeFile: state.resume.fileName,
    questions: pool,
    index: 0,
    phase: 'asking',
    mode: null,
    typed: '',
    followUsed: false,
    followText: '',
    items: [],
    remaining: 15 * 60
  };
  saveState();
  go('#/interview/live');
  ivDelay = setTimeout(function () {
    const d = state.draftInterview;
    if (!d) return;
    d.phase = 'ready';
    render();
  }, 1400);
}

function ivAnswerDone() {
  const d = state.draftInterview;
  if (!d) return;
  const mode = d.mode || 'voice';
  const typed = (d.typed || '').trim();
  if (mode === 'text' && !typed) { toast('请先输入作答内容'); return; }

  d.phase = 'judging';
  render();
  ivDelay = setTimeout(function () {
    const d2 = state.draftInterview;
    if (!d2) return;
    const s = ivCurrentQuestion();
    let score;
    if (mode === 'text') {
      if (typed.length >= 60) score = 78 + Math.floor(Math.random() * 16);
      else if (typed.length >= 20) score = 60 + Math.floor(Math.random() * 16);
      else score = 40 + Math.floor(Math.random() * 18);
    } else {
      score = d2.followUsed ? 70 + Math.floor(Math.random() * 26) : 62 + Math.floor(Math.random() * 30);
    }
    d2.items.push({
      qid: s.id,
      title: s.question,
      docName: ivSourceName(s),
      mode: mode,
      answer: mode === 'text' ? typed : '',
      follow: d2.followUsed,
      followText: d2.followUsed ? d2.followText : '',
      score: score,
      comment: ivComment(score)
    });
    d2.phase = 'answered';
    d2.mode = null;
    d2.typed = '';
    render();
  }, 1400);
}

function ivComment(score) {
  if (score >= 85) return '回答结构完整，能结合项目说明取舍，追问时补充到位。';
  if (score >= 75) return '要点基本覆盖，但缺少具体数据或案例支撑，追问部分略显含糊。';
  if (score >= 60) return '方向正确、深度不足，关键词提到了但没有展开。';
  return '未命中核心要点，建议回看对应课程后重练。';
}

function ivNext() {
  const d = state.draftInterview;
  if (!d) return;
  if (d.index >= d.questions.length - 1) { endInterview(false); return; }
  d.index += 1;
  d.phase = 'asking';
  d.followUsed = false;
  d.followText = '';
  d.mode = null;
  d.typed = '';
  render();
  ivDelay = setTimeout(function () {
    const d2 = state.draftInterview;
    if (!d2) return;
    d2.phase = 'ready';
    render();
  }, 1400);
}

function ivFollow() {
  const d = state.draftInterview;
  if (!d || d.followUsed) return;
  d.followUsed = true;
  d.followText = '你刚提到的这一点，如果数据量涨到十倍，你觉得最先出问题的地方是哪里？为什么？';
  d.phase = 'ready';
  d.mode = null;
  d.typed = '';
  render();
}

function endInterview(autoEnd) {
  const d = state.draftInterview;
  if (!d) return;
  clearInterviewTimers();

  for (let i = d.items.length; i < d.questions.length; i++) {
    d.items.push({
      qid: d.questions[i].id,
      title: d.questions[i].question,
      docName: ivSourceName(d.questions[i]),
      mode: '-',
      answer: '',
      follow: false,
      followText: '',
      score: 0,
      comment: '本题未作答。'
    });
  }

  let sum = 0;
  d.items.forEach(function (it) { sum += it.score; });
  const record = {
    id: 'iv' + Date.now(),
    subjectId: d.subjectId,
    source: d.source || 'subject',
    resumeFile: d.resumeFile || null,
    at: Date.now(),
    items: d.items,
    total: Math.round(sum / d.items.length)
  };
  state.interviews.unshift(record);
  state.draftInterview = null;
  saveState();
  toast(autoEnd ? '面试时长已到，已自动生成报告' : '面试结束，报告已生成');
  go('#/interview/report/' + record.id);
}

/* ==================== 路由 ==================== */

const routes = [
  { re: /^#\/login$/, view: 'login' },
  { re: /^#\/home$/, view: 'home' },
  { re: /^#\/subject\/([\w-]+)$/, view: 'subject' },
  { re: /^#\/practice$/, view: 'practice' },
  { re: /^#\/practice\/run\/([\w-]+)$/, view: 'practiceRun' },
  { re: /^#\/paper\/([\w-]+)$/, view: 'paper' },
  { re: /^#\/wrong-book$/, view: 'wrongBook' },
  { re: /^#\/interview$/, view: 'interview' },
  { re: /^#\/resume-interview$/, view: 'resumeInterview' },
  { re: /^#\/interview\/live$/, view: 'interviewLive' },
  { re: /^#\/interview\/report\/([\w-]+)$/, view: 'interviewReport' },
  { re: /^#\/records\/learning$/, view: 'recordsLearning' },
  { re: /^#\/records\/interview$/, view: 'recordsInterview' },
  { re: /^#\/profile$/, view: 'profile' },
  { re: /^#\/admin\/dashboard$/, view: 'admin-dashboard', admin: true },
  { re: /^#\/admin\/content$/, view: 'admin-content', admin: true },
  { re: /^#\/admin\/questions$/, view: 'admin-questions', admin: true },
  { re: /^#\/admin\/interview$/, view: 'admin-interview', admin: true },
  { re: /^#\/admin\/students$/, view: 'admin-students', admin: true },
  { re: /^#\/admin\/users$/, view: 'admin-users', admin: true },
  { re: /^#\/admin\/logs$/, view: 'admin-logs', admin: true }
];

function currentRoute() {
  const fallback = APP_SCOPE === 'admin' ? '#/admin/dashboard' : '#/login';
  const hash = location.hash || fallback;

  for (let i = 0; i < routes.length; i++) {
    // 两个入口页面各自只解析自己那一侧的路由
    if (APP_SCOPE === 'student' && routes[i].admin) continue;
    if (APP_SCOPE === 'admin' && !routes[i].admin) continue;

    const m = hash.match(routes[i].re);
    if (m) return { view: routes[i].view, params: m.slice(1), admin: !!routes[i].admin };
  }
  return { view: 'notfound', params: [], admin: false };
}

function render() {
  // 学员端误入后台路由：整页跳到管理端入口（两端是两个页面）
  if (APP_SCOPE === 'student' && String(location.hash || '').indexOf('#/admin') === 0) {
    location.href = 'admin.html' + location.hash;
    return;
  }

  const r = currentRoute();

  // ========== 管理端入口（admin.html）：独立页面，未登录就显示后台登录 ==========
  if (APP_SCOPE === 'admin') {
    if (!state.user || !state.user.isAdmin) {
      document.getElementById('app').innerHTML = ViewAdminLogin();
      return;
    }
    if (!r.admin) { go('#/admin/dashboard'); return; }

    document.getElementById('app').innerHTML = adminShell(r.view);
    if (typeof AdminViews[r.view] === 'function') {
      const main = document.getElementById('admin-body');
      if (main) main.innerHTML = AdminViews[r.view]();
    }
    playPageEnter(document.querySelector('.admin-body'), 'admin:' + r.view);
    mountCountUp();
    return;
  }

  // ========== 学员端入口（index.html） ==========
  if (r.view === 'login') {
    if (state.user) { go(state.user.isAdmin ? '#/admin/dashboard' : '#/home'); return; }
    document.getElementById('app').innerHTML = ViewLogin();
    return;
  }
  if (!state.user) { go('#/login'); return; }

  document.getElementById('app').innerHTML = cShell(r.view, r.params);
  window.scrollTo(0, 0);
  playPageEnter(document.querySelector('.container'), r.view);
  if (r.view === 'interviewLive') mountInterviewTimer();
  mountCountUp();
}

/* 只有切换到新页面时才播放入场动画，页面内重渲染不重复播 */
let lastRenderedView = null;

function playPageEnter(root, key) {
  if (!root || key === lastRenderedView) return;
  lastRenderedView = key;
  root.classList.add('page-enter');
}

/* 统计数字滚动增长 */
function mountCountUp() {
  const nodes = document.querySelectorAll('[data-count]');
  Array.prototype.forEach.call(nodes, function (el) {
    const target = Number(el.getAttribute('data-count'));
    if (!isFinite(target) || target <= 0) return;
    let current = 0;
    const step = Math.max(target / 18, 1);
    const timer = setInterval(function () {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      el.textContent = Math.round(current);
    }, 28);
  });
}

/* ==================== C 端框架 ==================== */

const cNav = [
  { hash: '#/home', label: '首页', key: 'home' },
  { hash: '#/practice', label: '刷题', key: 'practice' },
  { hash: '#/interview', label: 'AI 面试', key: 'interview' },
  { hash: '#/resume-interview', label: '简历面试', key: 'resumeInterview' },
  { hash: '#/wrong-book', label: '错题本', key: 'wrongBook' },
  { hash: '#/records/learning', label: '学习记录', key: 'recordsLearning' },
  { hash: '#/profile', label: '我的', key: 'profile' }
];

/* 面试进行中 / 报告页：判断这一场是不是简历面试，用于高亮对应菜单 */
function isResumeInterviewView(view, params) {
  if (view === 'interviewLive') {
    return !!(state.draftInterview && state.draftInterview.source === 'resume');
  }
  if (view === 'interviewReport') {
    const rec = byId(state.interviews, params[0]);
    return !!(rec && rec.source === 'resume');
  }
  return false;
}

function cShell(view, params) {
  const navHtml = cNav.map(function (item) {
    let active = view === item.key;
    if (view === 'recordsInterview' && item.key === 'recordsLearning') active = true;
    if (view === 'subject' && item.key === 'home') active = true;
    if (view === 'paper' && item.key === 'practice') active = true;
    if (view === 'interviewLive' || view === 'interviewReport') {
      const resume = isResumeInterviewView(view, params);
      if (resume && item.key === 'resumeInterview') active = true;
      if (!resume && item.key === 'interview') active = true;
    }
    return '<a href="' + item.hash + '" class="' + (active ? 'active' : '') + '">' + item.label + '</a>';
  }).join('');

  const user = state.user || {};
  const initial = (user.nickname || user.phone || '学').slice(0, 1);

  return '' +
    '<div class="topbar"><div class="topbar-inner">' +
      '<a class="brand" href="#/home"><span class="logo">枢</span><span class="name">云枢智学</span></a>' +
      '<nav class="nav">' + navHtml + '</nav>' +
      '<div class="topbar-right">' +
        (user.isAdmin
          ? '<a class="btn btn-sm" href="admin.html">进入管理后台</a>'
          : '<span class="tag tag-indigo">学员端</span>') +
        '<div class="avatar">' + esc(initial) + '</div>' +
        '<button class="btn btn-sm btn-ghost" data-act="logout">退出</button>' +
      '</div>' +
    '</div></div>' +
    '<div class="container">' + CViews[view](params) + '</div>' +
    '<div class="proto-badge">交互原型 · 数据为本地模拟</div>';
}

/* ==================== 登录页 ==================== */

let loginTab = 'login';
let lastPhone = '';

const LOGIN_TABS = [
  { key: 'login', label: '登录' },
  { key: 'register', label: '注册' },
  { key: 'admin', label: '后台' }
];

function loginTitle(tab) {
  if (tab === 'register') return '创建学员账号';
  if (tab === 'admin') return '管理后台登录';
  return '欢迎回来';
}

function loginSubtitle(tab) {
  if (tab === 'admin') return '后台仅供内部运营与超管使用';
  return '注册需要手机号短信验证，登录使用手机号 + 密码';
}

/* 三个面板的表单各自独立，切 tab 时只替换表单区域，不整页重渲染 */
function loginPanelHtml(tab) {
  if (tab === 'register') {
    return '' +
      '<div class="field"><label>手机号</label><input class="input" id="reg-phone" placeholder="请输入 11 位手机号"></div>' +
      '<div class="field"><label>短信验证码</label><div class="input-group">' +
        '<input class="input" id="reg-code" placeholder="请输入验证码">' +
        '<button class="btn" id="reg-code-btn" data-act="send-code">获取验证码</button>' +
      '</div></div>' +
      '<div class="field"><label>设置密码</label><input class="input" id="reg-pwd" type="password" placeholder="至少 6 位"></div>' +
      '<div class="field"><label>确认密码</label><input class="input" id="reg-pwd2" type="password" placeholder="再次输入密码"></div>' +
      '<button class="btn btn-primary btn-block mt8" data-act="do-register">注册并登录</button>' +
      '<p class="small muted mt16">原型说明：点击"获取验证码"后输入任意 4 位数字即可完成注册。</p>';
  }
  if (tab === 'admin') {
    return '' +
      '<div class="field"><label>管理员账号</label><input class="input" id="admin-user" placeholder="admin"></div>' +
      '<div class="field"><label>密码</label><input class="input" id="admin-pwd" type="password" placeholder="任意密码"></div>' +
      '<button class="btn btn-primary btn-block mt8" data-act="do-admin-login">进入管理后台</button>' +
      '<p class="small muted mt16">原型说明：角色固定为超管 / 运营两种。</p>';
  }
  return '' +
    '<div class="field"><label>手机号</label><input class="input" id="login-phone" placeholder="请输入 11 位手机号" value="' + esc(lastPhone) + '"></div>' +
    '<div class="field"><label>密码</label><input class="input" id="login-pwd" type="password" placeholder="请输入密码"></div>' +
    '<button class="btn btn-primary btn-block mt8" data-act="do-login">登录</button>' +
    '<p class="small muted mt16">原型说明：任意手机号 + 任意密码即可登录；登录态保存在浏览器本地。</p>';
}

function ViewLogin() {
  const index = Math.max(LOGIN_TABS.findIndex(function (t) { return t.key === loginTab; }), 0);

  return '' +
    '<div class="login-page">' +
      '<div class="login-brand">' +
        '<div class="login-logo"><span class="dot">枢</span>云枢智学</div>' +
        '<div>' +
          '<h1>学、练、面<br>一条闭环走完</h1>' +
          '<p>沿课程节点图逐课学习并点亮，按学科整卷刷题，用 AI 语音面试检验掌握程度——不用再纠结"学完到底会不会"。</p>' +
          '<ul class="login-points">' +
            '<li><b>学</b><span>学科 → 课程节点图，B 站课程一键直达</span></li>' +
            '<li><b>练</b><span>判断 / 单选 / 多选 / 简答，整卷提交出结果</span></li>' +
            '<li><b>面</b><span>语音 / 打字双通道 AI 面试，5 题 15 分钟出报告</span></li>' +
          '</ul>' +
        '</div>' +
        '<div class="login-tip">交互原型 · 仅演示交互与信息结构</div>' +
      '</div>' +
      '<div class="login-box"><div class="login-form">' +
        '<h2 id="login-title">' + loginTitle(loginTab) + '</h2>' +
        '<p class="sub" id="login-sub">' + loginSubtitle(loginTab) + '</p>' +
        '<div class="tabs tabs-slide">' +
          '<span class="tab-indicator" id="login-indicator" style="transform: translateX(' + (index * 100) + '%)"></span>' +
          LOGIN_TABS.map(function (t) {
            return '<button class="' + (t.key === loginTab ? 'active' : '') + '" data-act="login-tab" data-tab="' + t.key + '">' + t.label + '</button>';
          }).join('') +
        '</div>' +
        '<div id="login-form-body">' + loginPanelHtml(loginTab) + '</div>' +
      '</div></div>' +
    '</div>';
}

/* 管理端入口自带的后台登录页（独立页面，不复用学员端的三 tab 登录） */
function ViewAdminLogin() {
  return '' +
    '<div class="login-page">' +
      '<div class="login-brand">' +
        '<div class="login-logo"><span class="dot">枢</span>云枢智学 · 管理后台</div>' +
        '<div>' +
          '<h1>内容运营<br>与系统管理</h1>' +
          '<p>管理端与学员端是两个独立页面：这里维护学科与课程、题库、面试资料库与学员账号。</p>' +
          '<ul class="login-points">' +
            '<li><b>内容</b><span>学科 → 课程节点、学习顺序、上下架</span></li>' +
            '<li><b>题库</b><span>四类题型维护与 Excel 批量导入</span></li>' +
            '<li><b>资料</b><span>面试资料上传、切分入库、RRF 检索测试</span></li>' +
          '</ul>' +
        '</div>' +
        '<div class="login-tip">交互原型 · 仅演示交互与信息结构</div>' +
      '</div>' +
      '<div class="login-box"><div class="login-form">' +
        '<h2>后台登录</h2>' +
        '<p class="sub">仅供内部运营与超管使用</p>' +
        loginPanelHtml('admin') +
        '<p class="small muted mt16">' +
          '<a href="index.html">← 返回学员端</a>' +
        '</p>' +
      '</div></div>' +
    '</div>';
}

/* ==================== C 端页面 ==================== */

const CViews = {};

CViews.home = function () {
  const subjects = DB.subjects.filter(function (s) { return s.status; });

  const subjectCards = subjects.map(function (s) {
    const courses = coursesOfSubject(s.id).filter(function (c) { return c.status; });
    const p = subjectProgress(s.id);
    return '' +
      '<div class="card subject-card" data-act="go" data-hash="#/subject/' + s.id + '">' +
        '<div class="subject-icon">' + s.icon + '</div>' +
        '<h4>' + esc(s.name) + '</h4>' +
        '<p>' + esc(s.desc) + '</p>' +
        '<div class="subject-meta">' +
          '<span>' + courses.length + ' 个节点</span>' +
          '<span>已点亮 ' + p.done + '</span>' +
        '</div>' +
        '<div class="mt8">' + progressBar(p.rate) + '</div>' +
      '</div>';
  }).join('');

  const progressCards = subjects.map(function (s) {
    const p = subjectProgress(s.id);
    const next = nextCourse(s.id);
    return '' +
      '<div class="card card-pad">' +
        '<div class="row-between"><h4 style="margin:0;font-size:15px">' + s.icon + ' ' + esc(s.name) + '</h4>' +
          '<span class="tag tag-indigo">' + p.rate + '%</span></div>' +
        '<div class="small muted" style="margin:6px 0 10px">已点亮 ' + p.done + ' / ' + p.total + ' 个节点</div>' +
        progressBar(p.rate) +
        '<div class="row-between mt8">' +
          '<span class="small muted">' + (next ? '下一课：' + esc(next.title) : '已全部点亮 🎉') + '</span>' +
          '<button class="btn btn-sm" data-act="go" data-hash="#/subject/' + s.id + '">进入节点图</button>' +
        '</div>' +
      '</div>';
  }).join('');

  const recent = state.visits.slice(0, 3);
  const recentHtml = recent.length
    ? recent.map(function (v) {
        const c = byId(DB.courses, v.courseId);
        if (!c) return '';
        const s = byId(DB.subjects, c.subjectId);
        return '' +
          '<div class="course-row">' +
            '<div class="course-index">▶</div>' +
            '<div class="course-main"><h5>' + esc(c.title) + '</h5>' +
              '<div class="small muted">' + esc(s ? s.name : '') + ' · ' + fmtTime(v.at) + '</div></div>' +
            (courseDone(c.id) ? '<span class="tag tag-green">已点亮</span>' : '<span class="tag">未点亮</span>') +
            '<button class="btn btn-sm" data-act="go" data-hash="#/subject/' + c.subjectId + '">回到节点图</button>' +
          '</div>';
      }).join('')
    : '<div class="empty"><span class="empty-icon">📺</span>还没有学习记录，先去挑一个学科</div>';

  const first = nextCourse(subjects[0] ? subjects[0].id : '');

  return '' +
    '<div class="hero">' +
      '<div>' +
        '<h2>你好，' + esc(state.user.nickname || state.user.phone) + '</h2>' +
        '<p>学科里每个节点就是一节课，学完自己点亮；也可以直接来一场 AI 面试。</p>' +
      '</div>' +
      '<button class="btn" data-act="go" data-hash="' + (first ? '#/subject/' + subjects[0].id : '#/interview') + '">' +
        (first ? '继续学习' : '开始 AI 面试') + '</button>' +
    '</div>' +

    '<div class="page-head mt24"><h2>学习方向</h2><p>选择学科，进入它的课程节点图</p></div>' +
    '<div class="grid g3">' + subjectCards + '</div>' +

    '<div class="row-between mt24" style="margin-bottom:14px">' +
      '<h3 style="margin:0;font-size:16px">学习进度</h3>' +
      '<span class="small muted">完成率 = 已点亮节点 / 上架节点</span></div>' +
    '<div class="grid g2">' + progressCards + '</div>' +

    '<div class="row-between mt24" style="margin-bottom:14px"><h3 style="margin:0;font-size:16px">最近学习</h3></div>' +
    '<div class="card card-pad">' + recentHtml + '</div>';
};

/* 学科页 = 课程节点图 */
CViews.subject = function (params) {
  const s = byId(DB.subjects, params[0]);
  if (!s) return '<div class="empty">学科不存在</div>';

  const all = coursesOfSubject(s.id);
  const courses = all.filter(function (c) { return c.status; });
  const p = subjectProgress(s.id);
  const next = nextCourse(s.id);
  const qCount = questionsOfSubject(s.id).length;

  const nodes = courses.map(function (c, i) {
    const done = courseDone(c.id);
    const isNext = next && next.id === c.id;
    return '' +
      '<div class="tl-item ' + (done ? 'done' : '') + ' ' + (isNext ? 'active' : '') + '">' +
        '<div class="tl-dot"></div>' +
        '<div class="tl-box">' +
          '<div class="row-between">' +
            '<h5>' +
              '<span class="node-index">' + (i + 1) + '</span>' +
              esc(c.title) +
              (done ? ' <span class="tag tag-green">已点亮</span>' : '') +
              (isNext ? ' <span class="tag tag-indigo">推荐下一课</span>' : '') +
            '</h5>' +
            '<span class="small muted">' + esc(c.duration) + '</span>' +
          '</div>' +
          '<p class="small muted" style="margin:4px 0 10px">' + esc(c.desc || '') + '</p>' +
          '<div class="row">' +
            '<button class="btn btn-sm" data-act="open-course" data-id="' + c.id + '">去 B 站观看</button>' +
            '<button class="btn btn-sm ' + (done ? '' : 'btn-primary') + '" data-act="toggle-course" data-id="' + c.id + '">' +
              (done ? '取消点亮' : '点亮节点') + '</button>' +
          '</div>' +
        '</div>' +
      '</div>';
  }).join('');

  return '' +
    '<div class="breadcrumb"><a href="#/home">首页</a> / ' + esc(s.name) + '</div>' +
    '<div class="page-head">' +
      '<div class="row-between">' +
        '<div><h2>' + s.icon + ' ' + esc(s.name) + '</h2><p>' + esc(s.desc) + '</p></div>' +
        '<div class="row">' +
          '<button class="btn btn-sm" data-act="go" data-hash="#/practice">去刷题</button>' +
          '<button class="btn btn-sm btn-primary" data-act="start-practice" data-id="' + s.id + '">随机组卷（题池 ' + qCount + ' 题）</button>' +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div class="card card-pad mt16">' +
      '<div class="row-between" style="margin-bottom:8px">' +
        '<span class="small muted">学习进度（点亮节点数 / 上架节点数）</span>' +
        '<span class="tag tag-indigo">' + p.done + ' / ' + p.total + '</span>' +
      '</div>' + progressBar(p.rate) +
    '</div>' +
    '<div class="card card-pad mt16">' +
      (courses.length ? '<div class="timeline">' + nodes + '</div>'
        : '<div class="empty">该学科暂无上架课程</div>') +
    '</div>' +
    '<p class="small muted mt16">说明：课程视频均跳转 B 站观看，平台不采集观看时长；点亮由学员手动标记，顺序为线性推荐，不强制解锁。</p>';
};

CViews.practice = function () {
  const groups = DB.subjects.filter(function (s) { return s.status; }).map(function (s) {
    const qs = questionsOfSubject(s.id);
    const papers = state.papers.filter(function (paper) { return paper.subjectId === s.id; });
    const best = papers.length
      ? Math.max.apply(null, papers.map(function (paper) { return paperScore(paper).pct; }))
      : null;
    return '' +
      '<div class="course-row">' +
        '<div class="course-index">' + s.icon + '</div>' +
        '<div class="course-main"><h5>' + esc(s.name) + '</h5>' +
          '<div class="small muted">题池 ' + qs.length + ' 题' +
          (best === null ? '' : ' · 历史最高 ' + best + ' 分') + '</div></div>' +
        (qs.length
          ? '<button class="btn btn-sm btn-primary" data-act="start-practice" data-id="' + s.id + '">开始刷题（题池 ' + qs.length + ' 题）</button>'
          : '') +
      '</div>';
  }).join('');

  return '<div class="page-head"><h2>刷题自测</h2>' +
    '<p>选择学科：按题型比例随机抽 20 题组卷（题池不足时按实际题量），全部作答后一次性提交</p></div>' +
    '<div class="card card-pad"><div class="row wrap">' +
      '<span class="tag tag-indigo">判断题</span><span class="tag tag-indigo">单选题</span>' +
      '<span class="tag tag-indigo">多选题</span><span class="tag tag-indigo">简答题（AI 判分）</span>' +
      '<span class="small muted">简答题由 AI 对照参考答案判分</span>' +
    '</div></div>' +
    '<div class="card mt16"><div class="card-head"><h3>学科题池</h3>' +
      '<span class="small muted">共 ' + DB.subjects.length + ' 个学科</span></div>' +
      '<div class="card-body">' + groups + '</div></div>';
};

CViews.practiceRun = function (params) {
  const draft = state.draftPaper;
  if (!draft || draft.subjectId !== params[0]) {
    return '<div class="empty">没有进行中的答卷，请先选择学科</div>' +
      '<div style="text-align:center"><button class="btn btn-primary" data-act="go" data-hash="#/practice">去选择学科</button></div>';
  }
  const s = byId(DB.subjects, draft.subjectId);
  const qs = draft.questionIds.map(function (id) { return byId(DB.questions, id); });
  const answeredCount = qs.filter(function (q) { return isAnswered(draft, q); }).length;
  const total = qs.length;

  const qHtml = qs.map(function (q, i) {
    const opts = optionList(q).map(function (o) {
      const chosen = isChosen(draft, q, o.k);
      return '<div class="option ' + (chosen ? 'selected' : '') + '" data-act="choose-option" data-qid="' + q.id + '" data-key="' + o.k + '">' +
        '<span class="key">' + o.k + '</span><span>' + esc(o.t) + '</span></div>';
    }).join('');

    const body = q.type === 'short'
      ? '<textarea class="textarea" data-input="short" data-qid="' + q.id + '" placeholder="请输入作答内容">' +
        esc(draft.answers[q.id] || '') + '</textarea>' +
        '<div class="small muted mt8">本题 ' + q.score + ' 分 · 提交后由 AI 对照参考答案判分</div>'
      : opts;

    return '<div class="qcard card" id="q-' + i + '">' +
      '<div class="qhead"><div class="qno">' + (i + 1) + '</div>' +
        '<div><div class="qtitle">' + esc(q.title) + '</div>' +
        '<div class="small muted mt8">' + TYPE_LABEL[q.type] + ' · ' + q.difficulty + ' · ' + q.score + ' 分</div></div></div>' +
      body + '</div>';
  }).join('');

  const sheet = qs.map(function (q, i) {
    const done = isAnswered(draft, q);
    return '<div class="sheet-item ' + (done ? 'done' : '') + '" data-sheet="' + q.id + '" ' +
      'data-act="jump-q" data-index="' + i + '">' + (i + 1) + '</div>';
  }).join('');

  return '' +
    '<div class="breadcrumb"><a href="#/practice">刷题自测</a> / ' + esc(s.name) + '</div>' +
    '<div class="page-head"><h2>' + esc(s.name) + ' · 整卷练习</h2>' +
      '<p>共 ' + total + ' 题，已作答 <b id="count-top">' + answeredCount + '</b> 题；全部答完后一次性提交</p></div>' +
    '<div class="practice-layout">' +
      '<div><div>' + qHtml + '</div>' +
        '<div class="card card-pad row-between">' +
          '<span class="small muted">已作答 <b id="count-bottom">' + answeredCount + '</b> / ' + total + '</span>' +
          '<button class="btn btn-primary" data-act="submit-paper">提交试卷</button>' +
        '</div></div>' +
      '<div class="answer-sheet card card-pad">' +
        '<div class="row-between" style="margin-bottom:12px"><b>答题卡</b>' +
          '<span class="small muted"><b id="count-sheet">' + answeredCount + '</b>/' + total + '</span></div>' +
        '<div class="sheet-grid">' + sheet + '</div>' +
        '<p class="small muted mt16">提交后客观题立即出结果，简答题由 AI 对照参考答案判分。</p>' +
      '</div>' +
    '</div>';
};

/* 选项变更后只更新相关 DOM，避免整页重渲染导致滚动位置丢失 */
function refreshPracticeDom() {
  const draft = state.draftPaper;
  if (!draft) return;
  const qs = draft.questionIds.map(function (id) { return byId(DB.questions, id); });

  qs.forEach(function (q) {
    const nodes = document.querySelectorAll('[data-act="choose-option"][data-qid="' + q.id + '"]');
    Array.prototype.forEach.call(nodes, function (node) {
      const key = node.getAttribute('data-key');
      if (isChosen(draft, q, key)) node.classList.add('selected');
      else node.classList.remove('selected');
    });
    const sheetItem = document.querySelector('[data-sheet="' + q.id + '"]');
    if (sheetItem) {
      if (isAnswered(draft, q)) sheetItem.classList.add('done');
      else sheetItem.classList.remove('done');
    }
  });

  const answered = qs.filter(function (q) { return isAnswered(draft, q); }).length;
  ['count-top', 'count-bottom', 'count-sheet'].forEach(function (id) {
    const el = document.getElementById(id);
    if (el) el.textContent = answered;
  });
}

function isChosen(draft, q, key) {
  const a = draft.answers[q.id];
  if (q.type === 'multi') return Array.isArray(a) && a.indexOf(key) > -1;
  return a === key;
}

function isAnswered(draft, q) {
  const a = draft.answers[q.id];
  if (q.type === 'multi') return Array.isArray(a) && a.length > 0;
  if (q.type === 'short') return typeof a === 'string' && a.trim().length > 0;
  return !!a;
}

CViews.paper = function (params) {
  const paper = byId(state.papers, params[0]);
  if (!paper) return '<div class="empty">答卷不存在</div>';
  const s = byId(DB.subjects, paper.subjectId);
  const score = paperScore(paper);

  const head = '' +
    '<div class="card card-pad row" style="gap:26px">' +
      '<div class="score-ring" style="--pct:' + score.pct + '%"><div class="inner" data-count="' + score.pct + '">0</div></div>' +
      '<div style="flex:1">' +
        '<h3 style="margin:0 0 6px">' + (paper.shortPending ? 'AI 正在判分…' : '本次得分 ' + score.got + ' / ' + score.max) + '</h3>' +
        '<p class="muted" style="margin:0">' + esc(s ? s.name : '') + ' · ' + fmtTime(paper.at) + ' · ' +
          paper.items.length + ' 题</p>' +
        '<div class="row mt16">' +
          '<button class="btn btn-sm" data-act="go" data-hash="#/practice">再选一个学科</button>' +
          '<button class="btn btn-sm btn-primary" data-act="start-practice" data-id="' + paper.subjectId + '">重做本学科</button>' +
          '<button class="btn btn-sm" data-act="go" data-hash="#/wrong-book">查看错题本</button>' +
        '</div>' +
      '</div>' +
    '</div>';

  const items = paper.items.map(function (it, i) {
    const q = byId(DB.questions, it.qid);
    const pending = it.pending;
    let mark = '';
    if (!pending && it.type !== 'short') {
      mark = it.correct ? '<span class="tag tag-green">正确</span>' : '<span class="tag tag-red">错误</span>';
    } else if (!pending) {
      mark = '<span class="tag ' + (it.score / it.max >= 0.6 ? 'tag-green' : 'tag-orange') + '">' + it.score + ' / ' + it.max + ' 分</span>';
    } else {
      mark = '<span class="tag tag-indigo tag-pending">AI 判分中</span>';
    }

    const detail = it.type === 'short'
      ? (pending
          ? '<div class="small muted">AI 判分意见</div><div class="small" style="margin-top:4px">正在对照参考答案评估作答要点…</div>'
          : '<div class="small muted">参考答案</div>' +
            '<div class="small" style="margin-top:4px;white-space:pre-wrap">' + esc(q.answer || '') + '</div>' +
            '<div class="small muted" style="margin-top:10px">AI 判分意见</div>' +
            '<div class="small" style="margin-top:4px">' + esc(it.comment) + '</div>' +
            (q.analysis ? '<div class="small muted" style="margin-top:8px">评分要点：' + esc(q.analysis) + '</div>' : ''))
      : '<div class="small muted">' + (it.correct ? '回答正确' : '解析') + '</div>' +
        '<div class="small" style="margin-top:4px">' + esc(it.comment) + '</div>' +
        (q.analysis ? '<div class="small muted" style="margin-top:6px">' + esc(q.analysis) + '</div>' : '');

    return '' +
      '<div class="qcard card">' +
        '<div class="qhead"><div class="qno">' + (i + 1) + '</div>' +
          '<div style="flex:1"><div class="qtitle">' + esc(q.title) + '</div>' +
          '<div class="small muted mt8">' + TYPE_LABEL[it.type] + ' · 我的作答：' +
            esc(displayAnswer(it)) + '</div></div>' +
          '<div>' + mark + '</div>' +
        '</div>' +
        '<div class="card-pad" style="background:#fafbff;border-radius:10px;padding:12px 14px">' +
          detail +
        '</div>' +
      '</div>';
  }).join('');

  return '<div class="breadcrumb"><a href="#/practice">刷题自测</a> / 答卷结果</div>' + head +
    '<div class="mt24">' + items + '</div>';
};

/* 错题重做：先选答案，点"确定"后才判定并展示结果，再点"确定"关闭 */
let retryState = null;

function openRetryModal(qid) {
  const q = byId(DB.questions, qid);
  retryState = { qid: qid, picked: q && q.type === 'multi' ? [] : '', judged: false };
  paintRetryModal();
}

function retryIsPicked(key) {
  if (!retryState) return false;
  if (Array.isArray(retryState.picked)) return retryState.picked.indexOf(key) > -1;
  return retryState.picked === key;
}

function retryIsCorrect(q) {
  if (q.type === 'multi') {
    const mine = retryState.picked.slice().sort().join('');
    return mine === q.answer.slice().sort().join('');
  }
  return retryState.picked === q.answer;
}

function paintRetryModal() {
  if (!retryState) return;
  const q = byId(DB.questions, retryState.qid);
  if (!q) return;
  const judged = retryState.judged;
  const multi = q.type === 'multi';

  let body = '<div style="margin-bottom:12px">' + esc(q.title) + '</div>';
  if (multi) body += '<p class="small muted" style="margin-top:-4px">多选题，可选择多个选项</p>';

  body += optionList(q).map(function (o) {
    let cls = '';
    if (judged) {
      const isRight = multi ? q.answer.indexOf(o.k) > -1 : o.k === q.answer;
      if (isRight) cls = 'is-correct';
      else if (retryIsPicked(o.k)) cls = 'is-wrong';
    } else if (retryIsPicked(o.k)) {
      cls = 'selected';
    }
    return '<div class="option ' + cls + '" data-act="retry-pick" data-key="' + o.k + '">' +
      '<span class="key">' + o.k + '</span><span>' + esc(o.t) + '</span></div>';
  }).join('');

  if (judged) {
    const ok = retryIsCorrect(q);
    body += '<div class="mt16" style="padding:12px 14px;border-radius:10px;background:' +
      (ok ? 'var(--ok-light)' : 'var(--err-light)') + '">' +
      '<b style="color:' + (ok ? 'var(--ok)' : 'var(--err)') + '">' + (ok ? '回答正确，已从错题本移出' : '回答错误，仍保留在错题本') + '</b>' +
      '<div class="small" style="margin-top:6px">正确答案：' + esc(answerText(q)) + '</div>' +
      (q.analysis ? '<div class="small muted" style="margin-top:6px">解析：' + esc(q.analysis) + '</div>' : '') +
      '</div>';
  }

  document.getElementById('modal-root').innerHTML =
    '<div class="modal-mask" data-act="modal-close-bg">' +
      '<div class="modal">' +
        '<div class="modal-head">重做错题</div>' +
        '<div class="modal-body">' + body + '</div>' +
        '<div class="modal-foot">' +
          '<button class="btn btn-primary" data-act="retry-confirm">确定</button>' +
        '</div>' +
      '</div>' +
    '</div>';
}

CViews.wrongBook = function () {
  // 错题本只收客观题（判断题 / 单选题 / 多选题），简答题不进错题本
  const list = state.wrongBook.filter(function (w) {
    const q = byId(DB.questions, w.qid);
    return q && q.type !== 'short';
  });

  const rows = list.map(function (w) {
    const q = byId(DB.questions, w.qid);
    const s = byId(DB.subjects, q.subjectId);
    return '' +
      '<div class="course-row">' +
        '<div class="course-index">' + TYPE_LABEL[q.type].slice(0, 2) + '</div>' +
        '<div class="course-main">' +
          '<h5>' + esc(q.title) + '</h5>' +
          '<div class="small muted">' + TYPE_LABEL[q.type] + ' · ' + esc(s ? s.name : '') +
            ' · 错误 ' + w.times + ' 次</div>' +
        '</div>' +
        '<button class="btn btn-sm" data-act="retry-wrong" data-qid="' + w.qid + '">重做</button>' +
        '<button class="btn btn-sm btn-danger" data-act="remove-wrong" data-qid="' + w.qid + '">移除</button>' +
      '</div>';
  }).join('');

  return '' +
    '<div class="page-head"><h2>错题本</h2>' +
      '<p>只收录客观题（判断 / 单选 / 多选）；重做答对后自动移出，简答题不进入错题本</p></div>' +
    '<div class="card mt16"><div class="card-head"><h3>客观错题（' + list.length + '）</h3>' +
      '<span class="small muted">重做答对后自动移出</span></div>' +
      '<div class="card-body">' +
        (list.length ? rows : '<div class="empty"><span class="empty-icon">✅</span>暂无错题</div>') +
      '</div></div>';
};

/* 简历卡片：未上传 / 处理中 / 已就绪 三种状态 */
function resumeCard() {
  const r = state.resume;

  if (!r) {
    return '<div class="card card-pad">' +
      '<div class="row-between">' +
        '<div><h4 style="margin:0 0 4px">上传简历</h4>' +
          '<span class="small muted">仅支持 PDF，单份不超过 10 MB；文件存入 OSS，仅本人可见</span></div>' +
        '<span class="tag">未上传</span>' +
      '</div>' +
      '<div class="field mt16"><label>简历文件</label>' +
        '<input class="input" type="file" id="resume-file" accept=".pdf" style="padding:8px 10px;height:auto"></div>' +
      '<button class="btn btn-primary" data-act="resume-upload">上传并解析</button>' +
      '<p class="small muted mt8">处理流程：上传 OSS → 转 Markdown → 切分 → 向量化入库 → 生成面试范围</p>' +
      '</div>';
  }

  if (r.status !== 'ready') {
    const stepIndex = r.status === 'uploading' ? 0 : 1;
    const steps = ['上传至 OSS', '解析成 Markdown', '切分并向量化'];
    const list = steps.map(function (t, i) {
      const done = i < stepIndex;
      const running = i === stepIndex;
      return '<div class="row" style="gap:8px;padding:6px 0">' +
        '<span class="tag ' + (done ? 'tag-green' : running ? 'tag-indigo' : '') + '">' +
          (done ? '已完成' : running ? '进行中' : '等待') + '</span>' +
        '<span class="small">' + esc(t) + '</span>' +
        '</div>';
    }).join('');

    return '<div class="card card-pad">' +
      '<div class="row-between">' +
        '<div><h4 style="margin:0 0 4px">' + esc(r.fileName) + '</h4>' +
          '<span class="small muted">' + esc(r.size || '') + ' · 正在处理，请稍候</span></div>' +
        '<span class="tag tag-indigo">处理中</span>' +
      '</div>' +
      '<div class="mt16">' + list + '</div>' +
      '</div>';
  }

  const chips = DB.resumeProjects.map(function (p) {
    return '<span class="tag tag-indigo">' + esc(p.name) + ' · ' + esc(p.stack) + '</span>';
  }).join('');

  return '<div class="card card-pad">' +
    '<div class="row-between">' +
      '<div><h4 style="margin:0 0 4px">' + esc(r.fileName) + '</h4>' +
        '<span class="small muted">' + esc(r.size || '') + ' · 已存入 OSS 并完成切分 · ' + fmtTime(r.at) + '</span></div>' +
      '<span class="tag tag-green">已就绪</span>' +
    '</div>' +
    '<div class="row wrap mt16">' + chips + '</div>' +
    '<p class="small muted mt8">识别到 2 段项目经历：面试将从项目中出 3 题、技能与求职意向出 2 题。</p>' +
    '<div class="row mt16">' +
      '<button class="btn btn-primary" data-act="resume-start">开始简历面试</button>' +
      '<button class="btn" data-act="resume-reset">重新上传</button>' +
    '</div>' +
    '</div>';
}

CViews.interview = function () {
  const left = 3 - state.interviewUsedToday;
  const cards = DB.subjects.filter(function (s) { return s.status; }).map(function (s) {
    const pool = interviewQuestionsOfSubject(s.id);
    return '' +
      '<div class="card card-pad">' +
        '<div class="row-between"><div class="row">' +
          '<div class="subject-icon">' + s.icon + '</div>' +
          '<div><h4 style="margin:0">' + esc(s.name) + '</h4>' +
          '<span class="small muted">检索命中 ' + pool.length + ' 个片段</span></div>' +
        '</div></div>' +
        '<p class="small muted mt16" style="margin-bottom:14px">基于资料库做 RRF 混合检索召回片段出 5 题，语音或打字作答，每题可被追问 1 次。</p>' +
        '<button class="btn btn-primary btn-block" data-act="start-interview" data-id="' + s.id + '">开始面试</button>' +
      '</div>';
  }).join('');

  return '' +
    '<div class="page-head"><h2>AI 面试</h2><p>选择学科：从该学科资料库中检索片段生成面试题，作答支持语音与打字两种方式</p></div>' +
    '<div class="grid g2 mt16">' +
      '<div class="card stat"><div class="stat-label">今日剩余次数</div><div class="stat-num"><span data-count="' + left + '">0</span> <small>/ 3 次</small></div></div>' +
      '<div class="card stat"><div class="stat-label">单场规格</div><div class="stat-num">5 <small>题 / 15 分钟</small></div></div>' +
    '</div>' +
    '<div class="grid g3 mt16">' + cards + '</div>' +
    '<p class="small muted mt16">说明：语音作答以按钮模拟录音与转写；打字作答直接输入文本。两种方式共用同一套评分与报告。</p>';
};

/* 简历面试：独立路由，位于 AI 面试与错题本之间 */
CViews.resumeInterview = function () {
  const left = 3 - state.interviewUsedToday;
  return '' +
    '<div class="page-head"><h2>简历面试</h2>' +
      '<p>上传 PDF 简历，服务端存入 OSS 后走 RAG 流程，面试重点针对简历中的项目经历</p></div>' +
    '<div class="grid g2 mt16">' +
      '<div class="card stat"><div class="stat-label">今日剩余次数</div><div class="stat-num"><span data-count="' + left + '">0</span> <small>/ 3 次</small></div></div>' +
      '<div class="card stat"><div class="stat-label">单场规格</div><div class="stat-num">5 <small>题 / 15 分钟</small></div></div>' +
    '</div>' +
    '<div class="mt16">' + resumeCard() + '</div>' +
    '<p class="small muted mt16">说明：简历面试与学科面试共用每日 3 次上限；作答支持语音与打字，题目优先覆盖简历中的项目经历。</p>';
};

CViews.interviewLive = function () {
  const d = state.draftInterview;
  if (!d) return '<div class="empty">没有进行中的面试</div>';
  const q = ivCurrentQuestion();
  const s = byId(DB.subjects, d.subjectId);
  const isLast = d.index === d.questions.length - 1;
  const sourceTag = d.source === 'resume' ? '简历面试' : (s ? s.name : 'AI 面试');

  const askText = d.followUsed ? d.followText : q.question;
  const ghostBtn = 'style="background:rgba(255,255,255,.12);border-color:rgba(255,255,255,.2);color:#fff"';

  let center = '';
  if (d.phase === 'asking') {
    center = '<div class="ai-orb speaking">🎙</div>' +
      '<div class="iv-hint">AI 正在提问…</div>';
  } else if (d.phase === 'ready') {
    center = '<div class="ai-orb">🎙</div>' +
      '<div class="iv-question">' + esc(q.question) + '</div>' +
      (d.followUsed ? '<div class="iv-follow"><b>追问：</b>' + esc(d.followText) + '</div>' : '') +
      '<div class="iv-hint">选择作答方式：语音作答或打字作答</div>';
  } else if (d.phase === 'voice-answering') {
    center = '<div class="wave"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>' +
      '<div class="iv-question" style="font-size:15px;color:#c7cdf0">' + esc(askText) + '</div>' +
      '<div class="iv-hint">正在录音，请作答…</div>';
  } else if (d.phase === 'typing') {
    center = '<div class="iv-question" style="font-size:15px;max-width:660px">' + esc(askText) + '</div>' +
      '<textarea id="iv-text" class="textarea" data-input="interview" ' +
        'style="max-width:660px;width:100%;min-height:120px" placeholder="输入你的回答，建议分点表述">' +
        esc(d.typed || '') + '</textarea>' +
      '<div class="iv-hint">文字作答会与语音作答一起进入同一份评分报告</div>';
  } else if (d.phase === 'judging') {
    center = '<div class="ai-orb speaking">🤖</div>' +
      '<div class="iv-hint">已收到回答，AI 正在评估…</div>';
  } else {
    center = '<div class="ai-orb">✅</div>' +
      '<div class="iv-question" style="font-size:15px">本题已记录</div>' +
      '<div class="iv-hint">' + (d.mode === 'text' ? '文字作答' : '语音作答') +
        (d.followUsed ? ' · 已完成 1 次追问' : '') + '</div>';
  }

  let buttons = '';
  if (d.phase === 'ready') {
    buttons = '<button class="btn btn-light" data-act="iv-voice-start">语音作答</button>' +
      '<button class="btn" ' + ghostBtn + ' data-act="iv-type-start">打字作答</button>';
  } else if (d.phase === 'voice-answering') {
    buttons = '<button class="btn btn-light" data-act="iv-answer-done">回答完毕</button>';
  } else if (d.phase === 'typing') {
    buttons = '<button class="btn" ' + ghostBtn + ' data-act="iv-voice-start">改用语音</button>' +
      '<button class="btn btn-light" data-act="iv-text-submit">提交回答</button>';
  } else if (d.phase === 'answered') {
    if (!d.followUsed) {
      buttons += '<button class="btn" ' + ghostBtn + ' data-act="iv-follow">AI 追问（还可 1 次）</button>';
    }
    buttons += '<button class="btn btn-light" data-act="iv-next">' + (isLast ? '结束并生成报告' : '下一题') + '</button>';
  } else {
    buttons = '<button class="btn" disabled style="background:rgba(255,255,255,.08);border-color:rgba(255,255,255,.15);color:#8d97bd">请稍候…</button>';
  }

  return '' +
    '<div class="breadcrumb"><a href="' + (d.source === 'resume' ? '#/resume-interview' : '#/interview') + '">' +
      (d.source === 'resume' ? '简历面试' : 'AI 面试') + '</a> / 进行中</div>' +
    '<div class="interview-stage">' +
      '<div class="iv-top">' +
        '<div class="row"><span class="tag tag-indigo">' + esc(sourceTag) + '</span>' +
          '<span class="small" style="color:#8d97bd">第 ' + (d.index + 1) + ' / ' + d.questions.length + ' 题</span></div>' +
        '<div class="iv-timer" id="iv-timer">15:00</div>' +
      '</div>' +
      '<div class="iv-center">' + center + '</div>' +
      '<div class="iv-bottom">' + buttons + '</div>' +
    '</div>' +
    '<div class="row-between mt16">' +
      '<span class="small muted">语音 / 打字两种作答方式可逐题切换 · 单场 15 分钟，超时自动结束</span>' +
      '<button class="btn btn-sm btn-danger" data-act="iv-end">提前结束</button>' +
    '</div>';
};

function mountInterviewTimer() {
  // 只重置计时器，不能清掉提问阶段用于推进流程的延时任务
  if (ivTimer) { clearInterval(ivTimer); ivTimer = null; }
  const d = state.draftInterview;
  if (!d) return;
  updateIvTimerText(d.remaining);
  ivTimer = setInterval(function () {
    const cur = state.draftInterview;
    if (!cur) { clearInterviewTimers(); return; }
    cur.remaining -= 1;
    updateIvTimerText(cur.remaining);
    if (cur.remaining <= 0) {
      endInterview(true);
    }
  }, 1000);
}

function updateIvTimerText(seconds) {
  const el = document.getElementById('iv-timer');
  if (!el) return;
  const mm = Math.floor(Math.max(seconds, 0) / 60);
  const ss = Math.max(seconds, 0) % 60;
  el.textContent = pad(mm) + ':' + pad(ss);
}

CViews.interviewReport = function (params) {
  const rec = byId(state.interviews, params[0]);
  if (!rec) return '<div class="empty">报告不存在</div>';
  const s = byId(DB.subjects, rec.subjectId);
  const pct = rec.total;
  const title = rec.source === 'resume' ? '简历面试' : (s ? s.name : 'AI 面试');

  const items = rec.items.map(function (it, i) {
    return '' +
      '<div class="report-item">' +
        '<div class="row-between">' +
          '<h5>' + (i + 1) + '. ' + esc(it.title) + '</h5>' +
          '<span class="report-score">' + it.score + '</span>' +
        '</div>' +
        '<div class="row wrap" style="gap:6px;margin-top:6px">' +
          (it.docName ? '<span class="tag">来源：' + esc(it.docName) + '</span>' : '') +
          '<span class="tag ' + (it.mode === 'text' ? 'tag-indigo' : '') + '">' +
            (it.mode === 'text' ? '打字作答' : it.mode === 'voice' ? '语音作答' : '未作答') + '</span>' +
        '</div>' +
        (it.answer ? '<div class="small muted" style="margin-top:8px">回答：' + esc(it.answer) + '</div>' : '') +
        (it.follow ? '<div class="small muted" style="margin-top:4px">追问：' + esc(it.followText) + '</div>' : '') +
        '<div class="small" style="margin-top:6px">' + esc(it.comment) + '</div>' +
      '</div>';
  }).join('');

  return '' +
    '<div class="breadcrumb"><a href="' + (rec.source === 'resume' ? '#/resume-interview' : '#/interview') + '">' +
      (rec.source === 'resume' ? '简历面试' : 'AI 面试') + '</a> / 面试报告</div>' +
    '<div class="card card-pad row" style="gap:26px">' +
      '<div class="score-ring" style="--pct:' + pct + '%"><div class="inner" data-count="' + pct + '">0</div></div>' +
      '<div style="flex:1">' +
        '<h3 style="margin:0 0 6px">面试总分 ' + pct + ' 分</h3>' +
        '<p class="muted" style="margin:0">' + esc(title) +
          (rec.source === 'resume' && rec.resumeFile ? ' · ' + esc(rec.resumeFile) : '') +
          ' · ' + fmtTime(rec.at) + ' · 共 ' + rec.items.length + ' 题</p>' +
        '<div class="row mt16">' +
          '<button class="btn btn-sm" data-act="go" data-hash="#/records/interview">面试记录</button>' +
          '<button class="btn btn-sm btn-primary" data-act="go" data-hash="' +
            (rec.source === 'resume' ? '#/resume-interview' : '#/interview') + '">再来一场</button>' +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div class="card card-pad mt16">' +
      '<div class="row-between" style="margin-bottom:14px"><b>逐题明细与 AI 点评</b>' +
        '<span class="small muted">总分由各题得分汇总得出</span></div>' +
      items +
    '</div>';
};

CViews.recordsLearning = function () {
  const doneCourses = Object.keys(state.completedCourses).length;
  const subjectCount = DB.subjects.filter(function (s) {
    return coursesOfSubject(s.id).some(function (c) { return courseDone(c.id); });
  }).length;

  const rows = state.visits.length
    ? state.visits.map(function (v) {
        const c = byId(DB.courses, v.courseId);
        if (!c) return '';
        const s = byId(DB.subjects, c.subjectId);
        return '' +
          '<div class="course-row">' +
            '<div class="course-index">▶</div>' +
            '<div class="course-main"><h5>' + esc(c.title) + '</h5>' +
              '<div class="small muted">' + esc(s ? s.name : '') + ' · ' + fmtTime(v.at) + '</div></div>' +
            (courseDone(c.id) ? '<span class="tag tag-green">已点亮</span>' : '<span class="tag">未点亮</span>') +
            '<button class="btn btn-sm" data-act="go" data-hash="#/subject/' + c.subjectId + '">进入节点图</button>' +
          '</div>';
      }).join('')
    : '<div class="empty"><span class="empty-icon">🕘</span>暂无学习记录</div>';

  return '' +
    '<div class="page-head"><h2>学习记录</h2><p>节点访问流水 + 手动点亮状态</p></div>' +
    '<div class="grid g3 mt16">' +
      '<div class="card stat"><div class="stat-label">访问节点</div><div class="stat-num">' + state.visits.length + '</div></div>' +
      '<div class="card stat"><div class="stat-label">点亮课程</div><div class="stat-num">' + doneCourses + '</div></div>' +
      '<div class="card stat"><div class="stat-label">参与学科</div><div class="stat-num">' + subjectCount + '</div></div>' +
    '</div>' +
    '<div class="card card-pad mt16">' + rows + '</div>' +
    '<div class="row mt16"><button class="btn" data-act="go" data-hash="#/records/interview">查看面试记录 →</button></div>';
};

CViews.recordsInterview = function () {
  const rows = state.interviews.length
    ? state.interviews.map(function (rec) {
        const s = byId(DB.subjects, rec.subjectId);
        const title = rec.source === 'resume' ? '简历面试' : (s ? s.name : 'AI 面试');
        return '' +
          '<div class="course-row">' +
            '<div class="course-index">🎙</div>' +
            '<div class="course-main"><h5>' + esc(title) + ' · ' + rec.total + ' 分</h5>' +
              '<div class="small muted">' + fmtTime(rec.at) + ' · ' + rec.items.length + ' 题' +
                (rec.source === 'resume' && rec.resumeFile ? ' · ' + esc(rec.resumeFile) : '') + '</div></div>' +
            '<button class="btn btn-sm" data-act="go" data-hash="#/interview/report/' + rec.id + '">查看报告</button>' +
          '</div>';
      }).join('')
    : '<div class="empty"><span class="empty-icon">🎧</span>还没有面试记录，去发起一场吧</div>';

  return '<div class="page-head"><h2>面试记录</h2><p>历史面试与对应报告</p></div>' +
    '<div class="card card-pad mt16">' + rows + '</div>';
};

CViews.profile = function () {
  const u = state.user || {};
  const doneCourses = Object.keys(state.completedCourses).length;
  return '' +
    '<div class="page-head"><h2>个人信息</h2><p>注册手机号不可修改（原型简化）</p></div>' +
    '<div class="grid g2 mt16">' +
      '<div class="card card-pad">' +
        '<div class="row" style="gap:14px">' +
          '<div class="avatar" style="width:52px;height:52px;font-size:20px">' +
            esc((u.nickname || u.phone || '学').slice(0, 1)) + '</div>' +
          '<div><h4 style="margin:0">' + esc(u.nickname || '未设置昵称') + '</h4>' +
            '<div class="small muted">' + esc(u.phone) + '</div></div>' +
        '</div>' +
        '<div class="field mt24"><label>昵称</label>' +
          '<input class="input" id="pf-nickname" value="' + esc(u.nickname || '') + '" placeholder="设置一个昵称"></div>' +
        '<div class="field"><label>所在城市</label>' +
          '<input class="input" id="pf-city" value="' + esc(u.city || '') + '" placeholder="选填"></div>' +
        '<button class="btn btn-primary" data-act="save-profile">保存</button>' +
      '</div>' +
      '<div class="card card-pad">' +
        '<h4 style="margin:0 0 12px">我的数据</h4>' +
        '<div class="row-between" style="padding:8px 0;border-bottom:1px solid var(--line)"><span class="muted">点亮课程</span><b>' + doneCourses + '</b></div>' +
        '<div class="row-between" style="padding:8px 0;border-bottom:1px solid var(--line)"><span class="muted">答题记录</span><b>' + state.papers.length + '</b></div>' +
        '<div class="row-between" style="padding:8px 0;border-bottom:1px solid var(--line)"><span class="muted">错题本</span><b>' + state.wrongBook.length + '</b></div>' +
        '<div class="row-between" style="padding:8px 0"><span class="muted">面试次数</span><b>' + state.interviews.length + '</b></div>' +
        '<div class="row mt24"><button class="btn" data-act="go" data-hash="#/records/interview">面试记录</button>' +
          '<button class="btn btn-danger" data-act="logout">退出登录</button></div>' +
      '</div>' +
    '</div>';
};

CViews.notfound = function () {
  return '<div class="empty"><span class="empty-icon">🔍</span>页面不存在' +
    '<div class="mt16"><button class="btn btn-primary" data-act="go" data-hash="#/home">回到首页</button></div></div>';
};

/* ==================== 事件委托 ==================== */

document.addEventListener('click', function (e) {
  const trigger = e.target.closest('[data-act]');
  if (!trigger) return;
  const act = trigger.dataset.act;
  const id = trigger.dataset.id;

  switch (act) {
    /* ---- 通用 ---- */
    case 'go':
      go(trigger.dataset.hash);
      break;
    case 'modal-close':
      closeModal();
      break;
    case 'modal-close-bg':
      if (e.target === trigger) {
        const wasRetry = !!retryState;
        closeModal();
        if (wasRetry) render();
      }
      break;
    case 'modal-ok':
      if (modalOnOk) modalOnOk();
      break;
    case 'logout':
      state.user = null;
      saveState();
      // 管理端退出后回到学员端登录页（两个入口是两个页面）
      if (APP_SCOPE === 'admin') location.href = 'index.html#/login';
      else go('#/login');
      break;

    /* ---- 登录 ---- */
    case 'login-tab': {
      const tab = trigger.dataset.tab;
      if (tab === loginTab) return;
      loginTab = tab;

      // 只切按钮态与表单区域，整页不重渲染，避免画面闪烁
      const index = Math.max(LOGIN_TABS.findIndex(function (t) { return t.key === tab; }), 0);
      const buttons = document.querySelectorAll('.tabs-slide button');
      Array.prototype.forEach.call(buttons, function (btn) {
        if (btn.dataset.tab === tab) btn.classList.add('active');
        else btn.classList.remove('active');
      });
      const indicator = document.getElementById('login-indicator');
      if (indicator) indicator.style.transform = 'translateX(' + (index * 100) + '%)';

      const title = document.getElementById('login-title');
      if (title) title.textContent = loginTitle(tab);
      const sub = document.getElementById('login-sub');
      if (sub) sub.textContent = loginSubtitle(tab);

      const panel = document.getElementById('login-form-body');
      if (panel) panel.innerHTML = loginPanelHtml(tab);
      break;
    }
    case 'do-login': {
      const phone = document.getElementById('login-phone').value.trim();
      const pwd = document.getElementById('login-pwd').value.trim();
      if (!/^1\d{10}$/.test(phone)) { toast('请输入 11 位手机号'); return; }
      if (!pwd) { toast('请输入密码'); return; }
      lastPhone = phone;
      state.user = { phone: phone, nickname: '学员' + phone.slice(-4), isAdmin: false };
      saveState();
      toast('登录成功');
      go('#/home');
      break;
    }
    case 'send-code': {
      const btn = document.getElementById('reg-code-btn');
      if (btn.disabled) return;
      let left = 60;
      btn.disabled = true;
      btn.textContent = left + 's 后重发';
      toast('验证码已发送（原型：任意 4 位数字即可）');
      const timer = setInterval(function () {
        left -= 1;
        if (!document.body.contains(btn)) { clearInterval(timer); return; }
        if (left <= 0) {
          clearInterval(timer);
          btn.disabled = false;
          btn.textContent = '获取验证码';
        } else {
          btn.textContent = left + 's 后重发';
        }
      }, 1000);
      break;
    }
    case 'do-register': {
      const phone = document.getElementById('reg-phone').value.trim();
      const code = document.getElementById('reg-code').value.trim();
      const pwd = document.getElementById('reg-pwd').value.trim();
      const pwd2 = document.getElementById('reg-pwd2').value.trim();
      if (!/^1\d{10}$/.test(phone)) { toast('请输入 11 位手机号'); return; }
      if (!/^\d{4}$/.test(code)) { toast('请输入 4 位验证码'); return; }
      if (pwd.length < 6) { toast('密码至少 6 位'); return; }
      if (pwd !== pwd2) { toast('两次输入的密码不一致'); return; }
      lastPhone = phone;
      state.user = { phone: phone, nickname: '学员' + phone.slice(-4), isAdmin: false };
      saveState();
      toast('注册成功，已自动登录');
      go('#/home');
      break;
    }
    case 'do-admin-login': {
      const name = document.getElementById('admin-user').value.trim();
      if (!name) { toast('请输入管理员账号'); return; }
      state.user = { phone: name, nickname: name, isAdmin: true, role: '超管' };
      saveState();
      toast('已进入管理后台');
      go('#/admin/dashboard');
      break;
    }

    /* ---- 学习 ---- */
    case 'toggle-course': {
      const course = byId(DB.courses, id);
      if (!course) return;
      if (state.completedCourses[id]) delete state.completedCourses[id];
      else state.completedCourses[id] = true;
      saveState();
      render();
      break;
    }
    case 'open-course': {
      const course = byId(DB.courses, id);
      if (!course) return;
      state.visits.unshift({ courseId: course.id, at: Date.now() });
      state.visits = state.visits.slice(0, 50);
      saveState();
      const url = course.url || ('https://search.bilibili.com/all?keyword=' + encodeURIComponent(course.title));
      window.open(url, '_blank');
      toast('已跳转 B 站，并记录一次访问');
      render();
      break;
    }

    /* ---- 刷题 ---- */
    case 'jump-q': {
      const target = document.getElementById('q-' + trigger.dataset.index);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      break;
    }
    case 'start-practice':
      startPractice(id);
      break;
    case 'choose-option': {
      const draft = state.draftPaper;
      if (!draft) return;
      const q = byId(DB.questions, trigger.dataset.qid);
      const key = trigger.dataset.key;
      if (q.type === 'multi') {
        const arr = Array.isArray(draft.answers[q.id]) ? draft.answers[q.id].slice() : [];
        const pos = arr.indexOf(key);
        if (pos > -1) arr.splice(pos, 1); else arr.push(key);
        draft.answers[q.id] = arr;
      } else {
        draft.answers[q.id] = key;
      }
      saveState();
      refreshPracticeDom();
      break;
    }
    case 'submit-paper': {
      const draft = state.draftPaper;
      if (!draft) return;
      const qs = draft.questionIds.map(function (qid) { return byId(DB.questions, qid); });
      const unanswered = qs.filter(function (q) { return !isAnswered(draft, q); }).length;
      if (unanswered > 0) {
        openModal({
          title: '还有题目未作答',
          body: '<p class="muted">还有 ' + unanswered + ' 道题未作答，未作答的题目将按 0 分计算。确定提交吗？</p>',
          okText: '仍然提交',
          onOk: function () { closeModal(); submitPaper(); }
        });
        return;
      }
      submitPaper();
      break;
    }
    case 'retry-wrong':
      openRetryModal(trigger.dataset.qid);
      break;
    case 'retry-pick': {
      if (!retryState || retryState.judged) return;
      const q = byId(DB.questions, retryState.qid);
      const key = trigger.dataset.key;
      if (q.type === 'multi') {
        const arr = retryState.picked.slice();
        const pos = arr.indexOf(key);
        if (pos > -1) arr.splice(pos, 1); else arr.push(key);
        retryState.picked = arr;
      } else {
        retryState.picked = key;
      }
      paintRetryModal();
      break;
    }
    case 'retry-confirm': {
      if (!retryState) return;
      if (!retryState.judged) {
        const empty = Array.isArray(retryState.picked) ? retryState.picked.length === 0 : !retryState.picked;
        if (empty) { toast('请先选择答案'); return; }
        retryState.judged = true;
        const q = byId(DB.questions, retryState.qid);
        if (retryIsCorrect(q)) {
          state.wrongBook = state.wrongBook.filter(function (w) { return w.qid !== q.id; });
        } else {
          const exist = state.wrongBook.find(function (w) { return w.qid === q.id; });
          if (exist) exist.times += 1;
        }
        saveState();
        paintRetryModal();
        return;
      }
      closeModal();
      render();
      break;
    }
    case 'remove-wrong':
      state.wrongBook = state.wrongBook.filter(function (w) { return w.qid !== trigger.dataset.qid; });
      saveState();
      toast('已从错题本移除');
      render();
      break;

    /* ---- 面试 ---- */
    case 'start-interview':
      startInterview(id);
      break;
    case 'resume-upload': {
      const input = document.getElementById('resume-file');
      const file = input && input.files && input.files[0];
      if (!file) { toast('请选择 PDF 简历文件'); return; }
      if (!/\.pdf$/i.test(file.name)) { toast('仅支持 PDF 格式'); return; }
      state.resume = {
        fileName: file.name,
        size: (file.size / 1024 / 1024).toFixed(2) + ' MB',
        status: 'uploading',
        at: Date.now()
      };
      saveState();
      render();
      setTimeout(function () {
        if (!state.resume) return;
        state.resume.status = 'parsing';
        saveState();
        render();
      }, 900);
      setTimeout(function () {
        if (!state.resume) return;
        state.resume.status = 'ready';
        saveState();
        toast('简历解析完成，已生成面试范围');
        render();
      }, 2100);
      break;
    }
    case 'resume-start':
      startResumeInterview();
      break;
    case 'resume-reset':
      state.resume = null;
      saveState();
      render();
      break;
    case 'iv-voice-start':
      if (state.draftInterview) {
        state.draftInterview.mode = 'voice';
        state.draftInterview.phase = 'voice-answering';
        render();
      }
      break;
    case 'iv-type-start':
      if (state.draftInterview) {
        state.draftInterview.mode = 'text';
        state.draftInterview.phase = 'typing';
        render();
        const input = document.getElementById('iv-text');
        if (input) input.focus();
      }
      break;
    case 'iv-text-submit':
      ivAnswerDone();
      break;
    case 'iv-answer-done':
      ivAnswerDone();
      break;
    case 'iv-follow':
      ivFollow();
      break;
    case 'iv-next':
      ivNext();
      break;
    case 'iv-end':
      openModal({
        title: '提前结束面试',
        body: '<p class="muted">结束后将按已作答的题目生成报告，未作答题目按 0 分计算。本次已计入每日次数。</p>',
        okText: '结束并生成报告',
        onOk: function () { closeModal(); endInterview(false); }
      });
      break;

    /* ---- 个人信息 ---- */
    case 'save-profile': {
      const nickname = document.getElementById('pf-nickname').value.trim();
      const city = document.getElementById('pf-city').value.trim();
      state.user.nickname = nickname || state.user.nickname;
      state.user.city = city;
      saveState();
      toast('已保存');
      render();
      break;
    }
  }
});

/* 简答题输入 */
document.addEventListener('input', function (e) {
  const el = e.target;
  if (el.dataset && el.dataset.input === 'short' && state.draftPaper) {
    state.draftPaper.answers[el.dataset.qid] = el.value;
    saveState();
    refreshPracticeDom();
  }
  if (el.dataset && el.dataset.input === 'interview' && state.draftInterview) {
    state.draftInterview.typed = el.value;
  }
});

/* ==================== 启动 ==================== */

const DEFAULT_HASH = APP_SCOPE === 'admin' ? '#/admin/dashboard' : '#/login';

window.addEventListener('hashchange', function () {
  if (!location.hash) location.hash = DEFAULT_HASH;
  render();
});

if (!location.hash) location.hash = DEFAULT_HASH;
render();
