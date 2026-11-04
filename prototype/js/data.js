/* 云枢智学 · 交互原型模拟数据
 * 说明：数据均为本地模拟，不涉及服务端请求。
 * 结构（v2）：学科 → 课程（线性学习顺序的节点图）；题目挂学科；点亮 = 课程完成。
 */

const DB = {};

/* ---------------- 学科（= 一条学习路径） ---------------- */
DB.subjects = [
  { id: 's-ai', name: 'AI 全栈开发', icon: '🧠', status: 1,
    keywords: ['python', 'gil', '接口', '数据库', '大模型', '流式'],
    desc: '从 Python 基础到 Web 后端接口，再到大模型应用落地，覆盖 AI 应用工程师的完整链路。' },
  { id: 's-agent', name: 'Agent 开发', icon: '🤖', status: 1,
    keywords: ['提示词', 'rag', '工具调用', '智能体', '模型', '格式'],
    desc: '围绕 Prompt 工程、工具调用、RAG 与多智能体编排，做能真正跑起来的智能体应用。' },
  { id: 's-java', name: 'Java 开发', icon: '☕', status: 1,
    keywords: ['hashmap', '多态', '线程池', 'spring', '事务', '接口'],
    desc: 'Java 语法与集合打底，Spring Boot 工程实践为主线，面向后端开发岗位。' }
];

/* ---------------- 课程（学科下的节点，sortOrder 决定学习顺序） ---------------- */
DB.courses = [
  { id: 'c-ai-1', subjectId: 's-ai', sortOrder: 1, title: 'Python 环境搭建与基础语法', duration: '52 分钟', status: 1,
    desc: '装环境、跑通第一个脚本，语法速览。',
    url: 'https://www.bilibili.com/video/BV1WWYE6LEzx' },
  { id: 'c-ai-2', subjectId: 's-ai', sortOrder: 2, title: '列表 / 字典 / 集合的常用操作', duration: '46 分钟', status: 1,
    desc: '四种容器的增删改查与适用场景。',
    url: 'https://www.bilibili.com/video/BV1TLNn6HEsm' },
  { id: 'c-ai-3', subjectId: 's-ai', sortOrder: 3, title: '文件读写与异常处理', duration: '38 分钟', status: 1,
    desc: 'with 上下文管理、常见异常与日志。',
    url: 'https://www.bilibili.com/video/BV1RFTc62EaK' },
  { id: 'c-ai-4', subjectId: 's-ai', sortOrder: 4, title: 'HTTP 协议与接口设计基础', duration: '55 分钟', status: 1,
    desc: '请求响应、状态码与 RESTful 设计。',
    url: 'https://www.bilibili.com/video/BV1m6G26yEue' },
  { id: 'c-ai-5', subjectId: 's-ai', sortOrder: 5, title: '数据库建模与增删改查', duration: '61 分钟', status: 1,
    desc: '表设计、索引与常用 SQL。',
    url: 'https://www.bilibili.com/video/BV1395x6AEvJ' },
  { id: 'c-ai-6', subjectId: 's-ai', sortOrder: 6, title: '工程分层与依赖管理', duration: '43 分钟', status: 0,
    desc: '目录分层、配置与依赖隔离。',
    url: 'https://www.bilibili.com/video/BV1XexY6EEY1' },
  { id: 'c-ai-7', subjectId: 's-ai', sortOrder: 7, title: 'Prompt 结构化写法与示例', duration: '48 分钟', status: 1,
    desc: '角色、任务、约束、示例四段式。',
    url: 'https://www.bilibili.com/video/BV1WWYE6LEzx' },
  { id: 'c-ai-8', subjectId: 's-ai', sortOrder: 8, title: '流式输出与前端联调', duration: '40 分钟', status: 1,
    desc: 'SSE 分片处理与首字延迟优化。',
    url: 'https://www.bilibili.com/video/BV1RFTc62EaK' },

  { id: 'c-ag-1', subjectId: 's-agent', sortOrder: 1, title: '提示词的四种常见结构', duration: '44 分钟', status: 1,
    desc: '不同任务该用哪种提示词骨架。',
    url: 'https://www.bilibili.com/video/BV1XexY6EEY1' },
  { id: 'c-ag-2', subjectId: 's-agent', sortOrder: 2, title: '输出约束与格式校验', duration: '37 分钟', status: 1,
    desc: '让模型稳定输出可解析结构。',
    url: 'https://www.bilibili.com/video/BV1TLNn6HEsm' },
  { id: 'c-ag-3', subjectId: 's-agent', sortOrder: 3, title: '函数调用：让模型调用你的代码', duration: '58 分钟', status: 1,
    desc: '工具描述、参数校验与结果回灌。',
    url: 'https://www.bilibili.com/video/BV1m6G26yEue' },
  { id: 'c-ag-4', subjectId: 's-agent', sortOrder: 4, title: 'RAG 链路：切分、召回与重排', duration: '66 分钟', status: 1,
    desc: '从切片到 RRF 融合的完整链路。',
    url: 'https://www.bilibili.com/video/BV1395x6AEvJ' },
  { id: 'c-ag-5', subjectId: 's-agent', sortOrder: 5, title: '多智能体的角色与协作模式', duration: '51 分钟', status: 1,
    desc: '主控 + 子角色的分工方式。',
    url: 'https://www.bilibili.com/video/BV1WWYE6LEzx' },
  { id: 'c-ag-6', subjectId: 's-agent', sortOrder: 6, title: '任务分派与状态机编排', duration: '57 分钟', status: 1,
    desc: '失败重试、降级与可观测性。',
    url: 'https://www.bilibili.com/video/BV1XexY6EEY1' },

  { id: 'c-jv-1', subjectId: 's-java', sortOrder: 1, title: '面向对象三大特性精讲', duration: '63 分钟', status: 1,
    desc: '封装、继承、多态与常见误区。',
    url: 'https://www.bilibili.com/video/BV1m6G26yEue' },
  { id: 'c-jv-2', subjectId: 's-java', sortOrder: 2, title: '集合框架：List / Map / Set', duration: '49 分钟', status: 1,
    desc: '底层结构与选型对比。',
    url: 'https://www.bilibili.com/video/BV1RFTc62EaK' },
  { id: 'c-jv-3', subjectId: 's-java', sortOrder: 3, title: 'Spring Boot 起步与自动装配', duration: '59 分钟', status: 1,
    desc: '起步依赖、自动配置与条件注解。',
    url: 'https://www.bilibili.com/video/BV1TLNn6HEsm' },
  { id: 'c-jv-4', subjectId: 's-java', sortOrder: 4, title: 'ORM 映射与事务处理', duration: '54 分钟', status: 1,
    desc: '实体映射、事务边界与失效场景。',
    url: 'https://www.bilibili.com/video/BV1395x6AEvJ' }
];

