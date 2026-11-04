/* 云枢智学 · 交互原型（管理后台页面）
 * 结构：学科 → 课程 两级；题目挂学科；无学习路线模块。
 */

/* ==================== 后台框架 ==================== */

const adminNav = [
  { group: '概览', items: [{ hash: '#/admin/dashboard', label: '数据看板', key: 'admin-dashboard' }] },
  { group: '内容管理', items: [
    { hash: '#/admin/content', label: '课程内容', key: 'admin-content' },
    { hash: '#/admin/questions', label: '刷题题库', key: 'admin-questions' },
    { hash: '#/admin/interview', label: '面试资料库', key: 'admin-interview' }
  ] },
  { group: '用户与系统', items: [
    { hash: '#/admin/students', label: '学员管理', key: 'admin-students' },
    { hash: '#/admin/users', label: '系统用户', key: 'admin-users' },
    { hash: '#/admin/logs', label: '操作日志', key: 'admin-logs' }
  ] }
];

function adminShell(view) {
  const navHtml = adminNav.map(function (group) {
    return '<div class="side-group">' + group.group + '</div><nav class="side-nav">' +
      group.items.map(function (item) {
        return '<a href="' + item.hash + '" class="' + (view === item.key ? 'active' : '') + '">' +
          '<span>' + item.label + '</span></a>';
      }).join('') + '</nav>';
  }).join('');

  const user = state.user || {};
  return '' +
    '<div class="admin-layout">' +
      '<aside class="sidebar">' +
        '<div class="sidebar-brand"><span class="logo">枢</span><span class="name">云枢智学 · 后台</span></div>' +
        navHtml +
      '</aside>' +
      '<div class="admin-main">' +
        '<div class="admin-top">' +
          '<div class="row"><span class="tag tag-indigo">管理后台</span>' +
            '<span class="small muted">当前角色：' + esc(user.role || '超管') + '</span></div>' +
          '<div class="row">' +
            '<a class="btn btn-sm" href="index.html">返回学员端</a>' +
            '<div class="avatar">' + esc((user.nickname || 'A').slice(0, 1)) + '</div>' +
            '<button class="btn btn-sm btn-ghost" data-act="logout">退出</button>' +
          '</div>' +
        '</div>' +
        '<div class="admin-body" id="admin-body"></div>' +
      '</div>' +
    '</div>' +
    '<div class="proto-badge">交互原型 · 后台数据刷新后重置</div>';
}

/* ==================== 后台通用件 ==================== */

function adminTable(head, rows) {
  const empty = '<tr><td colspan="' + head.length + '"><div class="empty">暂无数据</div></td></tr>';
  return '<div class="card"><div class="table-wrap"><table class="table">' +
    '<thead><tr>' + head.map(function (h) { return '<th>' + h + '</th>'; }).join('') + '</tr></thead>' +
    '<tbody>' + (rows.length ? rows.join('') : empty) + '</tbody>' +
    '</table></div></div>';
}

function adminPageHead(title, desc, addModule, addLabel) {
  return '<div class="row-between" style="margin-bottom:16px">' +
    '<div><h3 style="margin:0 0 4px">' + esc(title) + '</h3>' +
      '<span class="small muted">' + esc(desc) + '</span></div>' +
    (addModule
      ? '<button class="btn btn-primary btn-sm" data-act="admin-add" data-module="' + addModule + '">+ ' + esc(addLabel || '新增') + '</button>'
      : '') +
    '</div>';
}

function actionButtons(module, item) {
  return '<div class="table-actions">' +
    '<button class="btn btn-sm" data-act="admin-edit" data-module="' + module + '" data-id="' + item.id + '">编辑</button>' +
    '<button class="btn btn-sm" data-act="admin-toggle" data-module="' + module + '" data-id="' + item.id + '">' +
      (item.status ? '下架' : '上架') + '</button>' +
    '<button class="btn btn-sm btn-danger" data-act="admin-del" data-module="' + module + '" data-id="' + item.id + '">删除</button>' +
    '</div>';
}

function pushLog(module, action, target) {
  const user = state.user || {};
  DB.logs.unshift({
    id: 'l' + Date.now(),
    at: fmtTime(Date.now()),
    user: user.nickname || user.phone || 'admin',
    module: module,
    action: action,
    target: target
  });
}

function subjectName(id) {
  const s = byId(DB.subjects, id);
  return s ? s.name : '-';
}

function subjectNames() { return DB.subjects.map(function (s) { return s.name; }); }

function nameToSubjectId(name) {
  const s = DB.subjects.find(function (x) { return x.name === name; });
  return s ? s.id : DB.subjects[0].id;
}

function shortUrl(url) {
  if (!url) return '-';
  return '<span class="small url-text" title="' + esc(url) + '">' + esc(url) + '</span>';
}

const IMPORT_KIND_LABEL = { questions: '刷题题库', interview: '面试资料库', courses: '课程内容' };

/* 课程内容页当前选中的学科 */
const contentState = { subjectId: DB.subjects[0].id };

function currentSubject() {
  let s = byId(DB.subjects, contentState.subjectId);
  if (!s) { s = DB.subjects[0]; contentState.subjectId = s.id; }
  return s;
}

/* ==================== 模块注册：新增 / 编辑表单 ==================== */

