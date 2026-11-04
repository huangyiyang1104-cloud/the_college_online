# 云枢智学 · 高校课程学习与 AI 面试平台

面向高校学生的「学 → 练 → 面」闭环系统：沿课程节点图学习并点亮、按学科整卷刷题、用 AI 语音面试检验掌握程度。

- **学员端**：首页、学科节点图、学习记录、刷题、错题本、AI 面试（语音播报 + 语音作答 + 逐题报告）、简历面试
- **管理端**：看板、学科与课程、题库、面试资料库、学员管理、系统账号、操作日志

---

## 一、技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.14 · FastAPI · SQLAlchemy 2 · Pydantic v2 |
| 数据库 | MySQL 8 · Redis 7 · MinIO（对象存储）· Milvus 2.5（向量库） |
| 学员端 | Vue 3 · TypeScript · Vite · Element Plus |
| 管理端 | Vue 3 · TypeScript · Vite · Element Plus（独立工程，`/admin/` 部署） |
| 大模型 | DeepSeek 4.1 Flash（出题 / 判分 / 追问 / 结语） |
| Embedding | 阿里云 DashScope `qwen3.7-text-embedding`（1024 维） |
| 语音 | 腾讯云 TTS（超自然大模型音色）+ 一句话识别 ASR |
| 变声 | RVC（独立 Python 3.11 微服务，本地 GPU，tomorin 音色） |
| 部署 | Nginx + Docker Compose |

后端严格三层：`api/`（controller，只做 HTTP 编排）→ `services/`（业务规则、事务边界）→ `repositories/`（全部 SQL）。

---

## 二、功能清单

### 学员端

| 模块 | 接口 | 说明 |
|---|---|---|
| C1 认证 | 6 | 手机号验证码注册（阿里云号码认证）、密码登录、双 token 刷新、退出、个人信息 |
| C2 学科节点图 | 6 | 首页聚合、学科列表、节点图、访问流水（按天去重）、点亮/取消（幂等） |
| C3 学习记录 | 2 | 记录列表（可按学科筛选）、统计汇总 |
| C4 刷题 | 5 | 随机组卷 20 题、提交判分（客观题即时 / 简答题 LLM 同步）、答卷列表与详情 |
| C5 错题本 | 4 | 列表、重做、移除、统计 |
| C6 AI 面试 | 11 | 配额、发起（资料库检索 + LLM 出题）、作答评分、追问、结束、语音音频、ASR 转写、结语语音、WS 票据、记录列表 |
| C7 简历面试 | 3 | PDF 上传、解析状态、删除；发起走 C6 的 `source=2` |
| C8 报告 | 1 | 逐题分数、回答、追问、点评、来源文档 |

### 管理端

| 模块 | 说明 |
|---|---|
| B1 看板 | 规模与活跃指标、注册趋势 |
| B2 学科与课程 | 学科 CRUD、课程 CRUD + 排序、课程/题库 Excel 导入（预览 + 确认两段式） |
| B3 题库 | 四类题型（判断/单选/多选/简答）维护 |
| B4 面试资料库 | 上传 → 切分 → 向量化入库、重试、删除、检索测试 |
| B5 学员 | 列表、启停用 |
| B6 系统账号 | CRUD、停用 |
| B7 操作日志 | 写操作审计 |

---

## 三、目录结构

```
the_college_online/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # controller（admin / student）
│   │   ├── services/        # 业务逻辑
│   │   ├── repositories/    # 数据访问
│   │   ├── integrations/    # LLM / embedding / Milvus / MinIO / TTS / ASR / RVC / PDF
│   │   ├── core/            # 配置、数据库、缓存、鉴权、错误码
│   │   ├── models.py        # ORM 模型
│   │   └── schemas.py       # 请求/响应模型
│   ├── scripts/             # 自检与冒烟脚本
│   ├── requirements.txt
│   └── Dockerfile
├── frontend-student/        # 学员端（base = /）
├── frontend-admin/          # 管理端（base = /admin/）
├── rvc-service/             # RVC 变声微服务（独立 Python 3.11）
├── deploy/                  # docker compose / nginx / 一键部署
├── scripts/sql/schema.sql   # 建库脚本
├── docs/                    # PRD、设计文档、接口文档
└── prototype/               # 早期交互原型（仅参考）
```

