# Universal Scraper 命令行工具使用指南

## 简介

Universal Scraper 提供了一个统一的命令行工具 `us.py`，整合了以下功能：

- 工作流生成（原 generate_workflow.py, generate_workflows*.py）
- 爬虫执行（原 scraper.py）
- 分析执行（原 analyzer.py）
- 工作流执行（原 run_workflow.py）
- 通知发送（原 notifier.py）

## 使用方法

```bash
python scripts/us.py [命令] [选项]
```

## 主要命令

- `generate`, `gen` - 生成工作流配置
- `execute`, `run` - 执行完整工作流
- `scrape`, `crawl` - 仅执行爬虫
- `analyze` - 仅执行分析
- `notify` - 仅发送通知

### 生成工作流

```bash
# 一次性生成所有工作流（包括通用工作流和所有站点工作流）
python scripts/us.py generate --type all

# 使用高级选项一次性生成所有工作流
python scripts/us.py generate --type all --enhanced --cache enable --timeout 90 --error-strategy tolerant

# 为指定站点生成所有工作流
python scripts/us.py generate --site pm001 --type all

# 生成通用工作流（主调度、仪表盘、代理池）
python scripts/us.py generate --type common

# 使用增强版Jsonnet引擎生成工作流
python scripts/us.py generate --site heimao --enhanced

# 控制缓存设置
python scripts/us.py generate --site pm001 --cache enable

# 设置工作流超时时间
python scripts/us.py generate --site heimao --timeout 60

# 设置错误处理策略
python scripts/us.py generate --site pm001 --error-strategy tolerant
```

### 执行完整工作流

```bash
# 执行完整工作流（爬虫 -> 分析 -> 通知）
python scripts/us.py run --site pm001

# 指定输出目录
python scripts/us.py run --site heimao --output-dir ./custom_output
```

### 仅执行爬虫

```bash
# 仅执行爬虫阶段
python scripts/us.py scrape --site pm001

# 可以使用别名 crawl
python scripts/us.py crawl --site heimao
```

### 仅执行分析

```bash
# 仅执行分析阶段
python scripts/us.py analyze --site pm001 --data ./data/daily/2025-05-27/pm001_data.json
```

### 仅发送通知

```bash
# 仅执行通知阶段
python scripts/us.py notify --site pm001 \
  --data ./data/daily/2025-05-27/pm001_data.json \
  --analysis ./analysis/daily/2025-05-27/pm001_analysis.json \
  --summary ./analysis/daily/2025-05-27/pm001_summary.md
```

## 全局选项

所有命令都支持以下全局选项：

- `-v, --verbose`: 显示详细日志
- `-c, --config`: 指定设置文件路径
- `-d, --sites-dir`: 指定站点配置目录
- `-o, --output-dir`: 指定输出目录

## 高级选项

### 工作流生成高级选项

- `-e, --enhanced`: 使用增强版Jsonnet引擎（如果可用）
- `--cache {enable,disable}`: 启用或禁用依赖项缓存
- `--timeout INT`: 设置工作流超时时间（分钟）
- `--error-strategy {strict,tolerant}`: 错误处理策略
  - `strict`: 严格模式，任何错误都会导致工作流失败
  - `tolerant`: 宽松模式，允许部分错误，工作流继续执行

## 示例工作流

1. 生成工作流配置：
   ```bash
   # 基本用法
   python scripts/us.py generate --site pm001 --type all
   
   # 高级用法 - 启用缓存、设置超时和错误处理策略
   python scripts/us.py generate --site pm001 --type all --cache enable --timeout 90 --error-strategy tolerant
   ```

2. 执行完整工作流：
   ```bash
   python scripts/us.py run --site pm001
   ```

3. 分步执行：
   ```bash
   # 先执行爬虫
   python scripts/us.py scrape --site pm001
   
   # 再执行分析
   python scripts/us.py analyze --site pm001 --data ./data/daily/2025-05-27/pm001_data.json
   
   # 最后发送通知
   python scripts/us.py notify --site pm001 \
     --data ./data/daily/2025-05-27/pm001_data.json \
     --analysis ./analysis/daily/2025-05-27/pm001_analysis.json \
     --summary ./analysis/daily/2025-05-27/pm001_summary.md
   ```

## 最佳实践

1. **使用增强版Jsonnet引擎**：当需要更复杂的工作流模板时，使用增强版引擎可以提供更多功能。
   ```bash
   python scripts/us.py generate --site pm001 --enhanced
   ```

2. **优化工作流执行时间**：为长时间运行的爬虫任务设置合理的超时时间。
   ```bash
   python scripts/us.py generate --site heimao --timeout 120
   ```

3. **错误处理策略选择**：
   - 对于重要数据采集任务，使用严格模式确保数据完整性：
     ```bash
     python scripts/us.py generate --site pm001 --error-strategy strict
     ```
   - 对于大规模爬取任务，使用宽松模式提高成功率：
     ```bash
     python scripts/us.py generate --site heimao --error-strategy tolerant
     ```