const ADMIN_MODULES = {
  subjects: {
    label: '课程内容',
    list: 'subjects',
    addTitle: '新增学科',
    fields: [
      { key: 'name', label: '学科名称', placeholder: '如：数据分析' },
      { key: 'icon', label: '图标（emoji）', value: '📘' },
      { key: 'keywords', label: '检索关键词（逗号分隔）', placeholder: '如：python,gil,接口' },
      { key: 'desc', label: '简介', type: 'textarea' }
    ],
    create: function (d) {
      return {
        id: 's-' + Date.now(), name: d.name || '未命名学科', icon: d.icon || '📘',
        keywords: (d.keywords || '').split(/[,，]/).map(function (x) { return x.trim(); }).filter(Boolean),
        desc: d.desc, status: 1
      };
    }
  },
  courses: {
    label: '课程内容',
    list: 'courses',
    addTitle: '新增课程（成为学习路径上的一个节点）',
    fields: [
      { key: 'title', label: '课程标题', placeholder: '如：并发编程入门' },
      { key: 'duration', label: '时长', value: '45 分钟' },
      { key: 'url', label: 'B 站播放地址', value: 'https://www.bilibili.com/video/BV' },
      { key: 'desc', label: '节点说明', type: 'textarea' }
    ],
    create: function (d) {
      const list = coursesOfSubject(contentState.subjectId);
      const next = list.length ? Math.max.apply(null, list.map(function (c) { return c.sortOrder; })) + 1 : 1;
      return {
        id: 'c-' + Date.now(), subjectId: contentState.subjectId, sortOrder: next,
        title: d.title || '未命名课程', duration: d.duration || '40 分钟',
        desc: d.desc || '', url: d.url || '', status: 1
      };
    }
  },
  questions: {
    label: '刷题题库',
    list: 'questions',
    addTitle: '手工新增题目',
    fields: [
      { key: 'subject', label: '所属学科', type: 'select', options: subjectNames() },
      { key: 'type', label: '题型', type: 'select', options: ['判断题', '单选题', '多选题', '简答题'] },
      { key: 'title', label: '题干', type: 'textarea' },
      { key: 'answer', label: '正确答案 / 简答参考答案', type: 'textarea', placeholder: '客观题填 A / A,C；简答题填参考答案' },
      { key: 'analysis', label: '解析 / 评分要点', type: 'textarea' }
    ],
    create: function (d) {
      const typeMap = { '判断题': 'judge', '单选题': 'single', '多选题': 'multi', '简答题': 'short' };
      const type = typeMap[d.type] || 'single';
      const q = {
        id: 'q' + Date.now(), subjectId: nameToSubjectId(d.subject), type: type,
        score: type === 'short' ? 20 : 10, difficulty: '中等', category: '手工录入', tags: ['手工录入'],
        title: d.title || '未填写题干', answer: d.answer, analysis: d.analysis
      };
      if (type === 'single' || type === 'multi') {
        q.options = [{ k: 'A', t: '选项 A' }, { k: 'B', t: '选项 B' }, { k: 'C', t: '选项 C' }, { k: 'D', t: '选项 D' }];
        if (type === 'multi') q.answer = (d.answer || 'A').split(/[,，]/).map(function (x) { return x.trim(); }).filter(Boolean);
      }
      return q;
    }
  },
  users: {
    label: '系统用户',
    list: 'adminUsers',
    addTitle: '新增后台用户',
    fields: [
      { key: 'username', label: '账号' },
      { key: 'role', label: '角色', type: 'select', options: ['运营', '超管'] }
    ],
    create: function (d) {
      return {
        id: 'a' + Date.now(), username: d.username || 'new_user',
        role: d.role, createdAt: fmtTime(Date.now()).slice(0, 10), status: 1
      };
    }
  }
};

/* 编辑表单的字段与回填 */
function editFieldsOf(moduleKey, item) {
  if (moduleKey === 'subjects') {
    return [
      { key: 'name', label: '学科名称', value: item.name },
      { key: 'icon', label: '图标（emoji）', value: item.icon },
      { key: 'keywords', label: '检索关键词（逗号分隔）', value: (item.keywords || []).join(',') },
      { key: 'desc', label: '简介', type: 'textarea', value: item.desc }
    ];
  }
  if (moduleKey === 'courses') {
    return [
      { key: 'title', label: '课程标题', value: item.title },
      { key: 'duration', label: '时长', value: item.duration },
      { key: 'url', label: 'B 站播放地址', value: item.url },
      { key: 'desc', label: '节点说明', type: 'textarea', value: item.desc || '' }
    ];
  }
  if (moduleKey === 'questions') {
    return [
      { key: 'subject', label: '所属学科', type: 'select', value: subjectName(item.subjectId), options: subjectNames() },
      { key: 'title', label: '题干', type: 'textarea', value: item.title },
      { key: 'analysis', label: '解析 / 评分要点', type: 'textarea', value: item.analysis || '' }
    ];
  }
  return [{ key: 'username', label: '账号', value: item.username }];
}

/* ==================== 资料导入（模拟解析） ==================== */