---

## 四、快速开始（本地开发）

### 1. 环境要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.14 | 后端（纯 Python 依赖都支持） |
| Python | 3.11 | **仅 RVC 微服务**，它依赖 `infer_rvc_python`，老版本才支持 |
| Node.js | 18+ | 两个前端 |
| Docker Desktop | 最新 | MySQL / Redis / MinIO / Milvus |
| NVIDIA GPU | 显存 ≥ 6GB | RVC 变声（没有可跳过，语音退化为 TTS 原声） |

### 2. 启动基础设施

```bash
cd deploy
copy .env.example .env          # 首次
docker compose up -d            # 只起基础设施（mysql/redis/minio/milvus/etcd）
```

宿主机端口（**注意不是默认端口**）：

| 服务 | 端口 |
|---|---|
| MySQL | **3307**（3306 常被本机 MySQL 占用） |
| Redis | 6379 |
| MinIO API / 控制台 | **19000 / 19001**（9000 落在 Windows Hyper-V 保留段） |
| Milvus | 19530，指标 19091 |

### 3. 配置

```bash
cd backend
copy .env.example .env
```

必填项：

| 变量 | 说明 |
|---|---|
| `MYSQL_PASSWORD` / `REDIS_PASSWORD` / `MINIO_SECRET_KEY` | 与 `deploy/.env` 保持一致 |
| `JWT_SECRET` | 32 位随机十六进制 |
| `DEEPSEEK_API_KEY` | 出题 / 判分 / 追问 |
| `DASHSCOPE_API_KEY` | Embedding |
| `TENCENT_SECRET_ID` / `_SECRET_KEY` / `_APP_ID` | TTS + ASR |
| `ALIYUN_PNVS_*` | 注册短信（测试号码白名单，不产生费用） |
| `AUTH_TEST_PHONES` | 允许注册的手机号，逗号分隔 |

自检：

```bash
cd backend
.venv\Scripts\python.exe scripts\audit_env.py     # 键是否齐全
.venv\Scripts\python.exe scripts\check_config.py  # 值是否填了
```

### 4. 启动后端

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. 启动前端

```bash
cd frontend-student && npm install && npm run dev    # http://localhost:5173
cd frontend-admin   && npm install && npm run dev    # http://localhost:5174/admin/
```

两个前端都通过 Vite 代理把 `/api` 转发到 `127.0.0.1:8000`。

### 6. 启动 RVC 变声（可选）

```powershell
# 首次：建独立环境（Python 3.11）
C:\Python311\python.exe -m venv D:\rvc-venv
D:\rvc-venv\Scripts\pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
D:\rvc-venv\Scripts\pip install infer_rvc_python librosa faiss-cpu soundfile fastapi "uvicorn[standard]"

# 模型放纯英文路径（faiss 读不了中文路径）
#   D:\rvc-venv\models\tomorin\tomorin.pth + tomorin.index
#   D:\rvc-venv\models\hubert_base\ + rmvpe.pt + ffmpeg.exe

# 启动
powershell -ExecutionPolicy Bypass -File D:\rvc-venv\start_service.ps1
```

没有 RVC 时把 `backend/.env` 的 `RVC_ENABLED` 设为 `false`，语音只播 TTS 原声。

---

## 五、部署（容器化）

```powershell
cd deploy
powershell -ExecutionPolicy Bypass -File .\up.ps1
```

脚本会依次：生成管理端 Basic Auth 凭据 → 构建两个前端 → 构建后端镜像 → 起容器 → 同步管理员密码 → 启动 RVC → 健康检查。

访问：

| 入口 | 地址 |
|---|---|
| 学员端 | `http://localhost/` |
| 管理端 | `http://localhost/admin/`（Basic Auth，凭据见 `deploy/.env`） |

关键设计：