/* ---------------- 刷题题库（挂学科） ----------------
 * type: judge / single / multi / short
 * 判断题沿用素材做法：选项 A=正确、B=错误，答案存 A / B
 * 简答题录参考答案 + 解析，判分由 AI 对照参考答案打分
 */
DB.questions = [
  { id: 'q1', subjectId: 's-ai', type: 'judge', score: 10, difficulty: '简单', category: 'python核心', tags: ['python核心'],
    title: 'Python 中 list 是可变类型，tuple 是不可变类型。', answer: 'A',
    analysis: 'list 支持增删改；tuple 创建后元素不可变，但内部元素若为可变对象，其自身内容仍可变。' },
  { id: 'q2', subjectId: 's-ai', type: 'single', score: 10, difficulty: '简单', category: 'python核心', tags: ['python核心'],
    title: '下列哪种结构最适合做「键值映射」查找？',
    options: [{ k: 'A', t: 'list' }, { k: 'B', t: 'dict' }, { k: 'C', t: 'tuple' }, { k: 'D', t: 'set' }],
    answer: 'B', analysis: 'dict 基于哈希表实现，按 key 查找平均 O(1)；list 需遍历，set 不存键值对。' },
  { id: 'q3', subjectId: 's-ai', type: 'multi', score: 10, difficulty: '简单', category: 'python核心', tags: ['python核心'],
    title: '以下哪些属于 Python 的不可变类型？',
    options: [{ k: 'A', t: 'str' }, { k: 'B', t: 'list' }, { k: 'C', t: 'tuple' }, { k: 'D', t: 'dict' }],
    answer: ['A', 'C'], analysis: 'str 与 tuple 不可变；list 与 dict 可变，因此不能作为 dict 的 key。' },
  { id: 'q4', subjectId: 's-ai', type: 'short', score: 20, difficulty: '中等', category: 'python核心', tags: ['python核心'],
    title: '简述 Python 中 with 语句的作用，以及它依赖的两个魔术方法。',
    answer: 'with 用于上下文管理，保证资源在代码块结束时被正确释放（即使发生异常）。进入代码块时调用 __enter__，退出时调用 __exit__；__exit__ 返回 True 可吞掉异常。',
    analysis: '答题要点：①自动释放资源、异常也生效；②__enter__ 进入；③__exit__ 退出并可返回 True 抑制异常。' },

  { id: 'q5', subjectId: 's-ai', type: 'judge', score: 10, difficulty: '简单', category: 'Web后端', tags: ['HTTP'],
    title: 'HTTP 状态码 404 表示服务端内部错误。', answer: 'B',
    analysis: '404 是资源未找到；服务端内部错误是 500。' },
  { id: 'q6', subjectId: 's-ai', type: 'single', score: 10, difficulty: '简单', category: 'Web后端', tags: ['RESTful'],
    title: 'RESTful 风格中，获取某个资源应该使用哪个方法？',
    options: [{ k: 'A', t: 'GET' }, { k: 'B', t: 'POST' }, { k: 'C', t: 'PUT' }, { k: 'D', t: 'DELETE' }],
    answer: 'A', analysis: 'GET 用于查询，语义安全且幂等；POST 新增、PUT 全量更新、DELETE 删除。' },
  { id: 'q7', subjectId: 's-ai', type: 'multi', score: 10, difficulty: '中等', category: 'Web后端', tags: ['接口安全'],
    title: '下列哪些做法有助于接口安全？',
    options: [{ k: 'A', t: '对入参做校验' }, { k: 'B', t: '接口不鉴权以提升性能' }, { k: 'C', t: '敏感信息不写日志' }, { k: 'D', t: '统一异常返回' }],
    answer: ['A', 'C', 'D'], analysis: '接口必须鉴权，B 错误；A、C、D 分别为入参校验、敏感数据保护、避免异常信息泄露。' },
  { id: 'q8', subjectId: 's-ai', type: 'short', score: 20, difficulty: '中等', category: 'Web后端', tags: ['数据库'],
    title: '说明数据库索引为什么能加速查询，以及索引过多会带来什么问题。',
    answer: '索引本质是额外维护的有序数据结构（如 B+ 树），查询时可快速定位数据页，减少全表扫描。代价是写入时要同步维护索引、占用磁盘空间，索引过多会拖慢增删改并增加优化器选择成本。',
    analysis: '要点：①索引是有序结构可快速定位；②减少全表扫描/减少 IO；③写放大与空间占用；④过多索引拖慢写入。' },

  { id: 'q9', subjectId: 's-ai', type: 'judge', score: 10, difficulty: '简单', category: '大模型应用', tags: ['Prompt'],
    title: '提示词中要求「输出必须是 JSON」属于对输出格式的约束。', answer: 'A',
    analysis: '属于格式约束，通常还需配合示例或结构化输出能力保证稳定性。' },
  { id: 'q10', subjectId: 's-ai', type: 'single', score: 10, difficulty: '简单', category: '大模型应用', tags: ['Prompt'],
    title: '少样本提示（few-shot）的主要作用是？',
    options: [{ k: 'A', t: '降低模型参数量' }, { k: 'B', t: '用示例引导输出模式' }, { k: 'C', t: '加快网络传输' }, { k: 'D', t: '替代向量检索' }],
    answer: 'B', analysis: 'few-shot 通过示例让模型模仿输出结构与风格，不改模型参数。' },
  { id: 'q11', subjectId: 's-ai', type: 'short', score: 20, difficulty: '中等', category: '大模型应用', tags: ['上下文'],
    title: '上下文过长会导致哪些问题？请给出两种缓解思路。',
    answer: '问题：超出模型窗口被截断、关键信息被淹没、调用成本与延迟上升。缓解：①按任务切分上下文，只保留相关片段（检索/摘要）；②做历史对话压缩或结构化记忆；③分段处理再汇总。',
    analysis: '需同时写到「成本/延迟」与「信息丢失」两类问题，并给出可执行的两种缓解手段。' },

  { id: 'q12', subjectId: 's-agent', type: 'judge', score: 10, difficulty: '简单', category: 'Prompt工程', tags: ['Prompt'],
    title: '提示词越长，模型输出质量一定越好。', answer: 'B',
    analysis: '长度不等于质量，冗余信息会稀释关键指令，反而降低稳定性。' },
  { id: 'q13', subjectId: 's-agent', type: 'single', score: 10, difficulty: '简单', category: 'Prompt工程', tags: ['输出约束'],
    title: '要保证模型输出可被程序解析，最直接的做法是？',
    options: [{ k: 'A', t: '把温度调到最大' }, { k: 'B', t: '约定输出结构并校验/重试' }, { k: 'C', t: '删掉所有示例' }, { k: 'D', t: '增加无关背景描述' }],
    answer: 'B', analysis: '明确结构（如 JSON Schema）+ 解析失败重试，是工程上最稳的做法。' },
  { id: 'q14', subjectId: 's-agent', type: 'short', score: 20, difficulty: '中等', category: 'Prompt工程', tags: ['Prompt'],
    title: '你如何判断一条提示词写得好不好？请说明你的评估方法。',
    answer: '做法：先明确任务目标与验收标准，构造覆盖正常与边界情况的测试集，用固定输入批量跑，比较输出正确率、格式合规率与稳定性；对失败样本定位是信息缺失、歧义还是约束不足，再迭代提示词。',
    analysis: '要点：①有明确验收标准；②有测试集与固定输入；③量化指标；④失败归因再迭代。' },

  { id: 'q15', subjectId: 's-agent', type: 'single', score: 10, difficulty: '中等', category: 'RAG', tags: ['RAG'],
    title: 'RAG 中「重排（rerank）」的作用是？',
    options: [{ k: 'A', t: '扩大召回数量' }, { k: 'B', t: '对召回结果重新排序以提升相关性' }, { k: 'C', t: '压缩模型体积' }, { k: 'D', t: '替换向量库' }],
    answer: 'B', analysis: '向量召回偏粗排，rerank 用更精细的相关性模型对候选重新打分排序。' },
  { id: 'q16', subjectId: 's-agent', type: 'judge', score: 10, difficulty: '简单', category: '工具调用', tags: ['function calling'],
    title: '工具调用（function calling）中，模型直接执行本地函数并把结果返回给前端。', answer: 'B',
    analysis: '模型只输出调用意图与参数，实际执行由服务端完成，再把结果回灌给模型继续推理。' },
  { id: 'q17', subjectId: 's-agent', type: 'short', score: 20, difficulty: '中等', category: '工具调用', tags: ['function calling'],
    title: '简述一次完整的工具调用流程中，服务端需要做哪些事情。',
    answer: '服务端：①把工具的描述与参数结构提供给模型；②接收模型返回的调用意图并校验参数；③执行真实函数（鉴权、超时、重试、限流）；④把执行结果以工具消息回灌模型；⑤循环直到模型给出最终回答；⑥记录调用链便于排查。',
    analysis: '要点覆盖：工具注册与描述、参数校验、执行与异常处理、结果回灌、循环终止、可观测性。' },

  { id: 'q18', subjectId: 's-agent', type: 'single', score: 10, difficulty: '中等', category: '多智能体', tags: ['Agent'],
    title: '多智能体编排中，主控角色通常负责？',
    options: [{ k: 'A', t: '执行所有子任务' }, { k: 'B', t: '拆解任务并分派、汇总结果' }, { k: 'C', t: '只做日志记录' }, { k: 'D', t: '替代向量数据库' }],
    answer: 'B', analysis: '主控（orchestrator）负责任务拆解、分派与结果汇总，子 agent 各自执行专项任务。' },
  { id: 'q19', subjectId: 's-agent', type: 'short', score: 20, difficulty: '困难', category: '多智能体', tags: ['Agent'],
    title: '多个智能体协作时，任务分派失败你怎么处理？',
    answer: '先判断失败类型：参数不足则补充上下文重新分派；能力不匹配则改派其他 agent；执行超时则限制重试次数并降级为单 agent 兜底。同时记录调用链路与失败原因，必要时由主控重新规划任务分解。',
    analysis: '要点：区分失败类型、重试与上限、降级兜底、重新规划、可观测记录。' },

  { id: 'q20', subjectId: 's-java', type: 'single', score: 10, difficulty: '简单', category: 'JavaSE基础', tags: ['JavaSE基础'],
    title: '下列哪种类型不是作为 Collection 类型的集合？',
    options: [{ k: 'A', t: 'List' }, { k: 'B', t: 'Set' }, { k: 'C', t: 'Map' }, { k: 'D', t: 'Queue' }],
    answer: 'C', analysis: 'Map 与 Collection 是并列的顶级接口，Map 存键值对，不属于 Collection。' },
  { id: 'q21', subjectId: 's-java', type: 'multi', score: 10, difficulty: '简单', category: 'JavaSE基础', tags: ['JavaSE基础'],
    title: '以下哪些是 List 的实现类？',
    options: [{ k: 'A', t: 'ArrayList' }, { k: 'B', t: 'HashMap' }, { k: 'C', t: 'LinkedList' }, { k: 'D', t: 'HashSet' }],
    answer: ['A', 'C'], analysis: 'ArrayList 与 LinkedList 实现 List；HashMap 属 Map，HashSet 属 Set。' },
  { id: 'q22', subjectId: 's-java', type: 'short', score: 20, difficulty: '中等', category: 'JavaSE基础', tags: ['JavaSE基础'],
    title: '简述 == 与 equals 的区别。',
    answer: '== 对基本类型比较值，对引用类型比较地址；equals 是 Object 的方法，默认也是比较地址，String 等类重写后比较内容。重写 equals 必须同时重写 hashCode，否则放入哈希集合会出现重复元素。',
    analysis: '要点：== 比较值/地址、equals 默认地址、可重写比较内容、equals 与 hashCode 的契约。' },

  { id: 'q23', subjectId: 's-java', type: 'judge', score: 10, difficulty: '简单', category: 'SpringBoot', tags: ['Spring'],
    title: 'Spring Boot 的自动装配依赖 spring.factories 或 AutoConfiguration.imports 中的配置。', answer: 'A',
    analysis: '自动装配通过约定的配置文件声明候选配置类，再按条件注解筛选后注入容器。' },
  { id: 'q24', subjectId: 's-java', type: 'single', score: 10, difficulty: '中等', category: 'SpringBoot', tags: ['Spring'],
    title: '下列哪种情况最可能导致 @Transactional 失效？',
    options: [{ k: 'A', t: '方法被同类内部直接调用' }, { k: 'B', t: '方法声明为 public' }, { k: 'C', t: '使用了接口注入' }, { k: 'D', t: '异常未被捕获' }],
    answer: 'A', analysis: '同类内部调用不经过代理对象，事务切面不生效；这是最常见的失效场景。' },
  { id: 'q25', subjectId: 's-java', type: 'short', score: 20, difficulty: '中等', category: 'SpringBoot', tags: ['Spring'],
    title: '一个接口响应变慢，你会如何定位问题？',
    answer: '先看监控与日志确认是整体还是单接口变慢；再按链路分段：网关耗时、应用耗时（线程池/GC/锁）、数据库耗时（慢查询/索引）、外部依赖耗时。用链路追踪定位到具体跨度，再针对性优化。',
    analysis: '要点：确认范围 → 按链路分段 → 数据库与外部依赖 → 线程/GC → 用链路追踪定位。' }
];

