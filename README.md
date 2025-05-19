# Universal Scraper | 通用网页爬虫框架

一个功能强大、高度可配置的网页数据采集和 AI 分析框架，专为研究和数据分析项目设计。

## 功能特点

- 🔍 **高度可配置** - 通过 YAML 配置文件轻松定义爬取目标和规则，无需编写代码
- 🤖 **AI 驱动分析** - 使用 LLM 模型（Gemini 或 OpenAI）自动分析和结构化网页数据
- 📊 **结构化输出** - 支持多种输出格式（JSON, CSV, TSV 等）
- 🔄 **自动化工作流** - 集成 GitHub Actions，实现定时爬取和分析
- 📱 **多渠道通知** - 支持钉钉、飞书、企业微信等通知渠道
- 🛡️ **稳定可靠** - 内置错误处理和重试机制，确保数据采集可靠性
- 🌐 **多引擎支持** - 支持常规 HTTP 请求、Playwright 和 Firecrawl 等多种爬取引擎
- 🚀 **页面交互支持** - 支持页面点击、滚动、表单填写等交互操作获取动态内容
- 🌍 **多语言支持** - 支持多语言网站内容采集和处理
- 🔐 **IP 代理池** - 内置动态 IP 代理池，支持自动验证和轮换
- 🕵️ **反爬虫机制** - 完善的浏览器指纹伪装和验证码处理能力
- 📈 **监控系统** - 基于 GitHub Pages 的可视化监控和管理系统

## 项目结构

```
universal-scraper/
├── config/                   # 配置文件目录
│   ├── sites/                # 站点配置文件
│   │   ├── example.yaml      # 示例站点配置
│   │   ├── firecrawl_example.yaml # Firecrawl示例配置
│   │   ├── heimao.yaml       # 黑猫投诉站点配置
│   │   └── pm001.yaml        # PM001钱币收藏网站配置
│   ├── analysis/             # AI分析配置
│   │   ├── prompts/          # 分析提示词模板
│   │   │   ├── general_prompt.txt    # 通用提示词
│   │   │   ├── heimao_prompt.txt     # 黑猫投诉分析提示词
│   │   │   └── pm001_prompt.txt      # PM001分析提示词
│   │   └── ...
│   ├── workflow/             # 工作流模板
│   │   ├── crawler.yml.template     # 爬虫工作流模板
│   │   ├── analyzer.yml.template    # 分析工作流模板
│   │   └── ...
│   └── settings.yaml         # 全局设置
├── scripts/                  # 脚本目录
│   ├── scraper.py            # 爬虫脚本
│   ├── ai_analyzer.py        # AI分析脚本
│   ├── notify.py             # 通知脚本
│   ├── playwright_test.py    # Playwright测试脚本
│   └── workflow_generator.py # 工作流生成器
├── .github/                  # GitHub相关文件
│   ├── workflows/            # GitHub Actions工作流
│   │   ├── heimao_crawler.yml # 黑猫投诉爬虫工作流
│   │   ├── pm001_crawler.yml  # PM001爬虫工作流
│   │   └── deploy_pages.yml   # 部署监控页面工作流
│   └── pages/                # GitHub Pages页面
│       └── dashboard/        # 监控仪表盘
├── data/                     # 数据存储目录
│   └── daily/                # 按日期存储的数据
├── analysis/                 # 分析结果目录
│   └── daily/                # 按日期存储的分析结果
├── docs/                     # 文档目录
│   ├── firecrawl_usage.md    # Firecrawl使用文档
│   ├── heimao_usage.md       # 黑猫投诉使用文档
│   └── ...                   # 其他文档
├── status/                   # 状态文件目录
├── src/                      # 源代码目录
│   ├── scrapers/             # 爬虫实现
│   │   ├── firecrawl_integration.py  # Firecrawl集成
│   │   ├── heimao_scraper.py         # 黑猫投诉爬虫
│   │   ├── integration_example.py    # 代理池和反爬集成示例
│   │   └── ...
│   ├── analyzers/            # 分析器实现
│   ├── parsers/              # 解析器实现
│   ├── notifiers/            # 通知器实现
│   ├── storage/              # 存储实现
│   └── utils/                # 工具函数
│       ├── proxy_pool.py     # 代理池管理
│       ├── anti_detect.py    # 反爬虫检测
│       └── ...
├── requirements.txt          # 项目依赖
└── README.md                 # 项目说明
```

