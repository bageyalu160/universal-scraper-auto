# 配置系统统一方案

## 🎯 问题背景

项目原本存在配置分散的问题：

- `config/settings.yaml` - 项目全局设置
- `config/workflow/global.yaml` - 工作流全局配置（已删除）

这导致了配置重复、管理困难、容易出现不一致等问题。

## ✅ 统一解决方案

### 核心思路

**将所有配置统一到 `config/settings.yaml` 一个文件中**，按功能模块分组管理。

### 新的配置架构

```yaml
# Universal Scraper 全局配置文件
config/settings.yaml:
├── runtime                    # 基础运行环境配置
├── github_actions            # GitHub Actions 工作流配置
├── schedules                 # 调度配置
├── paths                     # 路径配置
├── scripts                   # 脚本配置
├── dependencies              # 依赖项配置
├── environment_variables     # 环境变量配置
├── sites                     # 站点配置
├── analysis                  # AI 分析配置
├── notification              # 通知配置
├── proxy_pool                # 代理池配置
├── advanced                  # 高级配置
└── project                   # 项目信息
```

## 📋 配置模块详解

### 1. 基础运行环境 (`runtime`)

```yaml
runtime:
  mode: "local" # 运行模式：local/github
  runner: "ubuntu-latest" # GitHub Actions 运行器
  python_version: "3.10" # Python 版本
  timeout_minutes: 30 # 全局超时设置
  timezone: "Asia/Shanghai" # 时区设置
  debug: false # 调试模式
```

### 2. GitHub Actions 配置 (`github_actions`)

```yaml
github_actions:
  enabled: true
  workflow_dir: ".github/workflows"
  actions: # Actions 版本配置
    checkout: "actions/checkout@v4"
    setup_python: "actions/setup-python@v5"
    # ... 更多 Actions
  permissions: # 权限配置模板
    standard: { ... }
    pages: { ... }
    ai: { ... }
  concurrency: # 并发控制
    enabled: true
    cancel_in_progress: true
    group_prefix: "universal-scraper"
  artifacts: # 工件配置
    default_retention_days: 7
    retention: { ... }
```

### 3. 依赖项配置 (`dependencies`)

```yaml
dependencies:
  base: # 基础依赖
    - "requests>=2.31.0"
    - "pyyaml>=6.0"
  crawler: # 爬虫依赖（按引擎分组）
    requests: [...]
    playwright: [...]
    firecrawl: [...]
  analyzer: [...] # AI 分析依赖
  notification: [...] # 通知依赖
  # ... 更多依赖组
```

### 4. 通知配置 (`notification`)

```yaml
notification:
  enabled: true
  template: "..." # 通知模板
  channels: # 通知渠道
    dingtalk: { ... }
    feishu: { ... }
    wechat: { ... }
  apprise_urls: [] # 扩展通知服务
```

## 🔧 迁移指南

### 1. 模板文件迁移

**更新 Jsonnet 模板引用**：

```jsonnet
// 旧方式
local global_config = std.parseYaml(importstr '../global.yaml');

// 新方式
local settings = std.parseYaml(importstr '../../settings.yaml');

// 访问配置
settings.runtime.python_version
settings.github_actions.actions.checkout
settings.dependencies.base
```

### 2. Python 脚本迁移

**更新 Python 脚本中的配置读取**：

```python
# 旧方式
with open('config/settings.yaml') as f:
    settings = yaml.safe_load(f)
data_dir = settings['general']['data_dir']

# 新方式
with open('config/settings.yaml') as f:
    settings = yaml.safe_load(f)
data_dir = settings['paths']['data']
```

### 3. 主要配置路径变更

| 配置项      | 旧路径                          | 新路径                                    |
| ----------- | ------------------------------- | ----------------------------------------- |
| Python 版本 | `global.runner`                 | `runtime.python_version`                  |
| 数据目录    | `general.data_dir`              | `paths.data`                              |
| 分析目录    | `general.analysis_dir`          | `paths.analysis`                          |
| 状态目录    | `general.status_dir`            | `paths.status`                            |
| 通知配置    | `notification.dingtalk.enabled` | `notification.channels.dingtalk.enabled`  |
| AI 配置     | `analysis.api.api_key_env`      | `environment_variables.ai.gemini.api_key` |

## 🛠️ 工具函数增强

在 `params.libsonnet` 中新增了便捷的工具函数：

### 1. 依赖项管理

```jsonnet
// 获取特定类型的依赖项
params.getDependencies('crawler', 'playwright')

// 构建安装命令
params.buildInstallCommand('analyzer')
```

### 2. 环境变量管理

```jsonnet
// 获取通知相关环境变量
params.getEnvVars('notification')

// 构建通知环境变量映射
params.buildNotificationEnv()
```

### 3. GitHub Actions 配置

```jsonnet
// 获取特定 Action 版本
params.getAction('checkout')

// 构建权限配置
params.buildPermissions('pages')

// 构建并发控制配置
params.buildConcurrency('crawler')
```

## 🔄 需要更新的文件

### ✅ 已完成

- [x] 删除 `config/workflow/global.yaml`
- [x] 重构 `config/settings.yaml`
- [x] 更新 `config/workflow/templates/params.libsonnet`
- [x] 创建迁移文档

### 🔲 待完成

- [ ] 更新所有 Jsonnet 模板文件中的配置引用
- [ ] 更新 Python 脚本中的配置读取逻辑
- [ ] 重新生成所有工作流文件
- [ ] 更新相关文档

## 📈 优势总结

### 1. **统一管理**

- 所有配置集中在一个文件中
- 按功能模块清晰分组
- 避免配置分散和重复

### 2. **易于维护**

- 单一配置源，修改方便
- 层次化结构，查找便捷
- 版本控制友好

### 3. **灵活扩展**

- 模块化设计，易于添加新配置
- 工具函数简化模板开发
- 向后兼容性考虑

### 4. **减少错误**

- 统一的配置引用方式
- 类型安全的工具函数
- 配置验证机制

## 🚀 最佳实践

### 1. 配置访问

- 使用工具函数而非直接访问
- 利用默认值机制提高健壮性
- 遵循配置层次结构

### 2. 扩展配置

- 新增配置项时选择合适的模块
- 保持配置结构的一致性
- 提供合理的默认值

### 3. 版本管理

- 重大配置变更时更新版本号
- 在文档中记录配置变更历史
- 提供向后兼容的迁移路径