const IMPORT_CONFIG = {
  questions: {
    title: '导入刷题题库',
    accept: '.xlsx,.xls',
    fileHint: 'Excel 模板列：题干 / 分类 / 题型 / 难度 / 选项A-F / 正确答案 / 解析 / 标签',
    subjectSelect: true,
    summary: '解析 78 行，校验通过 74 行（4 行缺少题干已跳过，1 行答案格式不合法已跳过）',
    head: ['题干', '题型', '难度', '正确答案', '解析'],
    rows: [
      { cells: ['下列哪种类型不是作为 Collection 类型的集合？', '单选题', '简单', 'C', 'Map 与 Collection 并列，不属于 Collection'], type: 'single', answer: 'C', analysis: 'Map 与 Collection 并列，不属于 Collection' },
      { cells: ['下列关于函数参数的说法，正确的有', '多选题', '简单', 'A,B,C', '位置参数必须在关键字参数之前'], type: 'multi', answer: 'A,B,C', analysis: '位置参数必须在关键字参数之前' },
      { cells: ['请写出方法定义的通用语法格式', '简答题', '中等', '修饰符 返回值类型 方法名(参数列表) { 方法体 }', '考察方法定义完整结构'], type: 'short', answer: '修饰符 返回值类型 方法名(参数列表) { 方法体; return 返回值; }', analysis: '考察方法定义的完整结构' }
    ]
  },
  interview: {
    title: '上传面试资料',
    accept: '.pdf,.md',
    fileHint: '支持 PDF / Markdown；PDF 先经 MinerU 转 Markdown，再按标题层级切分并向量化入库',
    summary: '处理完成：转 md 成功，切分 42 个片段，已写入向量库',
    head: ['处理步骤', '结果'],
    rows: [
      { cells: ['① 上传文件', '接收原始 PDF 并保存，保留原始文档'] },
      { cells: ['② 转 Markdown', 'MinerU 解析版式、表格与代码块，输出保留标题层级的 md'] },
      { cells: ['③ 语义切分', '按标题层级切分，单个片段约 400–600 字，相邻片段重叠 80 字'] },
      { cells: ['④ 向量化入库', '写入向量库，同时建立关键词索引，供后续 RRF 融合使用'] }
    ]
  },
  courses: {
    title: '导入课程数据',
    accept: '.xlsx,.xls',
    fileHint: 'Excel 模板列：课程名称 / 来源 / 时长（分钟）/ BV号 / 封面 / 播放链接',
    subjectSelect: true,
    summary: '解析 436 行，校验通过 430 行（6 行播放链接为空已跳过）',
    head: ['课程名称', '时长', '播放链接'],
    rows: [
      { cells: ['2026全网最夯VibeCoding零基础入门到实战项目开发全套视频教程', '293 分钟', 'https://www.bilibili.com/video/BV1WWYE6LEzx'], url: 'https://www.bilibili.com/video/BV1WWYE6LEzx' },
      { cells: ['零基础AI具身智能机器人实战全套课程', '211 分钟', 'https://www.bilibili.com/video/BV1TLNn6HEsm'], url: 'https://www.bilibili.com/video/BV1TLNn6HEsm' },
      { cells: ['全网首发Agent测试一套通关', '2272 分钟', 'https://www.bilibili.com/video/BV1m6G26yEue'], url: 'https://www.bilibili.com/video/BV1m6G26yEue' }
    ]
  }
};

let importState = null;

function openImport(kind) {
  importState = { kind: kind, step: 1, subjectId: contentState.subjectId };
  paintImportModal();
}

function paintImportModal() {
  if (!importState) return;
  const cfg = IMPORT_CONFIG[importState.kind];
  let body = '';

  if (importState.step === 1) {
    body =
      '<div class="field"><label>上传文件</label>' +
        '<input class="input" type="file" id="import-file" accept="' + cfg.accept + '" style="padding:8px 10px;height:auto">' +
        '<div class="small muted" style="margin-top:6px">' + esc(cfg.fileHint) + '</div>' +
      '</div>' +
      (cfg.subjectSelect
        ? '<div class="field"><label>导入到学科</label>' +
            '<select class="select" id="import-subject">' +
              DB.subjects.map(function (s) {
                return '<option value="' + s.id + '" ' + (s.id === importState.subjectId ? 'selected' : '') + '>' + esc(s.name) + '</option>';
              }).join('') +
            '</select></div>'
        : '<div class="field"><label>入库方式</label>' +
            '<div class="small muted">统一入面试资料库，不区分学科；抽题时按关键词检索</div></div>') +
      '<p class="small muted">原型说明：未选择文件时使用内置示例数据演示解析结果，实际上传后在服务端解析。</p>';

    document.getElementById('modal-root').innerHTML =
      '<div class="modal-mask" data-act="import-close-bg">' +
        '<div class="modal"><div class="modal-head">' + esc(cfg.title) + '</div>' +
          '<div class="modal-body">' + body + '</div>' +
          '<div class="modal-foot">' +
            '<button class="btn" data-act="import-close">取消</button>' +
            '<button class="btn btn-primary" data-act="import-next">解析并预览</button>' +
          '</div></div></div>';
    return;
  }

  const headHtml = '<tr>' + cfg.head.map(function (h) { return '<th>' + esc(h) + '</th>'; }).join('') + '</tr>';
  const rowsHtml = cfg.rows.map(function (r) {
    return '<tr>' + r.cells.map(function (c) {
      return '<td class="small">' + esc(c.length > 46 ? c.slice(0, 46) + '…' : c) + '</td>';
    }).join('') + '</tr>';
  }).join('');

  const targetName = cfg.subjectSelect ? subjectName(importState.subjectId) : '面试资料库';
  body =
    '<div class="row-between" style="margin-bottom:12px">' +
      '<span class="small muted">' + esc(importState.fileName || '示例文件') + ' → ' + esc(targetName) + '</span>' +
      '<span class="tag tag-green">' + esc(cfg.summary) + '</span>' +
    '</div>' +
    '<div class="table-wrap"><table class="table"><thead>' + headHtml + '</thead><tbody>' + rowsHtml + '</tbody></table></div>' +
    '<p class="small muted mt16">预览为前 3 行示例；确认后按模板批量写入。</p>';

  document.getElementById('modal-root').innerHTML =
    '<div class="modal-mask" data-act="import-close-bg">' +
      '<div class="modal" style="max-width:720px"><div class="modal-head">' + esc(cfg.title) + ' · 解析结果</div>' +
        '<div class="modal-body">' + body + '</div>' +
        '<div class="modal-foot">' +
          '<button class="btn" data-act="import-back">上一步</button>' +
          '<button class="btn btn-primary" data-act="import-confirm">确认导入</button>' +
        '</div></div></div>';
}

