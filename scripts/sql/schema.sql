-- ============================================================
-- 云枢智学 · MySQL 8.0 建表脚本
-- 依据：docs/design/03.数据库设计.md、docs/rules/database-rules.md
-- 版本：v2.0（内容主干调整：取消「阶段」与「学习路线」，改为学科内课程线性节点图）
--
-- 约定（与规范一致）：
--   1. 表名与字段名统一 snake_case，表名使用单数
--   2. 主键统一 `id` BIGINT UNSIGNED 自增
--   3. 禁止物理外键：表之间用 xxx_id 逻辑关联，由应用层校验
--   4. 时间字段统一 created_at / updated_at，存 UTC
--   5. 内容类表统一软删除：deleted_at（默认 1970-01-01，未删除即该默认值）
--      —— 之所以不用 NULL，是为了让 (业务唯一键, deleted_at) 组合唯一索引持续生效
--   6. 多值属性拆表（学科检索关键词、题目标签、答卷多选）
--   7. 状态字段统一 TINYINT UNSIGNED，取值见设计文档"状态字典"
-- ============================================================

SET NAMES utf8mb4;

-- ------------------------------------------------------------
-- 一、账号与权限
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `user` (
  `id`            BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `phone`         VARCHAR(20)      NOT NULL                COMMENT '手机号，唯一登录账号',
  `password_hash` VARCHAR(100)     NOT NULL                COMMENT '密码哈希',
  `nickname`      VARCHAR(64)      NOT NULL DEFAULT ''     COMMENT '昵称',
  `city`          VARCHAR(64)      NOT NULL DEFAULT ''     COMMENT '所在城市',
  `status`        TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 正常，0 禁用',
  `last_login_at` DATETIME         NULL                    COMMENT '最近登录时间（UTC）',
  `created_at`    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间（UTC）',
  `updated_at`    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_phone` (`phone`),
  KEY `idx_user_created_at` (`created_at`),
  KEY `idx_user_status` (`status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '学员账号';

CREATE TABLE IF NOT EXISTS `admin_user` (
  `id`            BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username`      VARCHAR(64)      NOT NULL                COMMENT '后台登录账号',
  `password_hash` VARCHAR(100)     NOT NULL                COMMENT '密码哈希',
  `role`          TINYINT UNSIGNED NOT NULL DEFAULT 2      COMMENT '角色：1 超管，2 运营',
  `is_builtin`    TINYINT UNSIGNED NOT NULL DEFAULT 0      COMMENT '是否内置账号：1 是（不可删除/停用），0 否',
  `status`        TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 启用，0 停用',
  `created_at`    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `updated_at`    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_admin_user_username` (`username`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '后台账号';

CREATE TABLE IF NOT EXISTS `user_login_log` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`    BIGINT UNSIGNED NOT NULL                COMMENT '学员 id（逻辑关联 user.id）',
  `login_at`   DATETIME        NOT NULL                COMMENT '登录时间（UTC），活跃度统计依据',
  `ip`         VARCHAR(45)     NOT NULL DEFAULT ''     COMMENT '登录 IP（兼容 IPv6）',
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_user_login_log_user_time` (`user_id`, `login_at`),
  KEY `idx_user_login_log_login_at` (`login_at`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '学员登录日志（日/周活口径：近 7 天去重）';

-- ------------------------------------------------------------
-- 二、内容主干：学科 → 课程（线性学习顺序）
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `subject` (
  `id`          BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name`        VARCHAR(64)      NOT NULL                COMMENT '学科名称',
  `icon`        VARCHAR(16)      NOT NULL DEFAULT ''     COMMENT '图标（emoji）',
  `description` VARCHAR(512)     NOT NULL DEFAULT ''     COMMENT '简介',
  `sort_order`  INT UNSIGNED     NOT NULL DEFAULT 0      COMMENT '学科展示排序，越小越靠前',
  `status`      TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 上架，0 下架',
  `deleted_at`  DATETIME         NOT NULL DEFAULT '1970-01-01 00:00:00' COMMENT '软删除时间，默认值表示未删除',
  `created_at`  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `updated_at`  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_subject_name_deleted` (`name`, `deleted_at`),
  KEY `idx_subject_status_sort` (`status`, `sort_order`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '学科（一条学习路径）';

CREATE TABLE IF NOT EXISTS `subject_keyword` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `subject_id` BIGINT UNSIGNED NOT NULL                COMMENT '学科 id（逻辑关联 subject.id）',
  `keyword`    VARCHAR(64)     NOT NULL                COMMENT '检索关键词，AI 面试取题的 query 来源',
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_subject_keyword` (`subject_id`, `keyword`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '学科检索关键词（多值拆表）';

CREATE TABLE IF NOT EXISTS `course` (
  `id`               BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `subject_id`       BIGINT UNSIGNED  NOT NULL                COMMENT '所属学科 id（逻辑关联 subject.id）',
  `title`            VARCHAR(255)     NOT NULL                COMMENT '课程标题（= 节点名）',
  `description`      VARCHAR(512)     NOT NULL DEFAULT ''     COMMENT '课程简介，用于节点悬浮说明',
  `duration_minutes` INT UNSIGNED     NOT NULL DEFAULT 0      COMMENT '时长（分钟）',
  `bilibili_url`     VARCHAR(512)     NOT NULL                COMMENT 'B 站播放地址（完整链接）',
  `sort_order`       INT UNSIGNED     NOT NULL DEFAULT 0      COMMENT '学科内学习顺序，节点图按此排列',
  `status`           TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 上架，0 下架',
  `deleted_at`       DATETIME         NOT NULL DEFAULT '1970-01-01 00:00:00' COMMENT '软删除时间',
  `created_at`       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `updated_at`       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_subject_title_deleted` (`subject_id`, `title`, `deleted_at`),
  KEY `idx_course_subject_sort` (`subject_id`, `sort_order`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '课程（学习路径上的节点，仅跳转 B 站）';

-- ------------------------------------------------------------
-- 三、学习行为：访问流水 / 节点点亮
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `learning_visit` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`    BIGINT UNSIGNED NOT NULL                COMMENT '学员 id（逻辑关联 user.id）',
  `course_id`  BIGINT UNSIGNED NOT NULL                COMMENT '课程 id（逻辑关联 course.id）',
  `visited_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '访问时间（UTC），点击节点跳转时写入',
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_visit_user_time` (`user_id`, `visited_at`),
  KEY `idx_visit_course` (`course_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '课程访问流水';

CREATE TABLE IF NOT EXISTS `course_completion` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`      BIGINT UNSIGNED NOT NULL                COMMENT '学员 id（逻辑关联 user.id）',
  `course_id`    BIGINT UNSIGNED NOT NULL                COMMENT '课程 id（逻辑关联 course.id）',
  `completed_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点亮时间（UTC）',
  `created_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_completion` (`user_id`, `course_id`),
  KEY `idx_course_completion_course` (`course_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '节点点亮状态（学员手动标记）';

-- ------------------------------------------------------------
-- 四、刷题题库（题目挂学科，整学科组卷）
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `question` (
  `id`               BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `subject_id`       BIGINT UNSIGNED  NOT NULL                COMMENT '所属学科 id（逻辑关联 subject.id）',
  `type`             TINYINT UNSIGNED NOT NULL                COMMENT '题型：1 判断，2 单选，3 多选，4 简答',
  `difficulty`       TINYINT UNSIGNED NOT NULL DEFAULT 2      COMMENT '难度：1 简单，2 中等，3 困难',
  `category`         VARCHAR(64)      NOT NULL DEFAULT ''     COMMENT '分类（对齐导入模板的分类列）',
  `title`            TEXT             NOT NULL                COMMENT '题干',
  `score`            DECIMAL(5, 2)    NOT NULL DEFAULT 10.00  COMMENT '分值',
  `reference_answer` TEXT             NULL                    COMMENT '简答题参考答案；客观题为空，答案由 question_option.is_correct 表达',
  `analysis`         TEXT             NULL                    COMMENT '解析 / 评分要点',
  `status`           TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 启用，0 停用',
  `deleted_at`       DATETIME         NOT NULL DEFAULT '1970-01-01 00:00:00' COMMENT '软删除时间',
  `created_at`       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `updated_at`       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_question_subject_type` (`subject_id`, `type`),
  KEY `idx_question_status` (`status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '刷题题目（挂学科）';

CREATE TABLE IF NOT EXISTS `question_option` (
  `id`          BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `question_id` BIGINT UNSIGNED  NOT NULL                COMMENT '题目 id（逻辑关联 question.id）',
  `option_key`  CHAR(1)          NOT NULL                COMMENT '选项标识：A / B / C …（判断题固定 A 正确、B 错误）',
  `content`     VARCHAR(512)     NOT NULL                COMMENT '选项内容',
  `is_correct`  TINYINT UNSIGNED NOT NULL DEFAULT 0      COMMENT '是否正确答案：1 是，0 否',
  `sort_order`  INT UNSIGNED     NOT NULL DEFAULT 0      COMMENT '展示顺序',
  `created_at`  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_option_key` (`question_id`, `option_key`),
  KEY `idx_option_question_correct` (`question_id`, `is_correct`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '题目选项（客观题答案由此表表达）';

CREATE TABLE IF NOT EXISTS `question_tag` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `question_id` BIGINT UNSIGNED NOT NULL                COMMENT '题目 id（逻辑关联 question.id）',
  `tag_name`    VARCHAR(32)     NOT NULL                COMMENT '标签名（对齐导入模板的标签列）',
  `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_question_tag` (`question_id`, `tag_name`),
  KEY `idx_tag_name` (`tag_name`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '题目标签（多值拆表）';

-- ------------------------------------------------------------
-- 五、答卷与错题本
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `exam_paper` (
  `id`             BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`        BIGINT UNSIGNED  NOT NULL                COMMENT '学员 id（逻辑关联 user.id）',
  `subject_id`     BIGINT UNSIGNED  NOT NULL                COMMENT '组卷学科 id（逻辑关联 subject.id）',
  `question_count` INT UNSIGNED     NOT NULL DEFAULT 0      COMMENT '题目数',
  `total_score`    DECIMAL(6, 2)    NOT NULL DEFAULT 0.00   COMMENT '试卷总分',
  `obtained_score` DECIMAL(6, 2)    NULL                    COMMENT '得分；判分中为空',
  `status`         TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 判分中，2 已完成',
  `submitted_at`   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间（UTC）',
  `created_at`     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `updated_at`     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_paper_user_time` (`user_id`, `submitted_at`),
  KEY `idx_paper_subject` (`subject_id`),
  KEY `idx_paper_status` (`status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '答卷（整卷提交）';

CREATE TABLE IF NOT EXISTS `exam_answer` (
  `id`               BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `paper_id`         BIGINT UNSIGNED  NOT NULL                COMMENT '答卷 id（逻辑关联 exam_paper.id）',
  `question_id`      BIGINT UNSIGNED  NOT NULL                COMMENT '题目 id（逻辑关联 question.id）',
  `question_title`   TEXT             NOT NULL                COMMENT '题干快照（题目可编辑，历史需可复现）',
  `question_type`    TINYINT UNSIGNED NOT NULL                COMMENT '题型快照：1 判断，2 单选，3 多选，4 简答',
  `score_max`        DECIMAL(5, 2)    NOT NULL                COMMENT '本题满分（快照）',
  `score_obtained`   DECIMAL(5, 2)    NULL                    COMMENT '本题得分；简答判分中为空',
  `is_correct`       TINYINT UNSIGNED NULL                    COMMENT '客观题对错：1 对，0 错；简答题为空',
  `answer_text`      TEXT             NULL                    COMMENT '简答题作答内容（语音转写或打字）',
  `reference_answer` TEXT             NULL                    COMMENT '参考答案快照（简答题）',
  `ai_comment`       TEXT             NULL                    COMMENT 'AI 判分点评（简答题）',
  `judged_at`        DATETIME         NULL                    COMMENT '判分完成时间（UTC）',
  `created_at`       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_answer_paper_question` (`paper_id`, `question_id`),
  KEY `idx_answer_question` (`question_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '答卷逐题作答';

CREATE TABLE IF NOT EXISTS `exam_answer_option` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `answer_id`      BIGINT UNSIGNED NOT NULL                COMMENT '作答 id（逻辑关联 exam_answer.id）',
  `option_key`     CHAR(1)         NOT NULL                COMMENT '选项标识快照',
  `option_content` VARCHAR(512)    NOT NULL                COMMENT '选项内容快照',
  `is_correct`     TINYINT UNSIGNED NOT NULL DEFAULT 0     COMMENT '该选项是否为正确答案（快照）',
  `created_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_answer_option` (`answer_id`, `option_key`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '客观题学员选择（多选拆表）';

CREATE TABLE IF NOT EXISTS `wrong_question` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`       BIGINT UNSIGNED NOT NULL                COMMENT '学员 id（逻辑关联 user.id）',
  `question_id`   BIGINT UNSIGNED NOT NULL                COMMENT '题目 id（逻辑关联 question.id）',
  `wrong_times`   INT UNSIGNED    NOT NULL DEFAULT 1      COMMENT '累计答错次数',
  `last_wrong_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最近一次答错时间（UTC）',
  `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次收录时间（UTC）',
  `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wrong_user_question` (`user_id`, `question_id`),
  KEY `idx_wrong_user_time` (`user_id`, `last_wrong_at`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '错题本（仅客观题）';

-- ------------------------------------------------------------
-- 六、面试：资料库 / 简历 / 会话 / 逐题
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `interview_doc` (
  `id`             BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `file_name`      VARCHAR(255)     NOT NULL                COMMENT '原始文件名',
  `file_type`      TINYINT UNSIGNED NOT NULL                COMMENT '文件类型：1 pdf，2 md',
  `file_size`      BIGINT UNSIGNED  NOT NULL DEFAULT 0      COMMENT '文件大小（字节）',
  `oss_key`        VARCHAR(512)     NOT NULL                COMMENT '对象存储中的对象 key',
  `status`         TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 待处理，2 转 md 中，3 已入库，4 解析失败',
  `failure_reason` VARCHAR(512)     NOT NULL DEFAULT ''     COMMENT '失败原因（status=4 时有值）',
  `uploaded_by`    BIGINT UNSIGNED  NOT NULL                COMMENT '上传人 admin_user.id',
  `deleted_at`     DATETIME         NOT NULL DEFAULT '1970-01-01 00:00:00' COMMENT '软删除时间',
  `created_at`     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `updated_at`     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_doc_status` (`status`),
  KEY `idx_doc_uploaded_at` (`created_at`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '面试资料库文档（切片存向量库，本表只存文件与处理状态）';

CREATE TABLE IF NOT EXISTS `resume` (
  `id`             BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`        BIGINT UNSIGNED  NOT NULL                COMMENT '学员 id（逻辑关联 user.id）',
  `file_name`      VARCHAR(255)     NOT NULL                COMMENT '原始文件名',
  `file_size`      BIGINT UNSIGNED  NOT NULL DEFAULT 0      COMMENT '文件大小（字节）',
  `oss_key`        VARCHAR(512)     NOT NULL                COMMENT '对象存储中的对象 key',
  `status`         TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 解析中，2 已就绪，3 解析失败',
  `failure_reason` VARCHAR(512)     NOT NULL DEFAULT ''     COMMENT '失败原因（status=3 时有值）',
  `parsed_at`      DATETIME         NULL                    COMMENT '解析完成时间（UTC）',
  `deleted_at`     DATETIME         NOT NULL DEFAULT '1970-01-01 00:00:00' COMMENT '软删除时间；重新上传时旧记录置为已删除',
  `created_at`     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `updated_at`     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_resume_user_status` (`user_id`, `status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '学员简历（仅本人可见）';

CREATE TABLE IF NOT EXISTS `interview_session` (
  `id`               BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`          BIGINT UNSIGNED  NOT NULL                COMMENT '学员 id（逻辑关联 user.id）',
  `source`           TINYINT UNSIGNED NOT NULL                COMMENT '来源：1 学科面试，2 简历面试',
  `subject_id`       BIGINT UNSIGNED  NULL                    COMMENT '学科 id（source=1 时有值）',
  `resume_id`        BIGINT UNSIGNED  NULL                    COMMENT '简历 id（source=2 时有值）',
  `question_count`   TINYINT UNSIGNED NOT NULL DEFAULT 5      COMMENT '本场题目数',
  `status`           TINYINT UNSIGNED NOT NULL DEFAULT 1      COMMENT '状态：1 进行中，2 正常结束，3 超时结束，4 提前结束',
  `total_score`      DECIMAL(5, 2)    NULL                    COMMENT '总分；未结束为空',
  `duration_seconds` INT UNSIGNED     NULL                    COMMENT '实际时长（秒）',
  `started_at`       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间（UTC）',
  `ended_at`         DATETIME         NULL                    COMMENT '结束时间（UTC）',
  `created_at`       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  `updated_at`       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_session_user_time` (`user_id`, `started_at`),
  KEY `idx_session_source` (`source`),
  KEY `idx_session_status` (`status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '面试会话';

CREATE TABLE IF NOT EXISTS `interview_question` (
  `id`                BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '主键',
  `session_id`        BIGINT UNSIGNED  NOT NULL                COMMENT '会话 id（逻辑关联 interview_session.id）',
  `question_index`    TINYINT UNSIGNED NOT NULL                COMMENT '本场第几题，从 1 开始',
  `question_text`     TEXT             NOT NULL                COMMENT '题目文本快照（由检索片段生成，必须落库以便复现）',
  `source_type`       TINYINT UNSIGNED NOT NULL                COMMENT '来源：1 面试资料库，2 简历',
  `source_doc_name`   VARCHAR(255)     NOT NULL DEFAULT ''     COMMENT '来源文档名快照（简历面试为项目名）',
  `source_snippet_id` VARCHAR(64)      NOT NULL DEFAULT ''     COMMENT '来源切片在向量库中的主键，便于追溯',
  `answer_mode`       TINYINT UNSIGNED NULL                    COMMENT '作答方式：1 语音，2 打字；未作答为空',
  `answer_text`       TEXT             NULL                    COMMENT '作答内容（语音为转写文本）',
  `follow_up_text`    TEXT             NULL                    COMMENT '追问内容（每题最多 1 次）',
  `follow_up_answer`  TEXT             NULL                    COMMENT '对追问的作答内容',
  `score`             DECIMAL(5, 2)    NULL                    COMMENT '本题得分',
  `ai_comment`        TEXT             NULL                    COMMENT '本题 AI 点评',
  `answered_at`       DATETIME         NULL                    COMMENT '作答完成时间（UTC）',
  `created_at`        DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间（UTC）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_question_index` (`session_id`, `question_index`),
  KEY `idx_interview_question_source` (`source_doc_name`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '面试逐题记录（含追问与评分）';

-- ------------------------------------------------------------
-- 七、系统日志
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `admin_operation_log` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `admin_user_id` BIGINT UNSIGNED NOT NULL                COMMENT '操作人 admin_user.id',
  `module`        VARCHAR(32)     NOT NULL                COMMENT '模块：课程内容 / 刷题题库 / 面试资料库 / 学员管理 / 系统用户',
  `action`        VARCHAR(32)     NOT NULL                COMMENT '动作：新增 / 编辑 / 上架 / 下架 / 删除 / 导入 / 启用 / 停用',
  `target_type`   VARCHAR(32)     NOT NULL DEFAULT ''     COMMENT '对象类型：subject / course / question / doc …',
  `target_id`     BIGINT UNSIGNED NULL                    COMMENT '对象 id（逻辑关联，随对象表而定）',
  `target_name`   VARCHAR(255)    NOT NULL DEFAULT ''     COMMENT '对象名称快照',
  `detail_before` JSON            NULL                    COMMENT '变更前快照',
  `detail_after`  JSON            NULL                    COMMENT '变更后快照',
  `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间（UTC）',
  PRIMARY KEY (`id`),
  KEY `idx_log_created_at` (`created_at`),
  KEY `idx_log_admin_time` (`admin_user_id`, `created_at`),
  KEY `idx_log_module` (`module`, `action`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '后台操作日志';
