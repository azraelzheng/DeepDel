# DeepDel - Windows 用户文件夹深度清理工具

## 概述

DeepDel 是一个基于 Python + Tkinter 的 Windows 用户文件夹清理工具，具备智能识别、AI 辅助判断和用户决策学习能力。

## 核心特性

- 智能识别文件来源程序（包括绿色版软件）
- AI 辅助判断不明确文件的删除风险
- 三级风险分类（安全/建议/谨慎）
- 用户决策学习，越用越智能
- 图形界面，操作直观

---

## 1. 整体架构

```
DeepDel/
├── main.py                 # 程序入口
├── config.py               # 配置管理
├── modules/
│   ├── __init__.py
│   ├── scanner.py          # 文件扫描引擎
│   ├── identifier.py       # 来源识别器（核心）
│   ├── classifier.py       # 风险分级器
│   ├── cleaner.py          # 清理执行器
│   ├── ai_analyzer.py      # AI 分析器
│   └── learner.py          # 用户决策学习
├── rules/
│   ├── safe_rules.json     # 安全删除规则
│   ├── suggest_rules.json  # 建议删除规则
│   ├── caution_rules.json  # 谨慎删除规则
│   └── software_db.json    # 软件/游戏名称数据库
├── ui/
│   ├── __init__.py
│   ├── main_window.py      # 主窗口
│   ├── scan_view.py        # 扫描结果视图
│   └── detail_panel.py     # 详情面板
├── data/
│   └── learner.db          # SQLite 学习数据库
└── utils/
    ├── __init__.py
    ├── registry.py         # 注册表操作
    ├── process.py          # 进程/服务检查
    └── file_utils.py       # 文件工具函数
    └── llm/
        ├── __init__.py
        ├── base.py         # LLM 基类
        ├── glm.py          # GLM 接口实现
        └── prompt_templates.py # Prompt 模板
```

---

## 2. 来源识别器（Identifier）

### 识别流程（Pipeline）

```
输入: 文件夹路径
        ↓
Stage 1: 快速匹配
├─ 文件夹名与 software_db.json 精确匹配
├─ 规则库中的已知模式匹配（如 node_modules, .venv）
└─ 输出: 匹配结果 + 置信度
        ↓
Stage 2: 关联检查
├─ A. 快捷方式/开始菜单验证
├─ B. 进程/服务运行检查
├─ C. MRU 注册表分析
└─ 输出: 程序状态（已安装/运行中/残留）
        ↓
Stage 3: 深度分析
├─ D. 创建时间聚类（找出同一批次创建的文件）
├─ E. 文件类型孤岛识别（只有配置无主程序）
├─ 配置文件解析（.json/.xml/.ini 提取软件名）
└─ 输出: 推测来源 + 证据链
        ↓
Stage 4: 学习与增强
├─ F. 查询 learner.db 历史决策
├─ 在线查询（可选，异步）
└─ 输出: 最终识别结果 + 置信度
```

### 识别结果数据结构

```python
@dataclass
class IdentificationResult:
    path: str                    # 文件夹路径
    source_name: str             # 来源程序名（如 "Visual Studio Code"）
    source_type: str             # 类型：software / game / dev_tool / unknown
    confidence: float            # 置信度 0.0-1.0
    risk_level: str              # safe / suggest / caution
    evidence_chain: List[str]    # 证据链
    program_status: str          # installed / running / uninstalled / portable_gone
    size_bytes: int              # 占用空间
    last_access: datetime        # 最后访问时间
```

---

## 3. AI 分析器

### AI 核心职责

```
触发条件: 识别器无法确定 → 置信度 < 0.6 或 状态未知

AI 分析内容:
├─ 文件夹名称、文件名模式
├─ 文件扩展名分布
├─ 配置文件摘要（脱敏）
├─ 创建/访问时间
├─ 文件夹结构特征
└─ 是否有关联程序在运行

AI 输出:
├─ deletion_suggestion: "can_delete" / "caution" / "keep"
├─ confidence: 0.0 - 1.0
├─ reason: "这是 XXX 的缓存文件夹，程序已卸载，可以安全删除"
└─ risk_points: ["包含配置文件", "可能有用户数据"]
```