/* ---------------- 面试资料库（上传 md / pdf → 转 md → 切分 → 向量化） ---------------- */
DB.interviewDocs = [
  { id: 'd1', name: 'AI面试题.pdf', type: 'pdf', size: '2.4 MB', status: 'ready', uploadedAt: '2026-10-26 10:12' },
  { id: 'd2', name: 'Python+AI面试题.pdf', type: 'pdf', size: '1.8 MB', status: 'ready', uploadedAt: '2026-10-26 10:20' },
  { id: 'd3', name: 'AI全栈开发-面试题.md', type: 'md', size: '132 KB', status: 'ready', uploadedAt: '2026-10-27 09:04' },
  { id: 'd4', name: 'Java面试.pdf', type: 'pdf', size: '3.1 MB', status: 'ready', uploadedAt: '2026-10-25 15:31' },
  { id: 'd5', name: '常见集合篇.pdf', type: 'pdf', size: '980 KB', status: 'ready', uploadedAt: '2026-10-25 15:33' },
  { id: 'd6', name: '多线程篇.pdf', type: 'pdf', size: '1.2 MB', status: 'ready', uploadedAt: '2026-10-25 15:35' },
  { id: 'd7', name: 'JVM虚拟机篇.pdf', type: 'pdf', size: '1.6 MB', status: 'ready', uploadedAt: '2026-10-25 15:37' },
  { id: 'd8', name: 'MySQL篇.pdf', type: 'pdf', size: '2.2 MB', status: 'ready', uploadedAt: '2026-10-25 15:40' },
  { id: 'd9', name: 'Redis篇.pdf', type: 'pdf', size: '1.4 MB', status: 'ready', uploadedAt: '2026-10-25 15:42' },
  { id: 'd10', name: '微服务篇.pdf', type: 'pdf', size: '1.9 MB', status: 'ready', uploadedAt: '2026-10-25 15:45' },
  { id: 'd11', name: '消息中间件篇.pdf', type: 'pdf', size: '1.1 MB', status: 'converting', uploadedAt: '2026-11-01 09:12' },
  { id: 'd12', name: '设计模式篇.pdf', type: 'pdf', size: '760 KB', status: 'pending', uploadedAt: '2026-11-01 09:20' },
  { id: 'd13', name: '技术场景篇.pdf', type: 'pdf', size: '1.3 MB', status: 'ready', uploadedAt: '2026-10-25 15:48' },
  { id: 'd14', name: 'SSM框架.pdf', type: 'pdf', size: '2.0 MB', status: 'ready', uploadedAt: '2026-10-25 15:50' }
];

