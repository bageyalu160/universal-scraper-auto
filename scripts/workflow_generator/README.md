# 工作流生成器 (Workflow Generator)

这是一个强大的工作流生成器，用于为 Universal Scraper 项目生成 GitHub Actions 工作流文件。生成器支持多种工作流类型，并确保生成的工作流符合 GitHub Actions 的语法和最佳实践。

## 主要特点

- 使用 JSON Schema 验证工作流语法
- 使用 actionlint 进行高级语法检查
- 使用 ruamel.yaml 保留 YAML 格式和注释
- 使用 Jinja2 模板引擎进行灵活渲染
- 支持条件表达式和环境变量的标准化
- 自动验证和修复常见的语法问题

## 安装和依赖项

工作流生成器依赖以下组件：

- Python 3.8 或更高版本
- jsonschema 库：用于根据官方 JSON Schema 验证工作流
- ruamel.yaml 库：用于高级 YAML 处理
- jinja2 库：用于模板渲染
- requests 库：用于下载 Schema 和其他资源
- actionlint（可选但推荐）：用于高级语法检查

### 安装依赖项

运行以下命令安装所需的 Python 依赖：

```bash
pip install jsonschema ruamel.yaml jinja2 requests
```

### 设置

为了自动设置所有依赖项（包括下载 JSON Schema 和安装 actionlint），请运行：

```bash
python scripts/workflow_generator/setup.py
```

## 使用方法

### 生成单个工作流

```python
from workflow_generator import WorkflowGenerator

# 初始化生成器
generator = WorkflowGenerator()

# 生成特定站点的爬虫工作流
generator.generate_workflow("site_id", "crawler")

# 生成特定站点的分析工作流
generator.generate_workflow("site_id", "analyzer")
```

### 生成所有工作流

```python
from workflow_generator import WorkflowGenerator

# 初始化生成器
generator = WorkflowGenerator()

# 为所有站点生成工作流
generator.generate_all_workflows()

# 生成通用工作流
generator.generate_common_workflows()
```

### 更新特定站点的工作流

```python
from workflow_generator import WorkflowGenerator

# 初始化生成器
generator = WorkflowGenerator()

# 更新指定站点的工作流
generator.update_workflows("site1,site2,site3")
```

## 架构

工作流生成器的主要组件包括：

- `WorkflowGenerator`: 主生成器类，协调整个生成过程
- `WorkflowYamlRenderer`: 将工作流模型渲染为 YAML 格式
- `WorkflowValidator`: 验证工作流语法和结构
- `WorkflowFactory`: 创建不同类型的工作流
- `WorkflowStrategy`: 工作流生成策略的基类
  - `CrawlerWorkflowStrategy`: 爬虫工作流生成策略
  - `AnalyzerWorkflowStrategy`: 分析工作流生成策略

## 最佳实践

1. 始终使用模板创建工作流，避免硬编码
2. 使用环境变量和变量引用，而不是硬编码值
3. 确保条件表达式使用标准格式（`${{ expression }}`）
4. 遵循 GitHub Actions 语法和结构
5. 定期更新 Schema 和 actionlint 以获取最新功能和修复

## 故障排除

如果遇到验证错误，请检查以下几点：

1. 确保所有变量引用使用正确的语法（`${{ var }}`）
2. 检查条件表达式中的操作符周围是否有空格
3. 验证工作流结构是否符合 GitHub Actions 规范
4. 检查运行器和步骤定义是否正确

## 贡献

欢迎贡献代码、报告问题或提出改进建议。请通过 GitHub Issues 提交问题，或创建 Pull Request 贡献代码。