### 隐私保护

```python
# 只发送给 AI 的信息（脱敏）
ai_input = {
    "folder_name": "Electron",           # 文件夹名
    "file_extensions": [".json", ".log"], # 扩展名统计
    "config_preview": {                   # 配置文件摘要（不含路径/用户名）
        "name": "VSCode",
        "version": "1.85.0"
    },
    "file_count": 156,
    "total_size": "45MB",
    "created_date": "2024-03-15"
}
# 不发送：完整路径、用户名、文件内容全文
```

### 工作流程

```
扫描文件夹
    ↓
规则匹配 → 明确可删? ─Yes→ 标记 safe
    ↓ No
注册表/进程检查 → 程序已卸载? ─Yes→ 标记 suggest
    ↓ No/Unknown
置信度 < 0.6? ─No→ 使用现有判断
    ↓ Yes
调用 AI 分析 ────────→ 返回删除建议 + 理由
    ↓
展示给用户 + 学习记录
```

---

## 4. 风险分级器与规则库

### 三级风险分类

| 级别 | 标识 | 条件 | 默认勾选 |
|------|------|------|----------|
| 安全删除 | `safe` | 临时文件、缓存、已知可清理目录 | 是 |
| 建议删除 | `suggest` | 程序已卸载、长期未使用、无关联进程 | 是 |
| 谨慎删除 | `caution` | 包含用户数据、配置、AI 置信度低 | 否 |

### 规则库结构

#### safe_rules.json - 安全删除规则

```json
{
  "temp_patterns": [
    {"pattern": "%TEMP%\\*", "description": "系统临时文件"},
    {"pattern": "%LOCALAPPDATA%\\Temp\\*", "description": "用户临时文件"}
  ],
  "cache_patterns": [
    {"pattern": "%LOCALAPPDATA%\\*\\Cache\\*", "description": "浏览器缓存"},
    {"pattern": "%LOCALAPPDATA%\\*\\GPUCache\\*", "description": "GPU 缓存"}
  ],
  "dev_caches": [
    {"pattern": "**\\node_modules", "description": "Node.js 依赖"},
    {"pattern": "**\\.venv", "description": "Python 虚拟环境"},
    {"pattern": "**\\__pycache__", "description": "Python 缓存"},
    {"pattern": "**\\.cache", "description": "通用缓存目录"},
    {"pattern": "%LOCALAPPDATA%\\NuGet\\Cache\\*", "description": "NuGet 缓存"},
    {"pattern": "%LOCALAPPDATA%\\pip\\Cache\\*", "description": "pip 缓存"}
  ],
  "log_patterns": [
    {"pattern": "**\\*.log", "description": "日志文件"},
    {"pattern": "%LOCALAPPDATA%\\CrashDumps\\*", "description": "崩溃转储"}
  ]
}
```

#### suggest_rules.json - 建议删除规则

```json
{
  "uninstalled_residuals": [
    {"pattern": "%APPDATA%\\{app_name}", "condition": "program_uninstalled"},
    {"pattern": "%LOCALAPPDATA%\\{app_name}", "condition": "program_uninstalled"}
  ],
  "empty_folders": {
    "enabled": true,
    "exclude_patterns": ["**\\.git\\*", "**\\.svn\\*"]
  },
  "long_unused": {
    "days_threshold": 180,
    "exclude_types": [".doc", ".docx", ".pdf", ".xls", ".xlsx"]
  }
}
```

#### caution_rules.json - 谨慎删除规则

```json
{
  "user_data_indicators": [
    {"pattern": "**\\*.db", "description": "数据库文件"},
    {"pattern": "**\\save*", "description": "游戏存档"},
    {"pattern": "**\\SavedGames\\*", "description": "保存的游戏"}
  ],
  "config_indicators": [
    {"pattern": "**\\settings.json", "description": "设置文件"},
    {"pattern": "**\\config.ini", "description": "配置文件"}
  ],
  "keep_if_running": true
}
```