function confirmImport() {
  const cfg = IMPORT_CONFIG[importState.kind];

  // 面试资料：PDF → 转 md → 切分 → 入库，直接生成一条文档记录
  if (importState.kind === 'interview') {
    const name = importState.fileName || '新上传资料.pdf';
    const isPdf = /\.pdf$/i.test(name);
    DB.interviewDocs.unshift({
      id: 'd' + Date.now(),
      name: name,
      type: isPdf ? 'pdf' : 'md',
      size: '—',
      status: 'ready',
      uploadedAt: fmtTime(Date.now())
    });
    pushLog('面试资料库', '上传', name + ' · 切分 42 段');
    closeModal();
    toast('已上传并完成切分入库');
    render();
    return;
  }

  let inserted = 0;
  cfg.rows.forEach(function (row) {
    const stamp = Date.now() + 'x' + Math.floor(Math.random() * 9999);
    if (importState.kind === 'questions') {
      const q = {
        id: 'q' + stamp, subjectId: importState.subjectId, type: row.type,
        score: row.type === 'short' ? 20 : 10, difficulty: '简单', category: '导入题库', tags: ['导入'],
        title: row.cells[0], answer: row.type === 'multi' ? row.answer.split(',') : row.answer,
        analysis: row.analysis
      };
      if (row.type === 'single' || row.type === 'multi') {
        q.options = [{ k: 'A', t: '选项 A' }, { k: 'B', t: '选项 B' }, { k: 'C', t: '选项 C' }, { k: 'D', t: '选项 D' }];
      }
      DB.questions.unshift(q);
    } else {
      const list = coursesOfSubject(importState.subjectId);
      const nextSort = list.length ? Math.max.apply(null, list.map(function (c) { return c.sortOrder; })) + 1 : 1;
      DB.courses.push({
        id: 'c' + stamp, subjectId: importState.subjectId, sortOrder: nextSort,
        title: row.cells[0], duration: row.cells[1], desc: '', source: 'B站', url: row.url, status: 1
      });
    }
    inserted += 1;
  });

  pushLog(IMPORT_KIND_LABEL[importState.kind] || '资料导入', '导入',
    subjectName(importState.subjectId) + ' · ' + inserted + ' 条');
  closeModal();
  toast('已导入 ' + inserted + ' 条，录完即上线');
  render();
}

/* ==================== 后台页面 ==================== */

const AdminViews = {};

AdminViews['admin-dashboard'] = function () {
  const totalStudents = 128 + DB.dailyStats.reduce(function (n, d) { return n + d.register; }, 0);
  const today = DB.dailyStats[DB.dailyStats.length - 1];
  const maxRegister = Math.max.apply(null, DB.dailyStats.map(function (d) { return d.register; }));

  const chart = DB.dailyStats.map(function (d) {
    const h = Math.round(d.register / maxRegister * 100);
    return '<div class="chart-col">' +
      '<div class="chart-bar" style="height:' + h + '%"><span>' + d.register + '</span></div>' +
      '<div class="chart-label">' + d.day + '</div></div>';
  }).join('');

  return adminPageHead('数据看板', '按需求约定，看板仅统计学员规模与活跃，不含学习/刷题/面试指标') +
    '<div class="grid g4">' +
      '<div class="card stat"><div class="stat-label">累计注册学员</div><div class="stat-num" data-count="' + totalStudents + '">0</div></div>' +
      '<div class="card stat"><div class="stat-label">今日新增</div><div class="stat-num" data-count="' + today.register + '">0</div></div>' +
      '<div class="card stat"><div class="stat-label">今日活跃</div><div class="stat-num" data-count="' + today.active + '">0</div></div>' +
      '<div class="card stat"><div class="stat-label">近 7 日新增</div><div class="stat-num" data-count="' +
        DB.dailyStats.reduce(function (n, d) { return n + d.register; }, 0) + '">0</div></div>' +
    '</div>' +
    '<div class="card mt16"><div class="card-head"><h3>近 7 日新增注册</h3>' +
      '<span class="small muted">单位：人</span></div>' +
      '<div class="card-body"><div class="chart">' + chart + '</div></div></div>' +
    '<div class="card card-pad mt16"><div class="small muted">' +
      '口径说明：活跃按「登录去重、近 7 天滚动」统计。掌握度相关数据归学员自己查看，后台不展示；题目错误率排行等统计不在本期范围。' +
    '</div></div>';
};