- **RVC 不进容器**：需要 GPU，留在宿主机；容器通过 `host.docker.internal:8010` 访问
- **管理端双保险**：nginx Basic Auth + 业务登录，两道密码分开配置
- **接口文档在公网时自动屏蔽**：`/api/docs`、`/api/openapi.json` 返回 404
- **限流**：登录注册 10 次/分钟，普通接口 20 次/秒（按 IP）

---

## 六、测试

```bash
cd backend
.venv\Scripts\python.exe scripts\run_all_smoke.py
```

会依次跑 7 套冒烟并汇总，共 **127 项断言**：

| 套件 | 项数 | 覆盖 |
|---|---|---|
| `smoke_admin.py` | 26 | 管理端全模块 |
| `smoke_student.py` | 14 | C1 认证 |
| `smoke_catalog.py` | 25 | C2 节点图 + C3 记录 |
| `smoke_practice.py` | 19 | C4 刷题 |
| `smoke_wrong.py` | 18 | C5 错题本 |
| `smoke_import.py` | 11 | Excel 导入 |
| `smoke_interview.py` | 14 | C6 面试全链路 |

专项自检：

```bash
python scripts/check_asr.py            # TTS → ASR 回读比对
python scripts/check_audio_pipeline.py # TTS → RVC → MinIO
python scripts/check_resume.py         # 造 PDF → 上传 → 解析 → 简历面试
python scripts/check_verdict_audio.py  # 结算 → 结语音频
```

---

## 七、密码与密钥管理

密码分三层，各管一段：

| 文件 | 管什么 |
|---|---|
| `deploy/.env` | 容器基础设施：MySQL / Redis / MinIO 的 root 密码 |
| `deploy/.env` | 管理端入口：`NGINX_BASIC_AUTH_USER` / `_PASSWORD` |
| `backend/.env` | 应用连接、`JWT_SECRET`、云厂商 Key、`ADMIN_INIT_PASSWORD` |

改密码：

```bash
# 管理端业务登录密码
cd backend && .venv\Scripts\python.exe scripts\reset_admin_password.py

# 管理端 Basic Auth 密码
cd deploy && ..\backend\.venv\Scripts\python.exe gen_htpasswd.py
docker compose restart nginx
```

> ⚠️ `.env` 已被 `.gitignore` 排除，**不要提交**。仓库里只有 `.env.example` 模板。

---

## 八、常见问题

**后端启动报 `Can't connect to MySQL`**
Docker Desktop 没启动。检查 `docker ps`，容器会自动恢复（`restart: unless-stopped`）。

**MinIO 连不上 / 语音上传失败**
`MINIO_ENDPOINT` 只能写 `host:port`，**不要带 `http://`**（SDK 会解析失败）。

**RVC 报 `could not open ...tomorin.index`**
模型目录含中文，faiss 用 C 的 `fopen` 读不了。把模型复制到纯英文路径。

**RVC 第一次推理特别慢**
首次会加载 hubert + rmvpe，约 10–20 秒；之后每段约 2.4 秒。

**微信/手机浏览器点麦克风没反应**
非 HTTPS 且非 localhost 时浏览器拒绝 `getUserMedia`。本地用 `localhost` 访问，或给站点配 HTTPS。

**面试出题偶尔 503**
大模型偶发超时。已内置一次重试 + 日志，业务侧提示“出题服务繁忙”，重试即可。

**简历上传后提示“可能是扫描件”**
图片型 PDF 没有文字层，无法提取。换文字版 PDF。

---

## 九、设计文档

| 文件 | 内容 |
|---|---|
| `docs/PRD.md` | 产品需求 |
| `docs/design/04.API接口设计.md` | 71 个 HTTP 接口 + 1 个 WS 的完整契约与错误码 |
| `docs/design/` 其余 | 架构、数据模型、交互设计 |
| `docs/CODEBUDDY.md` | 工程约定（分层规则、注释要求） |

---

## 十、说明

本项目为课程设计/毕业设计作品，语音与短信走云厂商**免费额度**（腾讯云 TTS 2 万字符、ASR 每月 5000 次、阿里云号码认证测试号码），额度用尽会停服而非扣费。