## 版本信息

- **当前版本**: v1.1.0
- **上次更新**: 2023-11-20

## 快速开始

### 安装

1. 克隆仓库

   ```bash
   git clone https://github.com/yourusername/universal-scraper.git
   cd universal-scraper
   ```

2. 安装依赖

   ```bash
   pip install -r requirements.txt
   ```

3. 安装项目包（开发模式）

   ```bash
   pip install -e .
   ```

4. 安装 Playwright 浏览器

   ```bash
   playwright install --with-deps
   ```

5. 设置环境变量
   ```bash
   # 根据您使用的AI提供商设置API密钥
   export OPENAI_API_KEY=your_openai_api_key
   # 或
   export GEMINI_API_KEY=your_gemini_api_key
   # Firecrawl API密钥（如果使用Firecrawl）
   export FIRECRAWL_API_KEY=your_firecrawl_api_key
   ```

### 创建站点配置

1. 在`config/sites/`目录下创建新的 YAML 配置文件（例如`mysite.yaml`）
2. 参考`example.yaml`模板填写配置

### 运行爬虫

```bash
# 基本爬虫运行
python scripts/scraper.py --site mysite

# 黑猫投诉爬虫
python scripts/scraper.py --site heimao

# PM001钱币网站爬虫
python scripts/scraper.py --site pm001
```

### 使用 Firecrawl 增强版爬虫

```bash
python src/scrapers/firecrawl_integration.py --site firecrawl_example --extract
```

### 运行 AI 分析

```bash
# 基本分析
python scripts/ai_analyzer.py --file data/daily/2023-01-01/mysite_data.json --site mysite

# 黑猫投诉分析
python scripts/ai_analyzer.py --file data/daily/2023-01-01/heimao_data.json --site heimao

# PM001网站数据分析
python scripts/ai_analyzer.py --file data/daily/2023-01-01/pm001_data.tsv --site pm001
```

### 生成工作流

```bash
# 为单个站点生成工作流
python scripts/workflow_generator.py --site mysite

# 为所有站点生成工作流
python scripts/workflow_generator.py --all
```

### 运行 Playwright 测试

```bash
# 运行单个浏览器测试
python scripts/playwright_test.py --browser chromium

# 运行所有浏览器测试
python scripts/playwright_test.py --browser all
```

## 使用代理池

代理池功能提供了 IP 轮换、验证和管理能力，适用于需要定期更换 IP 地址的爬虫场景。

### 在站点配置中启用代理池

```yaml
# config/sites/mysite.yaml
scraping:
  use_proxy: true # 是否使用代理
  rotate_proxy: true # 是否轮换代理IP
  max_retries: 3 # 最大重试次数
  retry_delay: 2 # 重试间隔(秒)

  # 代理池配置
  proxy_pool:
    update_interval: 3600 # 代理更新间隔(秒)
    timeout: 5 # 代理测试超时时间(秒)
    max_fails: 3 # 代理失败最大次数，超过后从可用列表移除
    sources: # 代理源配置
      - type: api
        url: "https://some-proxy-api.com/get"
        headers: # 自定义请求头(可选)
          Authorization: "Bearer your_token"
      - type: file
        path: "data/proxies.txt"
```

### 在代码中使用代理池

```python
from src.utils.proxy_pool import get_proxy, report_proxy_status

# 获取代理
proxy = get_proxy(rotate=True)  # 轮换模式获取代理

# 使用代理发送请求
response = requests.get("https://example.com", proxies=proxy)

# 报告代理状态
report_proxy_status(proxy, success=True)  # 成功使用
# 或
report_proxy_status(proxy, success=False)  # 使用失败
```

### 代理池管理命令

```bash
# 更新代理池
python -c "from src.utils.proxy_pool import get_proxy_pool; get_proxy_pool().update_proxies(force=True)"

# 验证所有代理
python -c "from src.utils.proxy_pool import get_proxy_pool; get_proxy_pool()._validate_proxies()"
```

## 使用反爬机制

反爬机制提供了浏览器指纹伪装和验证码处理能力，帮助爬虫绕过常见的反爬措施。

### 在站点配置中配置反爬机制

