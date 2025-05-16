# 黑猫投诉爬虫使用指南

本文档介绍如何使用通用网页爬虫框架中的黑猫投诉爬虫功能，包括配置、运行及 GitHub Actions 自动化设置。

## 功能概述

黑猫投诉爬虫可以自动获取黑猫投诉平台上的投诉信息，支持以下功能：

- 获取最新投诉列表
- 根据关键词搜索投诉（需要登录 Cookie）
- 输出结构化 JSON 数据
- 使用 AI 分析投诉内容并生成分析报告
- 通过 GitHub Actions 自动定时爬取和分析

## 配置说明

### 基本配置

黑猫投诉爬虫的配置文件位于`config/sites/heimao.yaml`，主要配置项包括：

```yaml
site_info:
  name: "黑猫投诉"
  base_url: "https://tousu.sina.com.cn"
  description: "黑猫投诉数据采集"

scraping:
  engine: "custom"
  custom_module: "src.scrapers.heimao_scraper"
  custom_function: "scrape_heimao"
  targets:
    - type: "latest" # 最新投诉列表
      limit: 10
    - type: "keyword" # 关键词搜索
      keywords: ["${HEIMAO_KEYWORDS}"] # 从环境变量获取关键词
  schedule: "0 9 * * *" # 每天早上9点执行
```

### 环境变量设置

爬虫需要以下环境变量：

- `HEIMAO_COOKIE`：黑猫投诉网站的 Cookie（可选，用于关键词搜索）
- `HEIMAO_KEYWORDS`：搜索关键词，多个关键词用逗号分隔（例如：`手机,电商,快递`）
- `OPENAI_API_KEY`或`GEMINI_API_KEY`：用于 AI 分析的 API 密钥
- `NOTIFICATION_WEBHOOK`：通知 webhook 地址（如钉钉、飞书等）
- `NOTIFICATION_TYPE`：通知类型（如`dingtalk`、`feishu`、`wechat`）
- `ENABLE_NOTIFICATION`：是否启用通知（`true`/`false`）

## 本地运行

### 手动运行爬虫

```bash
# 确保已安装依赖
pip install -r requirements.txt

# 设置环境变量（Linux/macOS）
export HEIMAO_COOKIE="your_cookie_here"
export HEIMAO_KEYWORDS="关键词1,关键词2"

# 运行爬虫
python src/scrapers/heimao_scraper.py
```

### 使用脚本运行

```bash
# 使用通用爬虫脚本运行
python scripts/scraper.py --site heimao
```

### AI 分析

```bash
# 分析指定日期的数据
python scripts/ai_analyzer.py --file data/daily/2023-10-01/heimao_data.json --site heimao
```

## GitHub Actions 自动化

黑猫投诉爬虫支持通过 GitHub Actions 自动运行，配置文件位于`.github/workflows/heimao_crawler.yml`。

### 设置步骤

1. Fork 或克隆本项目到您的 GitHub 仓库

2. 在 GitHub 仓库设置中添加以下密钥（Settings > Secrets and variables > Actions）:

   - `HEIMAO_COOKIE`：黑猫投诉网站的 Cookie
   - `HEIMAO_KEYWORDS`：要搜索的关键词，用逗号分隔
   - `OPENAI_API_KEY`或`GEMINI_API_KEY`：AI 服务的 API 密钥
   - 如需通知功能，还需设置`NOTIFICATION_WEBHOOK`、`NOTIFICATION_TYPE`和`ENABLE_NOTIFICATION`

3. 工作流会自动按照设定的计划（默认每天上午 9 点 UTC，对应北京时间 17 点）运行，也可以手动触发

### 查看结果

工作流运行后，结果会保存在以下位置：

- 爬取数据：`data/daily/YYYY-MM-DD/heimao_data.json`
- 分析报告：`analysis/daily/YYYY-MM-DD/heimao_analysis.md`
- 运行状态：`status/heimao_last_run.json`

这些文件将自动提交到仓库，您可以随时查看。同时，也可以在 GitHub Actions 的运行记录中下载这些文件作为构建产物（Artifacts）。

## 获取 Cookie 的方法

如需使用关键词搜索功能，需要提供有效的 Cookie，获取方法如下：

1. 使用浏览器（Chrome/Firefox/Edge 等）访问黑猫投诉网站：https://tousu.sina.com.cn/
2. 登录您的账号
3. 打开浏览器开发者工具（F12 或右键 > 检查）
4. 切换到"网络"（Network）标签
5. 刷新页面
6. 找到任意一个请求，在右侧 Headers 中找到"Cookie"项
7. 复制完整的 Cookie 值

注意：Cookie 有效期通常有限，如果爬虫报告 Cookie 无效，请重新获取。

## 常见问题

### Q: 如何修改爬取的数据量？

A: 编辑`config/sites/heimao.yaml`文件中的`limit`参数。

### Q: 没有 Cookie 能否使用？

A: 可以，但只能获取最新投诉列表，无法使用关键词搜索功能。

### Q: 如何调整自动运行的时间？

A: 修改`.github/workflows/heimao_crawler.yml`文件中的`cron`表达式。

### Q: 如何让 AI 分析使用特定的分析角度？

A: 编辑`config/analysis/prompts/heimao_prompt.txt`文件，修改提示词模板。

## 数据格式说明

爬虫输出的 JSON 数据格式如下：

```json
{
  "complaints": [
    {
      "id": "投诉ID",
      "title": "投诉标题",
      "company": "被投诉公司",
      "content": "投诉内容摘要",
      "url": "投诉详情链接",
      "timestamp": "投诉时间",
      "status": "投诉状态",
      "crawled_at": "爬取时间"
    }
    // 更多投诉记录...
  ]
}
```

## 实现原理

黑猫投诉爬虫通过模拟浏览器请求获取数据，主要步骤如下：

1. 生成请求签名参数（时间戳、随机字符串、哈希签名）
2. 构建请求 URL 和头信息
3. 发送请求获取 JSON 数据
4. 解析和过滤数据
5. 输出结构化结果

核心实现位于`src/scrapers/heimao_scraper.py`文件。
