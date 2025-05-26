# 🔧 工作流生成器使用说明

Universal Scraper 工作流生成器是一个功能强大的工具，用于自动生成 GitHub Actions 工作流文件。支持多种生成模式和模板格式。

## 📋 目录

- [快速开始](#快速开始)
- [命令行使用](#命令行使用)
- [增强版生成器](#增强版生成器)
- [传统 YAML 生成器](#传统yaml生成器)
- [Jsonnet 生成器](#jsonnet生成器)
- [工具命令](#工具命令)
- [环境配置](#环境配置)
- [故障排除](#故障排除)

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Jsonnet（如果使用Jsonnet功能）
pip install jsonnet
```

### 2. 查看可用站点

```bash
python run_workflow_generator.py list-sites
```

### 3. 生成第一个工作流

```bash
# 生成增强版分析工作流（推荐）
python run_workflow_generator.py enhanced-analyzer heimao

# 或使用传统YAML生成器
python run_workflow_generator.py yaml-analyzer heimao
```

## 💻 命令行使用

### 基本语法

```bash
python run_workflow_generator.py <命令> [参数] [选项]
```

### 全局选项

- `--verbose`, `-v`: 启用详细日志输出
- `--dry-run`: 试运行模式，不实际生成文件
- `--settings <文件>`: 指定设置文件路径
- `--sites-dir <目录>`: 指定站点配置目录
- `--output-dir <目录>`: 指定输出目录

### 示例

```bash
# 启用详细日志
python run_workflow_generator.py enhanced-analyzer heimao --verbose

# 试运行模式
python run_workflow_generator.py enhanced-all --dry-run

# 指定自定义配置
python run_workflow_generator.py enhanced-analyzer heimao --sites-dir custom/sites
```

## 🌟 增强版生成器

增强版生成器是推荐的工作流生成方式，支持完整的 YAML 模板功能。

### 可用命令

#### 生成单个站点工作流

```bash
# 生成分析工作流
python run_workflow_generator.py enhanced-analyzer <站点ID>

# 生成爬虫工作流
python run_workflow_generator.py enhanced-crawler <站点ID>
```

#### 批量生成

```bash
# 生成所有站点的所有工作流
python run_workflow_generator.py enhanced-all

# 仅生成分析工作流
python run_workflow_generator.py enhanced-all --types analyzer

# 仅生成爬虫工作流
python run_workflow_generator.py enhanced-all --types crawler
```

#### 使用详细 CLI

```bash
# 使用详细CLI命令
python scripts/workflow_generator/enhanced_cli.py enhanced analyzer heimao
python scripts/workflow_generator/enhanced_cli.py enhanced crawler heimao
python scripts/workflow_generator/enhanced_cli.py enhanced all
```

### 增强功能特性

- ✅ **智能参数检测**: 自动从不同触发源获取参数
- ✅ **文件验证**: 确保数据文件存在再执行分析
- ✅ **状态管理**: 创建结构化的状态文件
- ✅ **Git 集成**: 自动提交和推送结果
- ✅ **通知系统**: 支持钉钉、企业微信等通知方式
- ✅ **工件上传**: 自动保存分析结果
- ✅ **仪表盘触发**: 完成后自动更新监控仪表盘
- ✅ **并发控制**: 避免相同站点任务冲突
- ✅ **超时管理**: 防止任务无限运行

## 📜 传统 YAML 生成器

传统 YAML 生成器使用 Jinja2 模板引擎，适合简单的工作流生成。

### 可用命令

```bash
# 生成单个站点工作流
python run_workflow_generator.py yaml-analyzer <站点ID>
python run_workflow_generator.py yaml-crawler <站点ID>

# 生成所有工作流
python run_workflow_generator.py yaml-all
```

### 详细 CLI 使用

```bash
# 使用详细CLI
python scripts/workflow_generator/cli.py generate <站点ID> <工作流类型>
python scripts/workflow_generator/cli.py generate-all
python scripts/workflow_generator/cli.py update --sites site1,site2
```

## 🔍 Jsonnet 生成器

Jsonnet 生成器提供更强大的模板功能和代码重用能力。

### 可用命令

```bash
# 使用快速命令
python run_workflow_generator.py jsonnet <模板名> <输出名> [站点ID]

# 使用详细CLI
python scripts/workflow_generator/enhanced_cli.py jsonnet generate <模板名> <输出名> --site-id <站点ID>
```

### 示例

```bash
# 生成分析工作流
python run_workflow_generator.py jsonnet analyzer analyzer_heimao heimao

# 生成爬虫工作流
python run_workflow_generator.py jsonnet crawler crawler_heimao heimao
```

## 🛠️ 工具命令

### 站点管理

```bash
# 列出所有可用站点
python run_workflow_generator.py list-sites

# 验证站点配置
python run_workflow_generator.py validate [站点ID]

# 验证所有站点
python run_workflow_generator.py validate
```

### 文件管理

```bash
# 清理生成的工作流文件
python run_workflow_generator.py clean

# 清理并查看会删除的文件
python run_workflow_generator.py clean --dry-run
```

### 依赖项设置

```bash
# 安装并设置依赖项
python scripts/workflow_generator/setup.py
```

## ⚙️ 环境配置

### 目录结构

```
universal-scraper/
├── config/
│   ├── sites/              # 站点配置文件
│   └── workflow/
│       └── templates/      # 工作流模板
├── scripts/
│   └── workflow_generator/ # 生成器脚本
├── .github/
│   └── workflows/          # 生成的工作流文件
└── run_workflow_generator.py  # 快速运行脚本
```

### 配置文件

#### 站点配置示例 (`config/sites/heimao.yaml`)

```yaml
site_info:
  name: "黑猫投诉"
  description: "黑猫投诉平台数据采集"

crawler:
  engine: "firecrawl"
  schedule: "0 */6 * * *"

analysis:
  provider: "openai"
  output_format: "tsv"
  prompt_template: "default"
```

#### 全局设置 (`config/settings.yaml`)

```yaml
crawler:
  default_timeout: 30
  default_engine: "requests"

analysis:
  default_provider: "openai"
  default_output_format: "tsv"

notification:
  default_type: "dingtalk"
  enabled: true
```

### 环境变量

在 GitHub 仓库中设置以下 Secrets：

- `OPENAI_API_KEY`: OpenAI API 密钥
- `GEMINI_API_KEY`: Google Gemini API 密钥
- `DINGTALK_WEBHOOK`: 钉钉通知 Webhook URL
- `WECHAT_WEBHOOK`: 企业微信通知 Webhook URL

## 🐛 故障排除

### 常见问题

#### 1. 找不到 CLI 脚本

```bash
❌ 错误: 找不到CLI脚本 scripts/workflow_generator/enhanced_cli.py
```

**解决方案**：确保在项目根目录运行命令

#### 2. 站点配置无效

```bash
❌ 站点 heimao 配置无效
```

**解决方案**：

- 检查 `config/sites/heimao.yaml` 文件是否存在
- 验证 YAML 语法是否正确
- 使用 `python run_workflow_generator.py validate heimao` 检查配置

#### 3. 依赖项缺失

```bash
ModuleNotFoundError: No module named 'jsonnet'
```

**解决方案**：

```bash
pip install jsonnet
# 或安装所有依赖
pip install -r requirements.txt
```

#### 4. 权限错误

```bash
PermissionError: [Errno 13] Permission denied
```

**解决方案**：

- 确保有写入权限到输出目录
- 在 Linux/Mac 上可能需要 `chmod +x` 权限

### 调试技巧

#### 启用详细日志

```bash
python run_workflow_generator.py enhanced-analyzer heimao --verbose
```

#### 使用试运行模式

```bash
python run_workflow_generator.py enhanced-all --dry-run
```

#### 检查生成的文件

```bash
# 查看生成的工作流文件
ls -la .github/workflows/

# 检查文件内容
cat .github/workflows/analyzer_heimao.yml
```

### 获取帮助

#### 查看帮助信息

```bash
# 快速帮助
python run_workflow_generator.py help

# 详细帮助
python scripts/workflow_generator/enhanced_cli.py --help
```

#### 查看可用选项

```bash
# 查看增强版命令帮助
python scripts/workflow_generator/enhanced_cli.py enhanced --help

# 查看工具命令帮助
python scripts/workflow_generator/enhanced_cli.py tools --help
```

## 🎯 最佳实践

1. **优先使用增强版生成器**：功能更完整，支持更多特性
2. **验证配置**：生成工作流前先验证站点配置
3. **使用试运行模式**：大批量操作前先试运行
4. **启用详细日志**：调试时启用详细日志输出
5. **定期清理**：清理不需要的工作流文件
6. **版本控制**：将生成的工作流文件纳入版本控制

## 📚 更多资源

- [项目 README](../README.md)
- [开发规范](./DEVELOPMENT_GUIDELINES.md)
- [API 文档](./API.md)
- [GitHub Issues](https://github.com/your-repo/universal-scraper/issues)

---

**需要帮助？** 请在 GitHub Issues 中提问或联系项目维护者。