```yaml
# config/sites/mysite.yaml
scraping:
  anti_detection:
    browser_fingerprint: true # 启用浏览器指纹伪装
    captcha_solver: true # 启用验证码处理

    # 验证码处理配置(可选)
    captcha:
      default_provider: "local" # 默认验证码解决提供商
      providers:
        - name: "2captcha"
          api_key: "your_2captcha_key"
        - name: "anti-captcha"
          api_key: "your_anticaptcha_key"
```

### 在代码中使用反爬机制

```python
from src.utils.anti_detect import get_user_agent, get_browser_fingerprint, solve_captcha

# 获取随机用户代理
user_agent = get_user_agent(device_type="desktop", browser_type="chrome")

# 获取浏览器指纹
fingerprint = get_browser_fingerprint(fp_id="your_fingerprint_id")

# 使用浏览器指纹中的请求头
headers = fingerprint['headers']

# 解决验证码
captcha_result = solve_captcha(
    image_path="path/to/captcha.jpg",
    provider="2captcha"  # 或 "local", "anti-captcha"
)
```

### 获取 Playwright 浏览器选项

```python
from src.utils.anti_detect import get_playwright_options

# 获取Playwright选项
playwright_options = get_playwright_options(fp_id="your_fingerprint_id")

# 在Playwright中使用
browser = await playwright.chromium.launch()
context = await browser.new_context(**playwright_options)
```

### 获取 Selenium 浏览器选项

```python
from src.utils.anti_detect import get_selenium_options
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 获取Selenium选项
selenium_opts = get_selenium_options(fp_id="your_fingerprint_id", browser_type="chrome")

# 在Selenium中使用
chrome_options = Options()
for arg in selenium_opts['arguments']:
    chrome_options.add_argument(arg)

# 添加实验性选项
for key, value in selenium_opts['experimental_options'].items():
    chrome_options.add_experimental_option(key, value)

# 创建WebDriver
driver = webdriver.Chrome(options=chrome_options)
```

## 使用集成爬虫示例

查看`src/scrapers/integration_example.py`文件，获取完整的集成爬虫示例，包括：

- 代理池轮换和验证
- 浏览器指纹伪装
- 验证码自动处理
- 错误重试机制
- 爬虫状态报告

## 使用监控系统

项目集成了基于 GitHub Pages 的监控仪表盘，提供以下功能：

- 爬虫任务运行状态监控
- 代理池状态和管理
- 采集数据统计和可视化
- 系统日志查看

### 访问监控仪表盘

监控仪表盘部署在 GitHub Pages 上，可通过以下 URL 访问：

```
https://your-username.github.io/universal-scraper/
```

### 手动部署监控仪表盘

```bash
# 手动触发部署工作流
gh workflow run deploy_pages.yml
```

## 配置说明

### 站点配置

站点配置文件（`config/sites/mysite.yaml`）包含爬取特定网站所需的所有参数：

```yaml
site_info:
  name: "网站名称"
  base_url: "https://example.com"
  description: "网站描述"

scraping:
  targets:
    - url: "/path"
      method: "GET"
  schedule: "0 0 * * *" # 每天午夜执行

  # 代理和反爬设置
  use_proxy: true
  rotate_proxy: true
  anti_detection:
    browser_fingerprint: true
    captcha_solver: true

parsing:
  selector_type: "css" # 或 "xpath"
  field_selectors:
    title: "h1.title"
    content: "div.content"
    date: "span.date"

output:
  format: "json" # 或 "csv", "tsv"
  filename: "mysite_data.json"
```

### 全局设置

全局设置文件（`config/settings.yaml`）配置框架的整体行为：

```yaml
# 一般设置
default_site: "example"
run_mode: "local" # 本地运行或GitHub Actions
data_dir: "data"
analysis_dir: "analysis"
status_dir: "status"

# AI分析设置
ai_analysis:
  provider: "gemini" # 或 "openai"
  api_key_env: "GEMINI_API_KEY"
  output_format: "tsv"
```

## 高级使用

### 使用 Firecrawl 增强爬取能力

本框架集成了 Firecrawl，这是一个强大的爬虫工具，特别适合处理复杂的、JavaScript 渲染的网站。

1. 配置 Firecrawl

   在站点配置中添加 Firecrawl 特定配置：

   ```yaml
   scraping:
     engine: "firecrawl" # 使用Firecrawl引擎
     firecrawl_options: # Firecrawl特定选项
       formats: ["markdown", "html", "json", "screenshot"]
       onlyMainContent: true # 只提取主要内容
       enableWebSearch: true # 启用Web搜索增强提取
       # 页面交互操作
       actions:
         - { type: "wait", milliseconds: 2000 } # 等待2秒
         - { type: "click", selector: "button.show-more" } # 点击按钮
         - { type: "screenshot" } # 截图
     extract_prompt: "提取API名称、描述和参数" # 提取提示词
   ```