DB.interviewSnippets = [
  { id: 'sn1', docId: 'd1', question: '请介绍一下你在项目中使用 Python 处理数据时，遇到过的最棘手的问题。',
    snippet: '数据处理实战：编码不一致、缺失值填充、大文件内存占用……' },
  { id: 'sn2', docId: 'd2', question: 'Python 的 GIL 是什么？它对多线程程序有什么影响？',
    snippet: 'GIL 全局解释器锁：同一时刻只有一个线程执行字节码，IO 密集可缓解，CPU 密集需多进程。' },
  { id: 'sn3', docId: 'd1', question: '设计一个课程列表接口，你会如何考虑分页、过滤与返回结构？',
    snippet: '接口设计：分页参数 page/pageSize、过滤条件、统一响应体、空结果处理。' },
  { id: 'sn4', docId: 'd1', question: '数据库出现慢查询时，你的排查顺序是什么？',
    snippet: '慢查询定位：慢日志 → 执行计划 → 索引命中 → 数据量 → 锁等待。' },
  { id: 'sn5', docId: 'd2', question: '如果要让大模型稳定输出结构化数据，你会怎么设计提示词与校验？',
    snippet: '结构化输出：约定 JSON 结构、给少量示例、解析失败重试、字段级校验。' },
  { id: 'sn6', docId: 'd2', question: '流式输出的好处是什么？前端如何处理不完整的分片？',
    snippet: '流式输出：降低首字延迟；SSE 分片可能被截断，需按分隔符缓冲后再渲染。' },

  { id: 'sn7', docId: 'd3', question: '你如何判断一条提示词写得好不好？有没有自己的评估方法？',
    snippet: '提示词评估：固定测试集、输出正确率、格式合规率、稳定性对比。' },
  { id: 'sn8', docId: 'd3', question: '模型输出格式不稳定时，你会从哪几个方面排查？',
    snippet: '格式排查：约束是否明确、示例是否冲突、温度参数、解析与重试策略。' },
  { id: 'sn9', docId: 'd3', question: 'RAG 召回的文档质量很差，你会有哪些优化方向？',
    snippet: 'RAG 优化：切分粒度、混合检索、rerank 重排、查询改写、元数据过滤。' },
  { id: 'sn10', docId: 'd3', question: '工具调用中如何避免模型乱调用、重复调用工具？',
    snippet: '工具调用约束：工具描述清晰、参数 schema 校验、幂等设计、调用轮次上限。' },
  { id: 'sn11', docId: 'd3', question: '多个智能体协作时，任务分派失败你怎么处理？',
    snippet: '多智能体编排：超时重试、能力匹配改派、降级单 agent、主控重新规划。' },
  { id: 'sn12', docId: 'd3', question: '多智能体系统应该如何做可观测性？你会记录哪些信息？',
    snippet: '可观测性：调用链、每步输入输出、工具耗时、失败原因、token 消耗。' },

  { id: 'sn13', docId: 'd5', question: 'HashMap 的底层结构是什么？扩容时发生了什么？',
    snippet: 'HashMap：数组 + 链表 + 红黑树，负载因子 0.75，扩容重新计算索引。' },
  { id: 'sn14', docId: 'd4', question: '说说你对面向对象中「多态」的理解，并举一个实际例子。',
    snippet: '多态：父类引用指向子类对象，运行时决定调用哪个实现。' },
  { id: 'sn15', docId: 'd6', question: 'Java 线程池的核心参数有哪些？为什么要限制队列长度？',
    snippet: '线程池参数：corePoolSize、maximumPoolSize、keepAliveTime、workQueue、拒绝策略。' },
  { id: 'sn16', docId: 'd14', question: 'Spring Boot 的自动装配原理是什么？',
    snippet: '自动装配：AutoConfiguration.imports 声明候选类，条件注解筛选后注册 Bean。' },
  { id: 'sn17', docId: 'd8', question: '事务在什么情况下会失效？你遇到过吗？',
    snippet: '事务失效：同类内部调用、非 public 方法、异常被吞、传播行为设置不当。' },
  { id: 'sn18', docId: 'd13', question: '一个接口响应变慢，你会如何定位问题？',
    snippet: '接口变慢排查：整体还是单接口、链路分段耗时、慢 SQL、外部依赖、GC。' }
];

