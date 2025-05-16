# Firecrawl 集成使用指南

本文档介绍如何在 Universal Scraper 项目中使用 Firecrawl 功能进行网页爬取和结构化数据提取。

## 1. 安装依赖

首先，确保已安装所需的依赖：

```bash
pip install -r requirements.txt
```

此命令会安装 Firecrawl Python SDK 及其依赖项。

## 2. 配置 API 密钥

您需要获取 Firecrawl API 密钥，可以通过两种方式提供密钥：

1. 设置环境变量：

```bash
export FIRECRAWL_API_KEY=fc-your-api-key
```

2. 在命令行参数中提供：

```bash
python src/scrapers/firecrawl_integration.py --site firecrawl_example --api-key fc-your-api-key
```

## 3. 创建站点配置

在 `config/sites/` 目录下创建配置文件，例如 `firecrawl_example.yaml`。您可以参考示例配置，根据需要进行修改。

主要配置节点：

- `scraping.engine`: 设置为 "firecrawl" 使用 Firecrawl 引擎
- `scraping.firecrawl_options`: Firecrawl 特定配置选项
- `scraping.extract_prompt`: 用于 Extract 功能的提示词
- `parsing.field_selectors`: 定义要提取的数据字段及描述

## 4. 使用功能

### 4.1 爬取网站

运行以下命令爬取网站：

```bash
python src/scrapers/firecrawl_integration.py --site firecrawl_example --crawl
```

爬取结果将保存在 `data/daily/[日期]/firecrawl_example_crawl.json` 文件中。

### 4.2 提取结构化数据

使用 Extract 功能提取结构化数据：

```bash
python src/scrapers/firecrawl_integration.py --site firecrawl_example --extract
```

提取结果将保存在 `data/daily/[日期]/firecrawl_example_structured.json` 文件中。

### 4.3 映射网站结构

获取网站的 URL 地图：

```bash
python src/scrapers/firecrawl_integration.py --site firecrawl_example --map
```

网站地图将保存在 `data/daily/[日期]/firecrawl_example_sitemap.json` 文件中。

### 4.4 抓取单个 URL

抓取单个 URL 的内容：

```bash
python src/scrapers/firecrawl_integration.py --site firecrawl_example --scrape https://docs.firecrawl.dev/features/extract
```

### 4.5 执行所有功能

一次性运行所有功能：

```bash
python src/scrapers/firecrawl_integration.py --site firecrawl_example --all
```

## 5. 高级功能

### 5.1 页面交互操作（Actions）

Firecrawl 支持在抓取页面前执行一系列交互操作，例如点击、滚动、等待、填写表单等。这对于获取动态加载的内容或需要用户交互才能显示的内容非常有用。

在配置文件中的 `scraping.firecrawl_options.actions` 节点添加操作序列：

```yaml
scraping:
  firecrawl_options:
    actions:
      - { type: "wait", milliseconds: 2000 } # 等待2秒
      - { type: "click", selector: "button.show-more" } # 点击"显示更多"按钮
      - { type: "wait", milliseconds: 1000 } # 等待1秒
      - { type: "scroll", direction: "down" } # 向下滚动
      - { type: "screenshot" } # 截取屏幕截图
      - { type: "scrape" } # 抓取当前页面内容
```

支持的操作类型包括：

- `wait`: 等待指定的时间（单位：毫秒）
- `click`: 点击指定的元素
- `scroll`: 向上或向下滚动页面
- `write`: 在输入框中输入文本
- `press`: 按下键盘按键（例如 ENTER）
- `screenshot`: 截取屏幕截图
- `scrape`: 抓取当前页面内容

### 5.2 无架构提取

除了使用预定义的架构进行数据提取外，Firecrawl 还支持仅使用自然语言提示词进行提取，让 AI 自行确定输出的结构。

只需在配置中设置 `scraping.extract_prompt`，无需定义详细的 `parsing.field_selectors`：

