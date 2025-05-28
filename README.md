# Universal Scraper | 通用网页爬虫与 AI 分析框架

一个高度可配置、支持多引擎和 AI 分析的自动化数据采集平台，适用于研究、数据分析和自动化监控场景。

---

## 目录

1. 项目简介
2. 目录结构
3. 安装与环境
4. 快速上手
5. 工作流生成与自动化
6. 配置说明
7. 常见问题与迁移指引
8. 开发与贡献
9. 开发迭代流程

---

## 1. 项目简介

- **多引擎爬虫**：支持 HTTP、Playwright、Firecrawl 等多种采集方式
- **AI 分析**：集成 OpenAI、Gemini 等大模型，自动结构化网页数据
- **自动化工作流**：一键生成 GitHub Actions 工作流，支持定时、通知、监控
- **代理池与反爬**：内置 IP 轮换、指纹伪装、验证码处理
- **多渠道通知**：钉钉、企业微信、飞书等
- **可视化监控**：GitHub Pages 仪表盘

---

## 2. 目录结构（核心部分）

```
universal-scraper/
├── config/           # 配置（站点、分析、工作流模板等）
├── scripts/          # 主脚本（爬虫、分析、通知、工作流生成器等）
│   └── workflow_generator/
│       ├── enhanced_cli.py                # 推荐命令行入口
│       ├── enhanced_jsonnet_generator.py  # 推荐生成器类
├── src/              # 主要功能模块（爬虫、分析、通知、工具等）
├── data/             # 数据存储
├── analysis/         # 分析结果
├── status/           # 状态文件
├── .github/          # GitHub Actions工作流与仪表盘
├── docs/             # 详细文档
└── README.md
```

---

## 3. 安装与环境

```bash
git clone https://github.com/yourusername/universal-scraper.git
cd universal-scraper
pip install -r requirements.txt
pip install -e .
playwright install --with-deps
# 设置API密钥等环境变量（见下方配置说明）
```

---

## 4. 快速上手

### 4.1 创建站点配置

在`config/sites/`下新建`mysite.yaml`，参考`example.yaml`模板。

### 4.2 运行爬虫

```bash
python scripts/scraper.py --site mysite
```

### 4.3 运行 AI 分析

```bash
python scripts/ai_analyzer.py --file data/daily/2023-01-01/mysite_data.json --site mysite
```

---

## 5. 工作流生成与自动化

> **重要：所有工作流相关命令请统一使用 `enhanced_cli.py` 入口。**

### 5.1 生成单个站点分析工作流

```bash
python scripts/workflow_generator/enhanced_cli.py enhanced analyzer mysite
```

### 5.2 生成所有站点工作流

```bash
python scripts/workflow_generator/enhanced_cli.py enhanced all
```

### 5.3 兼容原有 YAML 生成器用法

```bash
python scripts/workflow_generator/enhanced_cli.py yaml generate mysite analyzer
```

---

## 6. 配置说明

- **站点配置**：`config/sites/`下每个 YAML 文件描述一个站点的采集与分析规则
- **全局设置**：`config/settings.yaml`，配置数据目录、AI 分析、代理池等
- **分析提示词**：`config/analysis/prompts/`，可自定义每个站点的 AI 提示词
- **环境变量**：如`OPENAI_API_KEY`、`GEMINI_API_KEY`、`FIRECRAWL_API_KEY`等

---

## 7. 常见问题与迁移指引

- **入口变更**：`cli.py`和`jsonnet_generator.py`已弃用，所有命令请用`enhanced_cli.py`和`enhanced_jsonnet_generator.py`
- **历史脚本迁移**：将原有入口替换为上述命令即可
- **详细 FAQ 与排障**：见`docs/`目录

---

## 8. 开发与贡献

- 遵循 PEP8，添加注释和单元测试
- 扩展新爬虫/分析器/通知渠道请参考`src/`和`docs/`
- 欢迎 PR 和 Issue

---

## 9. 开发迭代流程

### 9.1 需求分析与规划

1. **确定需求**
   - 明确新功能或改进点
   - 确定优先级和实施计划

2. **技术方案设计**
   - 编写技术方案文档
   - 确定实现方式和技术选型
   - 识别可能的风险点

### 9.2 工作流模板开发

1. **分析现有模板**
   - 识别重复代码和模式
   - 确定可抽取的公共函数

2. **开发公共函数库**
   - 在 `utils.libsonnet` 中实现公共函数
   - 常见公共函数类型：
     - 配置解析函数（如 `getConfigSection`、`getConfigValue`）
     - 依赖项获取函数（如 `getCrawlerDependencies`、`getAnalyzerDependencies`）
     - 缓存配置生成函数（如 `generateCacheConfig`）
     - 通用步骤生成函数（如 `generateCheckoutStep`、`generatePythonSetupStep`）
     - 工作流触发器生成函数（如 `generateWorkflowDispatchTrigger`）