/* ---------------- 简历面试 ---------------- */
DB.resumeProjects = [
  { name: '校园二手交易平台', stack: 'Spring Boot + MySQL + Redis', role: '后端主力' },
  { name: '智能客服 Agent', stack: 'Python + LangChain + Milvus', role: '独立开发' }
];

DB.resumeSnippets = [
  { id: 'rs1', project: '校园二手交易平台',
    question: '简历里写到你在校园二手交易平台负责后端，具体承担了哪些模块？',
    snippet: '项目经历：校园二手交易平台（Spring Boot + MySQL + Redis），负责商品、订单、支付回调三个模块。' },
  { id: 'rs2', project: '校园二手交易平台',
    question: '这个平台在订单写入压力变大时你做了什么优化？效果如何量化？',
    snippet: '订单写入峰值约 800 QPS，通过异步下单 + Redis 预扣库存 + 分库分表缓解。' },
  { id: 'rs3', project: '智能客服 Agent',
    question: '你独立开发的智能客服 Agent 如何保证回答不跑偏？检索和提示词分别起了什么作用？',
    snippet: '智能客服 Agent（Python + LangChain + Milvus），RAG 召回 + 工具调用，回答准确率从 62% 提升到 84%。' },
  { id: 'rs4', project: '智能客服 Agent',
    question: '简历里准确率从 62% 提升到 84%，这个指标是怎么定义和统计的？',
    snippet: '评测集 300 条人工标注问答，命中关键要点记为正确。' },
  { id: 'rs5', project: '',
    question: '简历里列了 Redis，你在项目里用它解决了什么问题？为什么不让数据库直接扛？',
    snippet: '技能：Redis 缓存、分布式锁、预扣库存。' },
  { id: 'rs6', project: '',
    question: '你最近一年主要做后端与 AI 应用，接下来希望往哪个方向深入？为什么？',
    snippet: '求职意向：AI 应用开发 / 后端。' }
];