2. 运行 Firecrawl 爬虫

   ```bash
   python src/scrapers/firecrawl_integration.py --site firecrawl_example --extract
   ```

详细使用说明请参考[Firecrawl 使用指南](docs/firecrawl_usage.md)。

### PM001 钱币网站数据采集

本框架集成了 PM001 钱币收藏网站的数据采集功能，可以自动获取该网站上的交易信息。

1. PM001 爬虫配置样例

   ```yaml
   # PM001网站爬虫配置
   site:
     name: "PM001"
     description: "PM001钱币收藏交易平台"
     base_url: "http://www.pm001.net/"
     output_filename: "pm001_recent_posts.tsv"
     encoding: "gbk"

   scraping:
     # 爬取的板块ID列表
     board_ids:
       - id: 5
         name: "小版张专栏"
         category: "邮票类"
       - id: 2
         name: "钱币大卖场"
         category: "钱币类"
       # 更多板块...

     # 时间范围设置
     time_range:
       days_limit: 2 # 抓取最近几天的帖子

     # 分页设置
     pagination:
       pages_per_board: 2 # 每个板块抓取的页数
   ```

2. 运行 PM001 爬虫

   ```bash
   python scripts/scraper.py --site pm001
   ```

3. 查看生成的数据

   数据将以 TSV 格式保存在`data/daily/`目录下，文件名格式为`pm001_recent_posts_YYYY-MM-DD.tsv`。

### 自定义分析提示词

1. 在`config/analysis/prompts/`目录下创建新的提示词文件
2. 文件名应为`{site_id}_prompt.txt`格式

### 使用 GitHub Actions 自动化

1. 生成工作流文件

   ```bash
   python scripts/workflow_generator.py --all
   ```

2. 在 GitHub 仓库设置中添加密钥:

   - `OPENAI_API_KEY` 或 `GEMINI_API_KEY`
   - `FIRECRAWL_API_KEY`（如果使用 Firecrawl）

3. 推送代码到 GitHub，工作流将按照配置的计划自动运行

### GitHub Actions 权限和变量设置

在使用 GitHub Actions 进行自动爬虫和分析前，需要正确配置以下权限和变量：

#### 1. 仓库权限设置

1. 打开仓库的"Settings" > "Actions" > "General"
2. 在"Workflow permissions"部分，选择"Read and write permissions"
3. 勾选"Allow GitHub Actions to create and approve pull requests"
4. 点击"Save"保存设置

#### 2. Secrets 和 Variables 设置

在仓库的"Settings" > "Secrets and variables" > "Actions"中添加以下密钥：

##### 必需的 Secrets：

- `GITHUB_TOKEN` - 用于工作流之间的触发，系统会自动提供
- `OPENAI_API_KEY` 或 `GEMINI_API_KEY` - 根据您选择的 AI 分析提供商设置

##### 特定爬虫需要的 Secrets：

- `HEIMAO_COOKIE` - 黑猫投诉平台的登录 Cookie
- `FIRECRAWL_API_KEY` - 如果使用 Firecrawl 爬虫引擎

##### 可选的 Variables：

- `HEIMAO_KEYWORDS` - 黑猫投诉搜索关键词，多个关键词用逗号分隔
- `ENABLE_NOTIFICATION` - 是否启用通知功能（true/false）
- `NOTIFICATION_TYPE` - 通知类型（dingtalk/feishu/wechat）
- `NOTIFICATION_WEBHOOK` - 通知 webhook 地址

#### 3. 工作流文件权限设置

每个工作流文件（.github/workflows/下的 YAML 文件）需要包含适当的权限声明：

```yaml
permissions:
  contents: write # 允许写入仓库内容
  actions: write # 允许触发其他工作流
```

#### 4. 手动触发工作流

1. 打开仓库的"Actions"标签页
2. 选择要运行的工作流（如"黑猫投诉 爬虫任务"）
3. 点击"Run workflow"
4. 根据需要填写输入参数（如日期）
5. 点击"Run workflow"开始执行

#### 5. 工作流间触发

如果需要从一个工作流触发另一个工作流，确保：