AdminViews['admin-content'] = function () {
  const subject = currentSubject();
  const courses = coursesOfSubject(subject.id);

  const subjectTabs = DB.subjects.map(function (s) {
    const active = s.id === contentState.subjectId;
    return '<button class="btn btn-sm ' + (active ? 'btn-primary' : '') + '" ' +
      'data-act="pick-subject" data-id="' + s.id + '">' + s.icon + ' ' + esc(s.name) + '</button>';
  }).join('');

  const keywordChips = (subject.keywords || []).map(function (k) {
    return '<span class="tag tag-indigo">' + esc(k) + '</span>';
  }).join(' ') || '<span class="small muted">未设置检索关键词</span>';

  const rows = courses.map(function (c, i) {
    return '<tr>' +
      '<td>' + c.sortOrder + '</td>' +
      '<td>' + esc(c.title) + '</td>' +
      '<td class="small muted">' + esc(c.duration) + '</td>' +
      '<td>' + shortUrl(c.url) + '</td>' +
      '<td>' + statusTag(c.status) + '</td>' +
      '<td><div class="table-actions">' +
        '<button class="btn btn-sm" data-act="course-up" data-id="' + c.id + '" ' + (i === 0 ? 'disabled' : '') + '>上移</button>' +
        '<button class="btn btn-sm" data-act="course-down" data-id="' + c.id + '" ' + (i === courses.length - 1 ? 'disabled' : '') + '>下移</button>' +
        '<button class="btn btn-sm" data-act="admin-edit" data-module="courses" data-id="' + c.id + '">编辑</button>' +
        '<button class="btn btn-sm" data-act="admin-toggle" data-module="courses" data-id="' + c.id + '">' +
          (c.status ? '下架' : '上架') + '</button>' +
        '<button class="btn btn-sm btn-danger" data-act="admin-del" data-module="courses" data-id="' + c.id + '">删除</button>' +
      '</div></td>' +
      '</tr>';
  });

  return '' +
    '<div class="row-between" style="margin-bottom:16px">' +
      '<div><h3 style="margin:0 0 4px">课程内容</h3>' +
        '<span class="small muted">学科 → 课程 两级；课程顺序即学员看到的学习路径</span></div>' +
      '<button class="btn btn-sm" data-act="admin-add" data-module="subjects">+ 新增学科</button>' +
    '</div>' +
    '<div class="card card-pad"><div class="row wrap">' + subjectTabs + '</div></div>' +

    '<div class="card card-pad mt16">' +
      '<div class="row-between">' +
        '<div><h4 style="margin:0 0 4px">' + subject.icon + ' ' + esc(subject.name) + '</h4>' +
          '<span class="small muted">' + esc(subject.desc) + '</span></div>' +
        '<div class="row">' +
          '<button class="btn btn-sm" data-act="import-open" data-kind="courses">导入课程 Excel</button>' +
          '<button class="btn btn-sm btn-primary" data-act="admin-add" data-module="courses">+ 新增课程</button>' +
        '</div>' +
      '</div>' +
      '<div class="row wrap mt16"><span class="small muted" style="margin-right:6px">AI 面试检索关键词：</span>' + keywordChips + '</div>' +
      '<div class="row mt16">' +
        '<button class="btn btn-sm" data-act="admin-edit" data-module="subjects" data-id="' + subject.id + '">编辑学科</button>' +
        '<button class="btn btn-sm" data-act="admin-toggle" data-module="subjects" data-id="' + subject.id + '">' +
          (subject.status ? '下架学科' : '上架学科') + '</button>' +
        '<button class="btn btn-sm btn-danger" data-act="admin-del" data-module="subjects" data-id="' + subject.id + '">删除学科</button>' +
      '</div>' +
    '</div>' +

    '<div class="mt16">' +
      adminTable(['顺序', '课程标题', '时长', 'B 站播放地址', '状态', '操作'], rows) +
    '</div>' +
    '<p class="small muted mt16">提示：删除学科前需先删除该学科下的课程（应用层校验）；课程为线性顺序，用「上移 / 下移」调整学习路径。</p>';
};

