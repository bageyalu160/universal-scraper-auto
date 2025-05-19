# 工作流生成器使用指南

本文档介绍如何使用工作流生成器来生成和管理 GitHub Actions 工作流文件。

## 功能概述

工作流生成器支持生成以下类型的工作流：

1. **站点特定工作流**：

   - 爬虫工作流（`crawler_*.yml`）：执行特定站点的数据采集任务
   - 分析工作流（`analyzer_*.yml`）：执行特定站点的数据分析任务

2. **通用工作流**：
   - 主调度工作流（`master_workflow.yml`）：协调多个站点的爬取和分析任务
   - 仪表盘更新工作流（`update_dashboard.yml`）：更新监控仪表盘

## 命令行参数

工作流生成器支持以下命令行参数：

```
usage: workflow_generator.py [-h] [--settings SETTINGS] [--sites-dir SITES_DIR]
                           [--output-dir OUTPUT_DIR] [--site SITE] [--all]
                           [--debug] [--type {crawler,analyzer,both,common,all}]
                           [--common]

选项:
  -h, --help            显示帮助信息
  --settings SETTINGS   设置文件路径
  --sites-dir SITES_DIR 站点配置目录
  --output-dir OUTPUT_DIR 输出目录
  --site SITE           指定站点ID，多个站点用逗号分隔
  --all                 生成所有站点的工作流
  --debug               启用调试模式
  --type {crawler,analyzer,both,common,all}
                        要生成的工作流类型 (默认: both)
  --common              生成通用工作流（主工作流和仪表盘更新工作流）
```

## 使用示例

### 生成通用工作流

```bash
# 生成主调度工作流和仪表盘更新工作流
python3 scripts/workflow_generator.py --type common

# 启用调试模式
python3 scripts/workflow_generator.py --type common --debug
```

### 生成站点特定工作流

```bash
# 为单个站点生成爬虫和分析工作流
python3 scripts/workflow_generator.py --site heimao

# 为多个站点生成爬虫工作流
python3 scripts/workflow_generator.py --site heimao,pm001 --type crawler

# 为多个站点生成分析工作流
python3 scripts/workflow_generator.py --site heimao,pm001 --type analyzer
```

### 生成所有工作流

```bash
# 生成所有站点的爬虫和分析工作流（不包括通用工作流）
python3 scripts/workflow_generator.py --all

# 生成所有工作流，包括通用工作流和所有站点工作流
python3 scripts/workflow_generator.py --type all --all
```

## 使用主调度工作流（Master Workflow）

主调度工作流用于协调执行多个站点的爬取和分析任务。

### 工作流触发方式

1. **手动触发**：

   - 在 GitHub Actions 界面中，选择`主调度工作流`，点击`Run workflow`
   - 选择执行操作（爬取所有、分析所有、更新仪表盘、全流程）
   - 可选择指定站点 ID 和数据日期

2. **定时触发**：
   - 工作流每天午夜（UTC 时间）自动执行完整流程

### 执行操作说明

- **crawl_all**：仅执行所有站点的爬取任务
- **analyze_all**：仅执行所有站点的分析任务
- **update_dashboard**：仅更新监控仪表盘
- **full_pipeline**：执行完整流程（爬取 → 分析 → 更新仪表盘）

## 使用仪表盘更新工作流

仪表盘更新工作流用于构建和部署项目的监控仪表盘。

### 工作流触发方式

1. **手动触发**：

   - 在 GitHub Actions 界面中，选择`更新监控仪表盘`，点击`Run workflow`
   - 可选择指定特定站点 ID（留空则处理所有站点）

2. **定时触发**：

   - 工作流每天凌晨 1 点（UTC 时间）自动执行

3. **被其他工作流调用**：
   - 主调度工作流可以触发仪表盘更新工作流

## 工作流文件目录结构

```
.github/
└── workflows/
    ├── master_workflow.yml      # 主调度工作流
    ├── update_dashboard.yml     # 仪表盘更新工作流
    ├── crawler_heimao.yml       # 黑猫投诉爬虫工作流
    ├── analyzer_heimao.yml      # 黑猫投诉分析工作流
    ├── crawler_pm001.yml        # PM001爬虫工作流
    ├── analyzer_pm001.yml       # PM001分析工作流
    └── ...                      # 其他站点工作流

config/
└── workflow/
    ├── crawler.yml.template     # 爬虫工作流模板
    ├── analyzer.yml.template    # 分析工作流模板
    └── templates/
        ├── master_workflow.yml.template    # 主调度工作流模板
        ├── update_dashboard.yml.template   # 仪表盘更新工作流模板
        ├── crawler.yml.template            # 爬虫工作流模板(副本)
        └── analyzer.yml.template           # 分析工作流模板(副本)
```

## 高级用法

### 自定义工作流输出路径

```bash
# 指定自定义输出目录
python3 scripts/workflow_generator.py --type all --all --output-dir ./custom_workflows
```

### 使用自定义设置文件

```bash
# 使用自定义设置文件
python3 scripts/workflow_generator.py --type all --all --settings ./custom_settings.yaml
```

### 使用自定义站点配置目录

```bash
# 使用自定义站点配置目录
python3 scripts/workflow_generator.py --type all --all --sites-dir ./custom_sites
```

## 工作流功能说明

### 主调度工作流

主调度工作流由以下步骤组成：

1. **准备环境**：检出代码，确定数据日期和要处理的站点列表
2. **爬取数据**：触发每个站点的爬虫工作流
3. **分析数据**：获取最新数据文件，触发每个站点的分析工作流
4. **更新仪表盘**：触发仪表盘更新工作流
5. **通知完成**：准备完成通知并发送到配置的渠道

### 仪表盘更新工作流

仪表盘更新工作流由以下步骤组成：

1. **构建仪表盘**：安装必要依赖，生成仪表盘数据，构建静态文件
2. **部署仪表盘**：将仪表盘部署到 GitHub Pages
3. **发送通知**：发送部署状态通知到配置的渠道

## 自定义通知配置

工作流支持发送通知到以下渠道：

1. **钉钉**：设置`ENABLE_NOTIFICATION=true`、`NOTIFICATION_TYPE=dingtalk`和`DINGTALK_WEBHOOK`密钥
2. **企业微信**：设置`ENABLE_NOTIFICATION=true`、`NOTIFICATION_TYPE=wechat`和`WECHAT_WEBHOOK`密钥

## 故障排除

### 常见问题

1. **找不到站点配置文件**：

   - 确保站点配置文件位于`config/sites/`目录
   - 确保文件扩展名为`.yaml`

2. **工作流文件未生成**：

   - 检查日志中的错误信息
   - 确保有正确的写入权限
   - 确保模板文件存在

3. **模板文件不存在**：
   - 确保模板文件位于`config/workflow/templates/`目录
   - 检查文件名是否正确

### 调试模式

使用`--debug`参数启用详细日志输出：

```bash
python3 scripts/workflow_generator.py --type all --all --debug
```

### 日志信息

工作流生成器会输出详细的日志信息，包括：

- 加载设置和配置文件的状态
- 工作流生成过程中的步骤
- 成功生成的工作流文件路径
- 错误和警告信息

## 贡献指南

如需修改或扩展工作流生成器，可以：

1. 添加新的工作流类型：在`WorkflowGenerator`类中添加相应的生成方法
2. 添加新的模板文件：在`config/workflow/templates/`目录中创建新的模板文件
3. 修改现有模板：直接编辑`config/workflow/templates/`目录中的模板文件
4. 扩展命令行接口：在`workflow_generator.py`中修改参数解析逻辑