/* ---------------- 后台：学员 / 管理员 / 日志 / 看板 ---------------- */
DB.students = [
  { id: 'u1', phone: '138****2211', nickname: '小北', registeredAt: '2026-10-02', doneCourses: 6, status: 1 },
  { id: 'u2', phone: '139****8830', nickname: '阿岚', registeredAt: '2026-10-08', doneCourses: 2, status: 1 },
  { id: 'u3', phone: '150****4477', nickname: 'Kevin', registeredAt: '2026-10-12', doneCourses: 4, status: 1 },
  { id: 'u4', phone: '186****0021', nickname: '橙子', registeredAt: '2026-10-19', doneCourses: 0, status: 0 },
  { id: 'u5', phone: '137****5566', nickname: '木木', registeredAt: '2026-10-24', doneCourses: 3, status: 1 },
  { id: 'u6', phone: '159****7788', nickname: '子夜', registeredAt: '2026-10-27', doneCourses: 1, status: 1 },
  { id: 'u7', phone: '135****9090', nickname: 'Luna', registeredAt: '2026-10-30', doneCourses: 0, status: 1 },
  { id: 'u8', phone: '133****1212', nickname: '老周', registeredAt: '2026-11-01', doneCourses: 0, status: 1 }
];

DB.adminUsers = [
  { id: 'a1', username: 'admin', role: '超管', createdAt: '2026-09-01', status: 1, protected: true },
  { id: 'a2', username: 'yunying01', role: '运营', createdAt: '2026-09-15', status: 1 },
  { id: 'a3', username: 'yunying02', role: '运营', createdAt: '2026-10-11', status: 1 },
  { id: 'a4', username: 'yunying03', role: '运营', createdAt: '2026-10-28', status: 0 }
];