1. 使用有足够权限的 token：

   ```yaml
   uses: benc-uk/workflow-dispatch@v1
   with:
     workflow: 目标工作流文件名
     token: ${{ secrets.GITHUB_TOKEN }}
     inputs: '{"key": "value"}'
   ```

2. 在使用 `workflow_dispatch` 时，确保提供所有必要的输入参数

配置正确后，GitHub Actions 将能够按计划或手动触发运行爬虫和分析任务，并自动提交结果到仓库。

### 使用 Playwright 进行自动化测试

本项目集成了 Playwright 进行浏览器自动化测试，支持在 GitHub Actions 中运行。

1. 安装 Playwright 浏览器

   ```bash
   playwright install --with-deps
   ```

2. 运行测试脚本

   ```bash
   python scripts/playwright_test.py --browser chromium
   ```

3. 查看测试报告

   测试报告将生成在 `playwright-report` 目录下，包括截图和 HTML 报告文件。

4. GitHub Actions 自动化测试

   项目在 GitHub Actions 中使用矩阵策略，自动在多种浏览器上运行测试。
   可以在 Actions 标签页中查看测试结果和下载测试报告。

### 黑猫投诉数据采集

本框架集成了黑猫投诉数据采集功能，可以自动获取黑猫投诉平台上的投诉信息。

1. 配置黑猫投诉爬虫

   ```yaml
   site_info:
     name: "黑猫投诉"
     base_url: "https://tousu.sina.com.cn"
     description: "黑猫投诉数据采集"

   scraping:
     engine: "custom" # 使用自定义引擎
     targets:
       - type: "latest" # 最新投诉列表
       - type: "keyword" # 关键词搜索
         keywords: ["${HEIMAO_KEYWORDS}"] # 从环境变量获取关键词
   ```

2. 设置必要的环境变量

   ```bash
   export HEIMAO_COOKIE="your_cookie_here"  # 获取Cookie方法见文档
   export HEIMAO_KEYWORDS="关键词1,关键词2"
   ```

3. 运行黑猫投诉爬虫

   ```bash
   python scripts/scraper.py --site heimao
   ```

4. 使用 GitHub Actions 自动化

   在仓库的 Secrets 中添加必要的环境变量，GitHub Actions 将按计划自动运行爬虫并分析数据。

详细使用说明请参考[黑猫投诉使用指南](docs/heimao_usage.md)。

## 数据处理工作流程

+----------------------------------+
| 配置阶段 |
+----------------------------------+
| 1. 创建站点配置文件(YAML) |
| 2. 设置 AI 分析提示词模板 |
| 3. 配置通知渠道 |
| 4. 配置工作流(可选) |
+------------------+---------------+
|
v
+----------------------------------+
| 爬虫阶段 |
+----------------------------------+
| 1. 加载站点配置 |
| 2. 选择爬虫引擎: |
| - HTTP 请求爬虫 |
| - Playwright 浏览器自动化 |
| - Firecrawl 增强爬虫 |
| 3. 执行爬取任务 |
| 4. 解析页面内容 |
| 5. 存储结构化数据 |
+------------------+---------------+
|
v
+----------------------------------+
| 分析阶段 |
+----------------------------------+
| 1. 读取爬取的数据 |
| 2. 选择 AI 服务: |
| - OpenAI |
| - Google Gemini |
| 3. 加载分析提示词 |
| 4. 执行 AI 分析 |
| 5. 解析 AI 响应 |
| 6. 输出结构化分析结果 |
+------------------+---------------+
|
v
+----------------------------------+
| 通知阶段 |
+----------------------------------+
| 1. 生成任务报告 |
| 2. 选择通知渠道: |
| - 钉钉 |
| - 飞书 |
| - 企业微信 |
| - 其他渠道 |
| 3. 发送通知 |
+------------------+---------------+
|
v
+----------------------------------+
| 自动化阶段(可选) |
+----------------------------------+
| 1. 生成 GitHub Actions 工作流 |
| 2. 配置定时任务 |
| 3. 设置触发条件 |
| 4. 自动执行完整工作流: |
| 爬取->分析->通知 |
+----------------------------------+

## 性能与资源消耗

### 硬件推荐配置

- **CPU**: 双核或更高配置
- **内存**: 至少 4GB RAM（使用 Playwright 或 Firecrawl 推荐 8GB+）
- **存储**: 50MB 基础代码 + 数据存储空间（根据爬取规模而定）
- **网络**: 稳定的互联网连接