AdminViews['admin-questions'] = function () {
  const rows = DB.questions.map(function (q) {
    return '<tr>' +
      '<td class="small">' + esc(subjectName(q.subjectId)) + '</td>' +
      '<td><span class="tag tag-indigo">' + TYPE_LABEL[q.type] + '</span></td>' +
      '<td class="small">' + esc(q.title.length > 38 ? q.title.slice(0, 38) + '…' : q.title) + '</td>' +
      '<td class="small muted">' + esc(q.difficulty || '-') + '</td>' +
      '<td class="small" title="' + esc(answerText(q)) + '">' + esc(answerText(q).slice(0, 20)) + (answerText(q).length > 20 ? '…' : '') + '</td>' +
      '<td class="small muted">' + esc((q.analysis || '-').slice(0, 26)) + '</td>' +
      '<td>' + q.score + '</td>' +
      '<td><div class="table-actions">' +
        '<button class="btn btn-sm" data-act="admin-edit" data-module="questions" data-id="' + q.id + '">编辑</button>' +
        '<button class="btn btn-sm btn-danger" data-act="admin-del" data-module="questions" data-id="' + q.id + '">删除</button>' +
      '</div></td>' +
      '</tr>';
  });

  return '<div class="row-between" style="margin-bottom:16px">' +
      '<div><h3 style="margin:0 0 4px">刷题题库</h3>' +
        '<span class="small muted">题目挂学科，整学科组卷；简答题录参考答案与解析，判分时由 AI 对照打分</span></div>' +
      '<div class="row">' +
        '<button class="btn btn-sm" data-act="import-open" data-kind="questions">导入题库 Excel</button>' +
        '<button class="btn btn-sm btn-primary" data-act="admin-add" data-module="questions">+ 手工新增</button>' +
      '</div>' +
    '</div>' +
    adminTable(['所属学科', '题型', '题干', '难度', '正确答案 / 参考答案', '解析', '分值', '操作'], rows);
};

AdminViews['admin-interview'] = function () {
  const statusMap = {
    ready: '<span class="tag tag-green">已切分入库</span>',
    converting: '<span class="tag tag-orange">转 md 中</span>',
    pending: '<span class="tag">待处理</span>'
  };

  const rows = DB.interviewDocs.map(function (d) {
    return '<tr>' +
      '<td>' + esc(d.name) + '</td>' +
      '<td><span class="tag">' + d.type.toUpperCase() + '</span></td>' +
      '<td class="small muted">' + esc(d.size) + '</td>' +
      '<td class="small muted">' + esc(d.uploadedAt) + '</td>' +
      '<td>' + (statusMap[d.status] || statusMap.pending) + '</td>' +
      '<td><div class="table-actions">' +
        '<button class="btn btn-sm btn-danger" data-act="admin-doc-del" data-id="' + d.id + '">删除</button>' +
      '</div></td>' +
      '</tr>';
  });

  const steps = [
    { t: '① 上传资料', d: 'PDF / Markdown 原文件' },
    { t: '② 转 Markdown', d: 'MinerU 解析版式、表格与代码块' },
    { t: '③ 语义切分', d: '按标题层级切分，相邻片段重叠' },
    { t: '④ 向量化入库', d: '向量索引 + 关键词索引，供 RRF 融合' }
  ].map(function (s) {
    return '<div class="card stat"><div class="stat-label">' + esc(s.t) + '</div>' +
      '<div class="small" style="margin-top:4px">' + esc(s.d) + '</div></div>';
  }).join('');

  return '<div class="row-between" style="margin-bottom:16px">' +
      '<div><h3 style="margin:0 0 4px">面试资料库</h3>' +
        '<span class="small muted">只管理原始资料：上传 md / pdf，转 md 后切分入库；面试题由检索结果动态生成</span></div>' +
      '<div class="row">' +
        '<button class="btn btn-sm" data-act="retrieve-open">检索测试（RRF）</button>' +
        '<button class="btn btn-sm btn-primary" data-act="import-open" data-kind="interview">上传资料</button>' +
      '</div>' +
    '</div>' +
    '<div class="grid g4">' + steps + '</div>' +
    adminTable(['文档', '类型', '大小', '上传时间', '状态', '操作'], rows) +
    '<p class="small muted mt16">切片入库后不记录归属学科：发起面试时用学科关键词作为 query 做向量召回 + 关键词召回，RRF 融合排序后取 TopN 片段交给模型生成 5 道面试题。</p>';
};

/* 检索测试：展示 RRF 融合排序结果（原型为模拟打分） */
let retrieveState = null;

function openRetrieve() {
  retrieveState = { subjectId: DB.subjects[0].id };
  paintRetrieveModal();
}

function paintRetrieveModal() {
  const subject = byId(DB.subjects, retrieveState.subjectId);
  const snippets = searchSnippets(subject ? subject.keywords : []);
  const scored = snippets.map(function (s, i) {
    const vecRank = i + 1;
    const kwRank = i === 1 ? 1 : i + 1;
    const rrf = 1 / (60 + vecRank) + 1 / (60 + kwRank);
    return { s: s, vecRank: vecRank, kwRank: kwRank, rrf: rrf };
  }).sort(function (a, b) { return b.rrf - a.rrf; }).slice(0, 5);

  const rows = scored.map(function (r) {
    return '<tr>' +
      '<td class="small">' + esc(r.s.question) + '</td>' +
      '<td class="small muted">' + esc(docName(r.s.docId)) + '</td>' +
      '<td>' + r.vecRank + '</td>' +
      '<td>' + r.kwRank + '</td>' +
      '<td><b>' + r.rrf.toFixed(5) + '</b></td>' +
      '</tr>';
  }).join('');

  document.getElementById('modal-root').innerHTML =
    '<div class="modal-mask" data-act="retrieve-close-bg">' +
      '<div class="modal" style="max-width:760px">' +
        '<div class="modal-head">检索测试 · RRF 融合排序</div>' +
        '<div class="modal-body">' +
          '<div class="field"><label>面试学科</label>' +
            '<select class="select" id="retrieve-subject">' +
              DB.subjects.map(function (s) {
                return '<option value="' + s.id + '" ' + (s.id === retrieveState.subjectId ? 'selected' : '') + '>' + esc(s.name) + '</option>';
              }).join('') +
            '</select></div>' +
          '<div class="table-wrap" style="margin-top:8px"><table class="table">' +
            '<thead><tr><th>召回片段（生成的题目）</th><th>来源文档</th><th>向量排名</th><th>关键词排名</th><th>RRF 得分</th></tr></thead>' +
            '<tbody>' + (rows || '<tr><td colspan="5"><div class="empty">该学科暂无可用片段</div></td></tr>') + '</tbody>' +
          '</table></div>' +
          '<p class="small muted mt16">RRF 得分 = 1/(60+向量排名) + 1/(60+关键词排名)；融合后取 TopN 交给模型出题。</p>' +
        '</div>' +
        '<div class="modal-foot">' +
          '<button class="btn" data-act="retrieve-close">关闭</button>' +
          '<button class="btn btn-primary" data-act="retrieve-run">重新检索</button>' +
        '</div>' +
      '</div>' +
    '</div>';
}