DB.logs = [
  { id: 'l1', at: '2026-10-31 18:22', user: 'yunying01', module: '刷题题库', action: '导入', target: 'AI 全栈开发 · 11 题' },
  { id: 'l2', at: '2026-10-31 16:05', user: 'yunying01', module: '课程内容', action: '下架', target: '工程分层与依赖管理' },
  { id: 'l3', at: '2026-10-30 11:40', user: 'admin', module: '系统用户', action: '停用', target: 'yunying03' },
  { id: 'l4', at: '2026-10-29 20:17', user: 'yunying02', module: '课程内容', action: '新增', target: 'Agent 开发' },
  { id: 'l5', at: '2026-10-28 09:31', user: 'yunying01', module: '面试资料库', action: '导入', target: 'AI 全栈开发面试题 32 题' },
  { id: 'l6', at: '2026-10-27 15:09', user: 'admin', module: '课程内容', action: '上架', target: 'Java 开发' }
];

DB.dailyStats = [
  { day: '10-26', register: 12, active: 86 },
  { day: '10-27', register: 18, active: 94 },
  { day: '10-28', register: 9, active: 88 },
  { day: '10-29', register: 22, active: 103 },
  { day: '10-30', register: 15, active: 112 },
  { day: '10-31', register: 26, active: 121 },
  { day: '11-01', register: 14, active: 97 }
];