### 资源消耗估算

| 爬取引擎   | 内存占用 | CPU 占用 | 网络流量/1000 页 | 适用场景                         |
| ---------- | -------- | -------- | ---------------- | -------------------------------- |
| HTTP 请求  | 低       | 低       | ~50-100MB        | 简单静态网页                     |
| Playwright | 中-高    | 中       | ~200-500MB       | 动态页面、需要交互的网站         |
| Firecrawl  | 中       | 中-高    | ~300-700MB       | 复杂 JS 渲染、需要云端处理的站点 |

### AI 分析资源消耗

| AI 提供商 | 处理速度 | 成本估算            | 特点                   |
| --------- | -------- | ------------------- | ---------------------- |
| OpenAI    | 快       | ~$0.02-0.10/1000 条 | 高精度、支持复杂指令   |
| Gemini    | 中       | ~$0.01-0.05/1000 条 | 性价比高、多模态能力强 |

## 常见问题与排障 (FAQ)

### 爬虫相关问题

1. **Q: 爬虫运行后没有数据输出?**  
   A: 检查以下几点:

   - 确认网站是否有反爬机制
   - 验证选择器是否正确
   - 检查网络连接是否稳定
   - 查看日志文件获取详细错误信息

2. **Q: 如何处理需要登录的网站?**  
   A: 可以使用 Cookie 或 Session 机制:

   - 在配置文件中添加 headers 部分包含 Cookie
   - 对于复杂情况，使用 Playwright 进行自动登录操作

3. **Q: 爬取速度过慢怎么办?**  
   A: 可以尝试以下优化:
   - 减少请求间隔时间（注意控制在合理范围）
   - 使用异步请求方式
   - 增加并发数（注意不要过高导致被封 IP）

### AI 分析相关问题

1. **Q: AI 分析结果质量不佳?**  
   A: 尝试以下方法:

   - 优化提示词模板
   - 尝试不同的 AI 提供商
   - 减少单次分析的数据量

2. **Q: AI API 调用失败?**  
   A: 检查以下几点:
   - 确认 API 密钥是否正确设置
   - 检查 API 额度是否已用完
   - 查看网络连接是否稳定

### GitHub Actions 相关问题

1. **Q: 工作流运行失败?**  
   A: 常见原因和解决方法:
   - Secret 未正确设置，检查 GitHub 仓库的 Secrets 配置
   - 权限问题，确认 workflow 文件中包含正确的 permissions 设置
   - 网络问题，可以在 Actions 日志中查看详细错误信息

## 安全性与合规性考虑

1. **遵守网站 robots.txt 规则**  
   爬虫默认会检查并遵守目标网站的 robots.txt 规则，请勿修改此行为。

2. **控制爬取频率**  
   为避免对目标网站造成过大负载，请合理设置请求间隔时间。

3. **数据使用合规性**  
   请确保您爬取的数据仅用于合法、合规的用途，并遵守相关法律法规。

4. **API 密钥安全**  
   请务必妥善保管您的 API 密钥，不要将其硬编码在代码中或提交到公开仓库。

## 开发者扩展指南

框架设计为易于扩展，以下是添加新功能的一般步骤:

### 添加新爬虫引擎

1. 在`src/scrapers/`目录下创建新的爬虫实现文件
2. 在配置系统中添加对应的引擎选项
3. 在主爬虫脚本中集成新引擎

### 添加新分析器

1. 在`src/analyzers/`目录下创建新的分析器实现
2. 在`config/analysis/prompts/`添加对应的提示词模板
3. 在分析脚本中集成新分析器

### 添加新通知渠道

1. 在`src/notifiers/`目录下实现新的通知渠道
2. 在通知脚本中集成新通知渠道

## 数据输出示例

### 黑猫投诉数据示例

```json
{
  "id": "123456",
  "title": "关于某品牌手机售后服务问题的投诉",
  "content": "购买的手机在保修期内出现故障，多次联系售后无人处理...",
  "submit_time": "2023-04-05 10:30:45",
  "status": "已处理",
  "category": "电子产品",
  "brand": "某手机品牌",
  "user_location": "北京市"
}
```

### PM001 数据示例