#### software_db.json - 软件/游戏数据库

```json
{
  "applications": {
    "Visual Studio Code": {
      "folder_names": ["Code", ".vscode", "vscode"],
      "publisher": "Microsoft",
      "type": "dev_tool",
      "registry_key": "Microsoft\\VisualStudio\\Code"
    },
    "微信": {
      "folder_names": ["WeChat", "Tencent\\WeChat"],
      "publisher": "Tencent",
      "type": "software",
      "registry_key": "Tencent\\WeChat"
    }
  },
  "games": {
    "Minecraft": {
      "folder_names": [".minecraft", "Minecraft"],
      "publisher": "Mojang",
      "type": "game",
      "save_folders": ["saves", "screenshots"]
    }
  }
}
```

### 分级决策流程

```
输入: IdentificationResult
         ↓
1. 匹配 safe_rules? → Yes: 返回 safe
         ↓ No
2. 匹配 caution_rules? → Yes: 返回 caution
         ↓ No
3. 程序状态判断
   - uninstalled → suggest
   - running → caution
   - unknown → 继续
         ↓
4. AI 分析（置信度 < 0.6 时触发）
   返回 AI 建议级别
```

---

## 5. 用户决策学习模块

### SQLite 数据库结构

```sql
-- 决策记录表（存储完整特征）
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 基础信息
    folder_name TEXT NOT NULL,
    parent_path_pattern TEXT,           -- 父路径模式

    -- 来源信息（关键）
    identified_source TEXT,             -- 识别的程序名
    source_confidence REAL,
    program_status TEXT,                -- installed / uninstalled / running / unknown

    -- 特征向量
    file_extensions TEXT,               -- JSON: {".json": 0.6, ".log": 0.3}
    has_executables INTEGER,            -- 0/1
    folder_depth INTEGER,
    total_files INTEGER,
    total_size INTEGER,

    -- 时间特征
    days_since_access INTEGER,
    created_cluster_date TEXT,

    -- 决策
    ai_suggestion TEXT,
    ai_confidence REAL,
    risk_level TEXT,
    user_decision TEXT NOT NULL,        -- deleted / kept

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 学习规则表（基于来源程序 + 特征组合）
CREATE TABLE learned_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 匹配条件（组合）
    source_program TEXT,
    folder_name_pattern TEXT,
    parent_path_pattern TEXT,
    extension_profile TEXT,

    -- 建议动作
    suggested_action TEXT NOT NULL,
    confidence REAL,

    -- 统计
    delete_count INTEGER DEFAULT 0,
    keep_count INTEGER DEFAULT 0,
    total_decisions INTEGER DEFAULT 0,

    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- AI 查询缓存
CREATE TABLE ai_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,
    query_summary TEXT,
    ai_response TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 学习匹配优先级

```
1. 最高优先级：来源程序 + 文件夹名 + 父路径 全匹配（需 >= 2 次决策）
2. 次级：来源程序 + 父路径模式（需 >= 3 次决策）
3. 通用：仅来源程序（需 >= 5 次决策）
4. 无匹配：交给 AI 判断
```

---

## 6. 用户界面

### 主窗口布局

```
┌────────────────────────────────────────────────────────────────────────┐
│  DeepDel - 深度清理工具                                    [─] [□] [×] │
├────────────────────────────────────────────────────────────────────────┤
│  [扫描设置 ▼]                                    [开始扫描]  [停止]     │
├────────────────────────────────────────────────────────────────────────┤
│  扫描进度: ████████████░░░░░░░░ 58%  |  已发现: 23 项 | 456 MB         │
├───────────────────────────────┬────────────────────────────────────────┤
│  扫描结果 (23)                 │  详细信息                             │
│  ├─ 临时文件 (8)      45MB     │  ───────────────────────────────────── │
│  │   ├─ ☑ Temp            12MB│  名称: node_modules                   │
│  │   ├─ ☑ Cache           33MB│  路径: C:\Users\xxx\AppData\Local\... │
│  │   └─ ...                   │  大小: 156 MB                         │
│  ├─ 开发缓存 (5)     890MB     │  来源: Node.js 项目依赖               │
│  │   ├─ ☑ node_modules  156MB │  ───────────────────────────────────── │
│  │   ├─ ☑ .venv         234MB │  识别链:                              │
│  │   └─ ...                   │  - 文件夹名精确匹配                   │
│  ├─ 谨慎处理 (3)     120MB     │  - 程序未运行                         │
│  │   ├─ ☐ GameSaves     120MB │  - AI 确认可删 (92%)                  │
│  │   └─ ...                   │  ───────────────────────────────────── │
│  └─ 未知文件 (7)     230MB     │  AI 建议: 可以删除                    │
│      ├─ ☐ UnknownApp1   45MB   │  这是项目的依赖目录，可以重新安装恢复  │
│      └─ ...                   │                                       │
│                               │  [询问 AI...]                         │
├───────────────────────────────┴────────────────────────────────────────┤
│  统计: 选中 12 项 | 可释放 1.2 GB     [全选] [全不选]  [删除选中]       │
└────────────────────────────────────────────────────────────────────────┘
```

### 关键交互

| 操作 | 行为 |
|------|------|
| 点击左侧项 | 右侧显示详细信息 |
| 勾选/取消 | 实时更新底部统计 |
| 右键菜单 | "询问 AI"、"打开目录"、"添加到排除列表" |
| 双击 | 在资源管理器中打开 |
| 删除后 | 学习用户决策，更新数据库 |

---

## 7. 配置管理

### config.yaml

```yaml
scan:
  paths:
    - "%TEMP%"
    - "%APPDATA%"
    - "%LOCALAPPDATA%"
    - "%PROGRAMDATA%"
  min_size_mb: 1
  exclude:
    - "**/.git/**"
    - "**/.svn/**"
    - "**/OneDrive/**"

