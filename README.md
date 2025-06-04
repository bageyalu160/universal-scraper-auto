# Universal Scraper | 通用网页爬虫与 AI 分析框架

一个高度可配置、支持多引擎和 AI 分析的自动化数据采集平台，适用于研究、数据分析和自动化监控场景。

**最新更新**: 新增工作流状态追踪和通知功能，提升工作流执行透明度和可靠性。

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
9. 最近更新

---

## 1. 项目简介

- **多引擎爬虫**：支持 HTTP、Playwright、Firecrawl 等多种采集方式
- **AI 分析**：集成 OpenAI、Gemini 等大模型，自动结构化网页数据
- **自动化工作流**：一键生成 GitHub Actions 工作流，支持定时、通知、监控
- **工作流状态追踪**：自动记录和报告工作流执行状态，支持父子工作流关联
- **代理池与反爬**：内置 IP 轮换、指纹伪装、验证码处理
- **多渠道通知**：钉钉、企业微信、飞书等，支持富文本内容
- **可视化监控**：GitHub Pages 仪表盘
- **增强的浏览器指纹伪装**：集成 playwright-stealth 提供更强的反检测能力
- **自动验证码处理**：集成 2captcha-python 自动处理 reCAPTCHA、hCaptcha 和图片验证码
- **强大的配置验证**：使用 Pydantic 进行 YAML 配置验证和类型转换

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
│   └── workflow/     # 工作流状态记录
├── .github/          # GitHub Actions工作流与仪表盘
├── docs/             # 详细文档
└── README.md
```

---

## 3. 安装与环境

```bash
git clone https://github.com/bageyalu160/universal-scraper-auto.git
cd universal-scraper
pip install -r requirements.txt
pip install -e .
playwright install --with-deps
# 设置API密钥等环境变量（见下方配置说明）
```

---

## 4. 快速上手

### 4.1 使用重构后的 PlaywrightScraper

重构后的 PlaywrightScraper 类集成了多种先进特性，包括浏览器指纹伪装、验证码自动处理和基于 Pydantic 的配置验证。

```bash
# 安装依赖
pip install -r requirements.txt

# 使用示例爬虫脚本
python3 scripts/example_scraper.py --config config/sites/example.yaml

# 可选参数
--headless         # 启用无头模式
--no-stealth       # 禁用浏览器指纹伪装
--no-captcha       # 禁用验证码自动处理
--max-pages N      # 设置最大爬取页数
--max-products N   # 设置最大爬取商品数
--proxy URL        # 设置代理地址 (http://user:pass@host:port)
```

### 4.2 验证码处理

重构后的 PlaywrightScraper 支持三种验证码类型的自动处理：

1. **reCAPTCHA** - Google 的 reCAPTCHA v2/v3
2. **hCaptcha** - hCaptcha 验证码
3. **图片验证码** - 传统的图片识别验证码

要使用验证码自动处理功能，需要在配置文件中设置有效的 2captcha API 密钥：

```yaml
captcha:
  enable: true
  provider: 2captcha
  api_key: your_api_key_here
  timeout: 120
  manual_fallback: true
```

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
- **工作流模板**：`config/workflow/templates/`，包含各类工作流的 Jsonnet 模板
- **工作流工具函数**：`config/workflow/templates/utils.libsonnet`，提供工作流生成的公共函数
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

## 9. 最近更新

### 9.1 工作流状态追踪和通知功能 (2025-05-30)

- **工作流状态记录**：自动记录每个工作流的执行状态、时间戳和相关信息
- **父子工作流关联**：支持在主工作流中追踪和监控子工作流的执行状态
- **状态检查机制**：提供工作流状态检查功能，确保依赖工作流正确完成
- **富文本通知**：支持在通知中包含更丰富的内容，如执行状态、链接等
- **Git操作优化**：改进Git提交机制，增加拉取远程更改以避免推送冲突

### 9.2 工作流参数优化 (2025-05-29)

- **移除引号包裹的参数**：优化工作流命令行参数传递方式
- **统一参数格式**：标准化工作流输入参数的处理方式
- **增强错误处理**：改进工作流执行过程中的错误捕获和处理

## 常用命令参考

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

## 最佳实践与注意事项

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