```csv
board_id,board_name,post_id,title,author,date,replies,views
5,"小版张专栏",12345,"2023年邮票小版张全套",user123,"2023-05-01",10,500
2,"钱币大卖场",12346,"早期1元纪念币10枚",coin_seller,"2023-04-30",5,320
```

## 贡献指南

我们欢迎各种形式的贡献，包括但不限于:

1. **报告 Bug**: 创建一个详细的 Issue 描述问题
2. **提交功能请求**: 通过 Issue 提交新功能想法
3. **提交代码**: 通过 Pull Request 贡献代码
   - Fork 仓库
   - 创建功能分支 (`git checkout -b feature/amazing-feature`)
   - 提交更改 (`git commit -m 'Add amazing feature'`)
   - 推送到分支 (`git push origin feature/amazing-feature`)
   - 创建 Pull Request

### 代码规范

- 遵循 PEP 8 编码规范
- 添加适当的注释和文档字符串
- 为新功能编写单元测试

## 更新日志

### v1.0.0 (2023-05-15)

- 初始版本发布
- 支持基本 HTTP 爬虫、Playwright 和 Firecrawl 引擎
- 集成 OpenAI 和 Gemini AI 分析功能
- 实现 GitHub Actions 自动化工作流
- 添加黑猫投诉和 PM001 网站爬虫实现

### v1.1.0 (2023-11-20)

- 添加代理池和反爬机制支持
- 集成基于 GitHub Pages 的监控系统

## 最新更新（代理池与反爬机制增强）

为了提高爬虫的稳定性和成功率，我们对代理池管理和反爬虫机制进行了以下增强：

### 代理池管理增强

1. **代理池与工作流集成**

   - 将代理池管理完全集成到主爬虫工作流
   - 自动检查代理数量，确保爬虫任务前有足够可用代理
   - 爬虫任务后更新代理使用统计

2. **异常恢复机制**

   - 添加代理失效自动恢复功能
   - 支持多级故障转移策略（更新->恢复->重建）
   - 代理数量低于阈值时触发自动恢复

3. **代理轮换策略优化**
   - 智能代理轮换，减少被封风险
   - 失败代理自动报告和更换
   - 代理统计和状态持久化

### 反爬虫机制增强

1. **浏览器行为模拟**

   - 模拟真实用户的浏览行为（引荐页面访问、页面停留时间）
   - 请求序列聚类，使请求模式更自然
   - 表单交互模拟

2. **智能延迟管理**

   - 基于正态分布的随机延迟，更贴近真实用户行为
   - 自适应延迟策略，根据网站响应调整
   - 多种预设延迟策略（从超快到隐身模式）

3. **封锁检测与规避**

   - 自动识别多种封锁模式
   - 检测到封锁时智能重试
   - IP 轮换与浏览器指纹更换结合

4. **工作流模板标准化**
   - 统一更新各工作流模板，确保一致性
   - 增强错误处理和重试逻辑
   - 完整的状态报告和通知

### 使用示例

```python
# 使用代理池和反爬机制的爬虫示例
from src.utils.proxy_pool import get_proxy, report_proxy_status
from src.utils.anti_detect import create_request_pattern_manager

# 创建请求模式管理器
request_manager = create_request_pattern_manager('example_site', {
    'delay_strategy': 'normal',
    'proxy': {
        'enabled': True,
        'rotation_count': 5,
        'rotate_on_failure': True
    }
})

# 获取待爬取的URL列表
urls = ['https://example.com/page1', 'https://example.com/page2', '...']

# 随机化请求顺序，模拟真实用户行为
urls = request_manager.randomize_requests(urls)

# 使用重试机制执行请求
import requests
for url in urls:
    response, success = request_manager.execute_with_retry(requests.get, url)
    if success:
        # 处理成功响应
        process_data(response)
    else:
        # 处理失败
        log_failure(url)
```

## 许可证

MIT License

## 工作流生成器更新

工作流生成器已更新，支持生成通用工作流文件：

- **主调度工作流(master_workflow.yml)**：用于协调多个站点的爬取和分析任务
- **仪表盘更新工作流(update_dashboard.yml)**：用于构建和部署监控仪表盘

### 使用方法

```bash
# 生成通用工作流
python3 scripts/workflow_generator.py --type common

# 生成所有工作流（包括通用工作流和站点特定工作流）
python3 scripts/workflow_generator.py --type all --all
```

详细使用说明请参阅[工作流生成器使用指南](docs/workflow_usage.md)。