AdminViews['admin-students'] = function () {
  const rows = DB.students.map(function (u) {
    return '<tr>' +
      '<td>' + esc(u.phone) + '</td>' +
      '<td>' + esc(u.nickname) + '</td>' +
      '<td>' + esc(u.registeredAt) + '</td>' +
      '<td>' + u.doneCourses + '</td>' +
      '<td>' + statusTag(u.status, '正常', '已禁用') + '</td>' +
      '<td><div class="table-actions">' +
        '<button class="btn btn-sm" data-act="admin-toggle" data-module="students" data-id="' + u.id + '">' +
          (u.status ? '禁用' : '启用') + '</button>' +
      '</div></td>' +
      '</tr>';
  });
  return adminPageHead('学员管理', '仅展示账号与点亮课程数，不展示掌握度、刷题与面试结果') +
    adminTable(['手机号', '昵称', '注册时间', '点亮课程', '状态', '操作'], rows);
};

AdminViews['admin-users'] = function () {
  const rows = DB.adminUsers.map(function (u) {
    let ops;
    if (u.protected) {
      ops = '<span class="tag">内置账号 · 不可删除</span>';
    } else {
      ops = '<div class="table-actions">' +
        '<button class="btn btn-sm" data-act="admin-toggle" data-module="users" data-id="' + u.id + '">' +
          (u.status ? '停用' : '启用') + '</button>' +
        '<button class="btn btn-sm btn-danger" data-act="admin-del" data-module="users" data-id="' + u.id + '">删除</button>' +
        '</div>';
    }
    return '<tr>' +
      '<td>' + esc(u.username) + (u.protected ? ' <span class="tag tag-indigo">超管</span>' : '') + '</td>' +
      '<td><span class="tag ' + (u.role === '超管' ? 'tag-indigo' : '') + '">' + esc(u.role) + '</span></td>' +
      '<td>' + esc(u.createdAt) + '</td>' +
      '<td>' + statusTag(u.status, '启用', '停用') + '</td>' +
      '<td>' + ops + '</td>' +
      '</tr>';
  });
  return adminPageHead('系统用户管理', '角色固定为超管 / 运营两种；内置超管账号不可删除、不可停用', 'users', '新增用户') +
    adminTable(['账号', '角色', '创建时间', '状态', '操作'], rows) +
    '<p class="small muted mt16">权限约定：运营管理内容（学科与课程 / 题库 / 资料库），超管额外可管理系统用户。</p>';
};

AdminViews['admin-logs'] = function () {
  const rows = DB.logs.map(function (l) {
    return '<tr>' +
      '<td class="small muted">' + esc(l.at) + '</td>' +
      '<td>' + esc(l.user) + '</td>' +
      '<td>' + esc(l.module) + '</td>' +
      '<td><span class="tag">' + esc(l.action) + '</span></td>' +
      '<td>' + esc(l.target) + '</td>' +
      '</tr>';
  });
  return adminPageHead('操作日志', '记录后台关键操作，含变更前后快照（原型只展示摘要）') +
    adminTable(['时间', '操作人', '模块', '动作', '对象'], rows);
};

/* ==================== 后台交互 ==================== */