ai:
  enabled: true
  provider: glm
  model: glm-4-flash
  trigger_confidence: 0.6
  timeout: 10

delete:
  use_recycle_bin: true
  create_restore_point: false

performance:
  max_workers: 4
```

---

## 8. 完整工作流程

```
1. 初始化
   • 加载 config.yaml
   • 加载规则库
   • 连接 learner.db
   • 初始化 AI 客户端

2. 扫描阶段
   • 多线程遍历扫描路径
   • 收集文件夹元数据
   • 应用 exclude 规则过滤
   • 实时更新 UI 进度

3. 识别阶段 (Identifier Pipeline)
   Stage 1: 规则库快速匹配
   Stage 2: 注册表/进程/快捷方式检查
   Stage 3: 配置文件解析、时间聚类分析
   Stage 4: 查询学习数据库

4. 分级阶段 (Classifier)
   • 应用三套规则库
   • 置信度 < 0.6 → 调用 AI
   • 最终确定 risk_level

5. 展示阶段
   • 分类显示在 UI
   • 默认勾选 safe 和 suggest

6. 删除阶段
   • 显示确认弹窗
   • 可选创建还原点
   • 移动到回收站或直接删除
   • 记录用户决策

7. 学习阶段
   • 分析用户决策模式
   • 提取新的 learned_rules
```

---

## 9. 技术栈总结

| 模块 | 技术 |
|------|------|
| 语言 | Python 3.x |
| GUI | Tkinter |
| 数据库 | SQLite |
| AI | GLM API (glm-4-flash) |
| 规则格式 | JSON / YAML |
| 并发 | threading |

---

## 10. 后续扩展方向

- [ ] 支持更多 AI 模型（OpenAI、本地模型）
- [ ] 规则库在线更新
- [ ] 多语言支持
- [ ] 定时自动清理
- [ ] 清理报告导出