```yaml
scraping:
  extract_prompt: "提取页面中的公司使命、是否支持单点登录、是否开源以及是否是Y Combinator公司。"
```

### 5.3 多输出格式支持

Firecrawl 支持多种输出格式，可以在 `scraping.firecrawl_options.formats` 中配置：

```yaml
scraping:
  firecrawl_options:
    formats: ["markdown", "html", "json", "screenshot", "links"]
```

可用格式包括：

- `markdown`: 将网页内容转换为 Markdown 格式（适合 LLM 处理）
- `html`: 原始 HTML 或处理后的 HTML
- `json`: 结构化的 JSON 数据（通常与 Extract 功能配合使用）
- `screenshot`: 页面截图
- `links`: 页面中的链接列表
- `rawHtml`: 完全原始的 HTML

## 6. Extract 功能详解

Firecrawl 的 Extract 功能是一个强大的结构化数据提取工具，它可以：

1. **从多个 URL 抽取数据**：可以提供单个或多个 URL，包括通配符路径。
2. **基于提示词提取**：使用自然语言提示词描述要提取的数据。
3. **基于架构提取**：使用 JSON Schema 定义要提取的数据结构。
4. **Web 搜索增强**：可启用 Web 搜索增强功能，获取更完整的信息。

### 6.1 架构定义

在配置文件的 `parsing.field_selectors` 节点下定义要提取的字段：

```yaml
parsing:
  field_selectors:
    product_name:
      description: "产品名称"
    price:
      description: "产品价格"
    features:
      description: "产品特性列表"
```

系统会自动将这些字段转换为适用于 Extract 的架构。

### 6.2 提示词编写

在配置文件的 `scraping.extract_prompt` 节点设置提示词。提示词应清晰描述要提取的内容，例如：

```yaml
scraping:
  extract_prompt: "提取网页中的产品信息，包括产品名称、价格和特性列表。"
```

## 7. 常见问题

### 问题 1: 提取结果不准确

解决方案：

- 优化提示词，使其更清晰明确
- 完善架构定义，添加更多字段描述
- 启用 Web 搜索增强 (`enableWebSearch: true`)
- 使用页面交互操作确保所需数据已加载

### 问题 2: API 请求失败

解决方案：

- 确认 API 密钥正确
- 检查网络连接
- 查看日志文件获取详细错误信息

### 问题 3: 动态内容无法获取

解决方案：

- 使用页面交互操作(Actions)
- 适当延长等待时间
- 添加点击和滚动操作确保内容加载

## 8. 示例：电子商务网站数据提取

以下是使用 Firecrawl 提取电子商务网站产品信息的完整示例：

```yaml
site:
  name: "电商示例"
  base_url: "https://example-shop.com/"

scraping:
  engine: "firecrawl"
  firecrawl_options:
    enableWebSearch: true
    formats: ["markdown", "json", "screenshot"]
    actions:
      - { type: "wait", milliseconds: 3000 }
      - { type: "click", selector: ".load-more-products" }
      - { type: "wait", milliseconds: 2000 }
      - { type: "scroll", direction: "down" }
      - { type: "wait", milliseconds: 1000 }
      - { type: "screenshot" }
      - { type: "scrape" }
  extract_prompt: "提取所有产品的名称、价格、评分和库存状态"
  targets:
    - url: "https://example-shop.com/products"

parsing:
  field_selectors:
    products:
      description: "产品列表"
    total_products:
      description: "产品总数"
    price_range:
      description: "价格范围"
```

运行命令：

```bash
python src/scrapers/firecrawl_integration.py --site ecommerce_example --extract
```

## 9. 参考资料

- [Firecrawl 官方文档](https://docs.firecrawl.dev/)
- [Extract 功能文档](https://docs.firecrawl.dev/features/extract)
- [Python SDK 文档](https://docs.firecrawl.dev/sdks/python)
- [页面交互操作说明](https://docs.firecrawl.dev/introduction#interacting-with-the-page-with-actions)