document.addEventListener('click', function (e) {
  const trigger = e.target.closest('[data-act]');
  if (!trigger) return;
  const act = trigger.dataset.act;
  const id = trigger.dataset.id;

  /* 课程内容页：切换学科 */
  if (act === 'pick-subject') {
    contentState.subjectId = id;
    render();
    return;
  }

  /* 课程顺序调整 */
  if (act === 'course-up' || act === 'course-down') {
    const list = coursesOfSubject(contentState.subjectId);
    const idx = list.findIndex(function (c) { return c.id === id; });
    const swapWith = act === 'course-up' ? idx - 1 : idx + 1;
    if (idx < 0 || swapWith < 0 || swapWith >= list.length) return;
    const a = list[idx], b = list[swapWith];
    const tmp = a.sortOrder; a.sortOrder = b.sortOrder; b.sortOrder = tmp;
    pushLog('课程内容', '调整顺序', a.title);
    render();
    return;
  }

  /* 资料导入 */
  if (act === 'import-open') {
    openImport(trigger.dataset.kind);
    return;
  }
  if (act === 'import-close') {
    closeModal();
    return;
  }
  if (act === 'import-close-bg') {
    if (e.target === trigger) closeModal();
    return;
  }
  if (act === 'import-back') {
    importState.step = 1;
    paintImportModal();
    return;
  }
  if (act === 'import-next') {
    const fileInput = document.getElementById('import-file');
    const subjectSelect = document.getElementById('import-subject');
    importState.fileName = fileInput && fileInput.files[0] ? fileInput.files[0].name : '';
    if (subjectSelect) importState.subjectId = subjectSelect.value;
    importState.step = 2;
    paintImportModal();
    return;
  }
  if (act === 'import-confirm') {
    confirmImport();
    return;
  }

  /* 面试资料库：检索测试 */
  if (act === 'retrieve-open') { openRetrieve(); return; }
  if (act === 'retrieve-run') {
    const sel = document.getElementById('retrieve-subject');
    if (sel) retrieveState.subjectId = sel.value;
    paintRetrieveModal();
    return;
  }
  if (act === 'retrieve-close') { closeModal(); return; }
  if (act === 'retrieve-close-bg') {
    if (e.target === trigger) closeModal();
    return;
  }
  if (act === 'admin-doc-del') {
    const doc = byId(DB.interviewDocs, id);
    openModal({
      title: '确认删除资料',
      body: '<p class="muted">删除后该文档的片段与向量索引一并移除，相关内容不会再被检索到。</p>' +
        '<p style="margin-bottom:0">文档：<b>' + esc(doc ? doc.name : '') + '</b></p>',
      okText: '确认删除',
      onOk: function () {
        DB.interviewDocs = DB.interviewDocs.filter(function (x) { return x.id !== id; });
        DB.interviewSnippets = DB.interviewSnippets.filter(function (s) { return s.docId !== id; });
        pushLog('面试资料库', '删除', doc ? doc.name : '');
        closeModal();
        toast('已删除');
        render();
      }
    });
    return;
  }

  const moduleKey = trigger.dataset.module;
  if (!moduleKey || !ADMIN_MODULES[moduleKey]) return;

  const config = ADMIN_MODULES[moduleKey];
  const list = DB[config.list];

  if (act === 'admin-add') {
    openModal({
      title: config.addTitle,
      fields: config.fields,
      okText: '保存',
      onOk: function (data) {
        const item = config.create(data);
        list.push(item);
        pushLog(config.label, '新增', item.name || item.title || item.username || '未命名');
        closeModal();
        toast('已保存，录完即上线');
        render();
      }
    });
    return;
  }

  if (act === 'admin-edit') {
    const item = list.find(function (x) { return x.id === id; });
    if (!item) return;
    openModal({
      title: '编辑',
      fields: editFieldsOf(moduleKey, item),
      okText: '保存',
      onOk: function (data) {
        if (moduleKey === 'subjects') {
          item.name = data.name || item.name;
          item.icon = data.icon || item.icon;
          item.desc = data.desc;
          item.keywords = (data.keywords || '').split(/[,，]/).map(function (x) { return x.trim(); }).filter(Boolean);
        } else if (moduleKey === 'courses') {
          item.title = data.title || item.title;
          item.duration = data.duration || item.duration;
          item.url = data.url || item.url;
          item.desc = data.desc || '';
        } else if (moduleKey === 'questions') {
          item.subjectId = nameToSubjectId(data.subject);
          item.title = data.title || item.title;
          item.analysis = data.analysis || '';
          item.tags = ['手工录入'];
        } else {
          item.username = data.username || item.username;
        }
        pushLog(config.label, '编辑', item.name || item.title || item.username || '');
        closeModal();
        toast('已保存');
        render();
      }
    });
    return;
  }

  if (act === 'admin-toggle') {
    const item = list.find(function (x) { return x.id === id; });
    if (!item || item.status === undefined) return;
    if (item.protected) { toast('内置账号不可停用'); return; }

    // 学科下架/删除前：不允许在有课程时直接删除（在 admin-del 中校验）
    item.status = item.status ? 0 : 1;
    pushLog(config.label, item.status ? '上架' : '下架', item.name || item.title || item.username || '');
    toast(item.status ? '已上架' : '已下架');
    render();
    return;
  }

  if (act === 'admin-del') {
    const item = list.find(function (x) { return x.id === id; });
    if (item && item.protected) { toast('内置账号不可删除'); return; }

    // 学科：有未删除课程时禁止删除（对应数据库设计 Q6 结论）
    if (moduleKey === 'subjects' && item) {
      const remain = coursesOfSubject(item.id).filter(function (c) { return !c.deletedAt; });
      if (remain.length) {
        toast('该学科下还有 ' + remain.length + ' 门课程，请先删除或下架课程');
        return;
      }
    }

    openModal({
      title: '确认删除',
      body: '<p class="muted">删除后该条目不再展示（正式实现为软删除，原型中直接从列表移除）。</p>' +
        '<p style="margin-bottom:0">对象：<b>' + esc(item ? (item.name || item.title || item.username) : '') + '</b></p>',
      okText: '确认删除',
      onOk: function () {
        if (item) item.deletedAt = fmtTime(Date.now());
        const idx = list.indexOf(item);
        if (idx > -1) list.splice(idx, 1);
        pushLog(config.label, '删除', item ? (item.name || item.title || item.username) : '');
        closeModal();
        toast('已删除');
        render();
      }
    });
  }
});