3. **更新工作流模板**
   - 使用公共函数替换重复代码
   - 确保模板的一致性和可维护性
   - 主要模板文件：
     - `crawler.jsonnet` - 爬虫工作流模板
     - `analyzer.jsonnet` - 分析工作流模板
     - `proxy_pool.jsonnet` - 代理池工作流模板
     - `dashboard.jsonnet` - 仪表板工作流模板
     - `master_workflow.jsonnet` - 主工作流模板

4. **测试模板生成**
   ```bash
   python3 scripts/us.py generate --site <站点ID> --type <工作流类型> --enhanced
   ```

### 9.3 命令行工具开发

1. **分析现有功能**
   - 识别需要添加的新参数和功能
   - 确定命令行接口设计

2. **更新参数解析**
   - 在 `us.py` 中添加新的命令行参数
   - 示例：
     ```python
     generate_parser.add_argument('--cache', choices=['enable', 'disable'], 
                                help='启用或禁用依赖项缓存')
     ```

3. **实现功能处理**
   - 在相应的处理函数中实现新功能
   - 示例：
     ```python
     if hasattr(args, 'cache') and args.cache:
         cache_enabled = args.cache == 'enable'
         generator.set_cache_enabled(cache_enabled)
     ```

4. **更新工作流生成器**
   - 在 `enhanced_jsonnet_generator.py` 中添加新方法
   - 示例：
     ```python
     def set_cache_enabled(self, enabled: bool):
         self.cache_enabled = enabled
         self.logger.debug(f"缓存设置已更新: {'启用' if enabled else '禁用'}")
     ```

5. **测试命令行功能**
   ```bash
   python3 scripts/us.py --verbose generate --site <站点ID> --type <工作流类型> --enhanced --cache enable --timeout 60 --error-strategy tolerant
   ```

### 9.4 站点配置开发

1. **创建或更新站点配置**
   - 在 `config/sites/` 目录下创建或更新 YAML 配置文件
   - 配置文件命名格式：`<站点ID>.yaml`

2. **配置爬取规则**
   - 定义目标 URL、选择器和爬取规则
   - 配置爬虫引擎和参数

3. **配置分析规则**
   - 定义 AI 分析提示词和参数
   - 配置输出格式和处理规则

4. **测试站点配置**
   ```bash
   python3 scripts/us.py scrape --site <站点ID> --verbose
   python3 scripts/us.py analyze --site <站点ID> --input <数据文件> --verbose
   ```

### 9.5 测试与验证

1. **单元测试**
   - 为关键组件编写单元测试
   - 使用 pytest 或其他测试框架

2. **集成测试**
   - 测试工作流生成和执行
   - 验证各组件之间的交互

3. **端到端测试**
   - 模拟完整的爬取-分析-通知流程
   - 验证整体功能和性能

4. **手动验证**
   - 在本地环境验证生成的工作流
   - 检查工作流的正确性和一致性

### 9.6 部署与发布

1. **提交代码**
   ```bash
   git add .
   git commit -m "描述你的更改"
   git push
   ```

2. **更新文档**
   - 更新 README 和使用文档
   - 记录新功能和变更

3. **发布版本**
   - 创建版本标签
   - 更新版本号和变更日志

4. **监控运行**
   - 监控 GitHub Actions 工作流运行情况
   - 收集反馈并进行必要的调整

### 9.7 常用命令参考

```bash
# 生成所有工作流
python3 scripts/us.py generate --type all --enhanced

# 生成特定站点的爬虫工作流
python3 scripts/us.py generate --site <站点ID> --type crawler --enhanced

# 生成特定站点的分析工作流
python3 scripts/us.py generate --site <站点ID> --type analyzer --enhanced

# 使用高级配置选项
python3 scripts/us.py --verbose generate --site <站点ID> --type crawler --enhanced --cache enable --timeout 60 --error-strategy tolerant
```

### 9.8 最佳实践与注意事项

1. **代码规范**
   - 使用有意义的变量名和函数名
   - 遵循 Python 的 PEP 8 规范
   - Jsonnet 文件使用 camelCase 命名风格

2. **工作流模板开发**
   - 优先使用公共函数，避免重复代码
   - 添加适当的错误处理和重试机制
   - 使用缓存减少重复计算和下载

3. **安全注意事项**
   - 使用 GitHub Secrets 存储 API 密钥
   - 不要在代码中硬编码敏感信息
   - 遵循最小权限原则

---

**如需详细用法、进阶配置、开发者文档，请查阅`docs/`目录。**