/* ---------------- 查询辅助 ---------------- */
function byId(list, id) {
  return list.find(function (item) { return item.id === id; });
}

function coursesOfSubject(subjectId) {
  return DB.courses
    .filter(function (c) { return c.subjectId === subjectId; })
    .sort(function (a, b) { return a.sortOrder - b.sortOrder; });
}

function questionsOfSubject(subjectId) {
  return DB.questions.filter(function (q) { return q.subjectId === subjectId; });
}

function searchSnippets(keywords) {
  const words = (keywords || []).map(function (w) { return String(w).toLowerCase(); });
  const scored = DB.interviewSnippets.map(function (s) {
    const text = (s.question + ' ' + s.snippet + ' ' + docName(s.docId)).toLowerCase();
    let hit = 0;
    words.forEach(function (w) { if (text.indexOf(w) > -1) hit += 1; });
    return { snippet: s, hit: hit };
  }).filter(function (x) { return x.hit > 0; });
  scored.sort(function (a, b) { return b.hit - a.hit; });
  return scored.map(function (x) { return x.snippet; });
}

function interviewQuestionsOfSubject(subjectId) {
  const subject = byId(DB.subjects, subjectId);
  return searchSnippets(subject ? subject.keywords : []);
}

function docName(docId) {
  const d = byId(DB.interviewDocs, docId);
  return d ? d.name : '';
}

/* ---------------- 学员状态（原型数据，保存在浏览器本地） ---------------- */
const STORAGE_KEY = 'yunshu-prototype-v3';

const state = {
  user: null,               // { phone, nickname, isAdmin }
  completedCourses: {},     // courseId -> true（节点点亮）
  visits: [],               // { courseId, at }
  papers: [],               // 答卷
  wrongBook: [],            // { qid, times, lastScore, addedAt }
  interviews: [],           // 面试记录
  interviewUsedToday: 0,    // 今日已发起面试次数
  resume: null,             // 简历：{ fileName, size, status, at }
  draftPaper: null,         // 进行中的答卷
  draftInterview: null      // 进行中的面试
};

function saveState() {
  const plain = {
    user: state.user,
    completedCourses: state.completedCourses,
    visits: state.visits,
    papers: state.papers,
    wrongBook: state.wrongBook,
    interviews: state.interviews,
    interviewUsedToday: state.interviewUsedToday,
    resume: state.resume
  };
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(plain)); } catch (e) { /* 忽略存储异常 */ }
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    Object.assign(state, JSON.parse(raw));
  } catch (e) { /* 忽略解析异常 */ }
}

loadState();
