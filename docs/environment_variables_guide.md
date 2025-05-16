# 环境变量使用指南

本文档描述了 Universal Scraper 项目中使用的关键环境变量，以及如何正确配置它们以确保爬虫和分析功能正常工作。

## 目录

- [通用环境变量](#通用环境变量)
- [站点特定环境变量](#站点特定环境变量)
  - [黑猫投诉](#黑猫投诉)
  - [PM001](#pm001)
  - [Firecrawl](#firecrawl)
- [环境变量配置方法](#环境变量配置方法)
  - [本地开发环境](#本地开发环境)
  - [GitHub Actions](#github-actions)
- [常见问题排查](#常见问题排查)

## 通用环境变量

| 环境变量               | 描述                                 | 必需 | 默认值 |
| ---------------------- | ------------------------------------ | ---- | ------ |
| `OPENAI_API_KEY`       | OpenAI API 密钥，用于 AI 分析        | 否\* | -      |
| `GEMINI_API_KEY`       | Google Gemini API 密钥，用于 AI 分析 | 否\* | -      |
| `ENABLE_NOTIFICATION`  | 是否启用通知功能                     | 否   | false  |
| `NOTIFICATION_TYPE`    | 通知类型（dingtalk/feishu/wechat）   | 否   | none   |
| `NOTIFICATION_WEBHOOK` | 通知 webhook 地址                    | 否   | -      |

\*注：如果启用了 AI 分析功能，则需要至少提供一种 AI 服务的 API 密钥。

## 站点特定环境变量

### 黑猫投诉

| 环境变量          | 描述                             | 必需 | 默认值 |
| ----------------- | -------------------------------- | ---- | ------ |
| `HEIMAO_COOKIE`   | 黑猫投诉网站的登录 Cookie        | 是   | -      |
| `HEIMAO_KEYWORDS` | 搜索关键词，多个关键词用逗号分隔 | 否   | -      |

#### 黑猫投诉 Cookie 获取方法

1. 使用浏览器登录黑猫投诉网站 (https://tousu.sina.com.cn)
2. 打开浏览器开发者工具（Chrome 中按 F12）
3. 切换到"Network"(网络)标签
4. 刷新页面
5. 找到任意一个请求，点击查看其 Headers(请求头)
6. 找到"Cookie"字段，复制完整的 Cookie 字符串

> **重要提示**：Cookie 包含敏感信息，请勿将其硬编码在代码中或提交到公开仓库。

### PM001

| 环境变量       | 描述                    | 必需 | 默认值 |
| -------------- | ----------------------- | ---- | ------ |
| `PM001_COOKIE` | PM001 网站的登录 Cookie | 否   | -      |

### Firecrawl

| 环境变量            | 描述               | 必需 | 默认值 |
| ------------------- | ------------------ | ---- | ------ |
| `FIRECRAWL_API_KEY` | Firecrawl API 密钥 | 是\* | -      |

\*注：仅当使用 Firecrawl 爬虫引擎时需要。

## 环境变量配置方法

### 本地开发环境

在本地开发环境中，可以通过以下方式设置环境变量：

#### Linux/macOS

```bash
# 设置环境变量
export HEIMAO_COOKIE="your_cookie_here"
export OPENAI_API_KEY="your_openai_api_key"

# 运行爬虫
python scripts/scraper.py --site heimao
```

#### Windows (CMD)

```batch
:: 设置环境变量
set HEIMAO_COOKIE=your_cookie_here
set OPENAI_API_KEY=your_openai_api_key

:: 运行爬虫
python scripts/scraper.py --site heimao
```

#### Windows (PowerShell)

```powershell
# 设置环境变量
$env:HEIMAO_COOKIE="your_cookie_here"
$env:OPENAI_API_KEY="your_openai_api_key"

# 运行爬虫
python scripts/scraper.py --site heimao
```

### GitHub Actions

在 GitHub Actions 中，有两种方式设置环境变量：

1. **Repository Secrets**：用于敏感信息，如 API 密钥和 Cookie
2. **Variables**：用于非敏感配置项

#### 设置 Repository Secrets

1. 进入 GitHub 仓库页面
2. 点击"Settings" > "Secrets and variables" > "Actions"
3. 点击"New repository secret"
4. 填写 Secret 名称（如`HEIMAO_COOKIE`）和值
5. 点击"Add secret"保存

#### 设置 Variables

1. 进入 GitHub 仓库页面
2. 点击"Settings" > "Secrets and variables" > "Actions"
3. 切换到"Variables"标签
4. 点击"New repository variable"
5. 填写变量名称（如`HEIMAO_KEYWORDS`）和值
6. 点击"Add variable"保存

## 工作流配置文件中添加环境变量

为确保 GitHub Actions 工作流中能够正确传递环境变量，需要在两个位置添加配置：

1. **工作流策略文件**：`scripts/workflow_generator/strategies/crawler.py`中添加环境变量

```python
# 步骤6: 运行爬虫脚本
scraper_env = {
    "OPENAI_API_KEY": "${{ secrets.OPENAI_API_KEY }}",
    "GEMINI_API_KEY": "${{ secrets.GEMINI_API_KEY }}",
    "HEIMAO_COOKIE": "${{ secrets.HEIMAO_COOKIE }}",  # 添加站点特定Cookie
    "HEIMAO_KEYWORDS": "${{ vars.HEIMAO_KEYWORDS || '' }}",
    # 其他环境变量...
}
```

2. **工作流模板文件**：`config/workflow/crawler.yml.template`中添加全局环境变量（可选，但推荐）

```yaml
# 全局环境变量
env:
  PYTHON_VERSION: "{{ python_version }}"
  RUN_DATE: {% raw %}${{ github.event.inputs.date || '' }}{% endraw %}
  # 添加站点特定的环境变量
  HEIMAO_COOKIE: {% raw %}${{ secrets.HEIMAO_COOKIE }}{% endraw %}
```

> **注意**：修改模板文件后，需要运行工作流生成器脚本更新工作流文件：
>
> ```bash
> python3 scripts/workflow_generator.py --site your_site_id
> ```

## 常见问题排查

### 问题：爬虫运行后没有获取数据

如果您看到类似以下日志：

```
未提供Cookie，搜索功能可能受限
总共获取到 0 条原始投诉数据
```

**可能原因**：

1. Cookie 环境变量未正确设置或传递
2. Cookie 已过期或无效

**解决方案**：

1. 检查环境变量是否正确设置
2. 为确保 Cookie 被正确传递，检查工作流文件中的环境变量配置
3. 重新获取有效的 Cookie

### 问题：GitHub Actions 中 Cookie 未被传递

**可能原因**：

1. Repository Secrets 中未设置 Cookie
2. 工作流文件中未配置环境变量传递

**解决方案**：

1. 检查 Repository Secrets 是否存在并正确命名
2. 检查工作流文件中是否包含环境变量配置
3. 重新生成工作流文件：`python3 scripts/workflow_generator.py --site heimao`

---

## 新增站点环境变量配置指南

当您添加新的站点爬虫时，如果需要使用特定的环境变量（如 Cookie 或 API 密钥），请按照以下步骤操作：

1. 在站点配置文件中定义环境变量名称：

```yaml
# config/sites/your_site.yaml
auth:
  cookie_env: "YOUR_SITE_COOKIE" # 存储Cookie的环境变量名
  required: true # 是否必需
```

2. 在爬虫脚本中正确获取环境变量：

```python
# 获取Cookie
cookie_env = auth.get('cookie_env')
cookie = os.environ.get(cookie_env) if cookie_env else None

# 检查必需的环境变量
if auth.get('required', False) and not cookie:
    logger.warning("未提供必需的Cookie环境变量")
```

3. 修改工作流策略文件，添加新的环境变量：

```python
# scripts/workflow_generator/strategies/crawler.py
scraper_env = {
    # 现有环境变量...
    "YOUR_SITE_COOKIE": "${{ secrets.YOUR_SITE_COOKIE }}",
    # 其他环境变量...
}
```

4. 重新生成工作流文件：

```bash
python3 scripts/workflow_generator.py --site your_site_id
```

遵循以上步骤，可以确保您的新站点爬虫能够正确接收和使用所需的环境变量。
