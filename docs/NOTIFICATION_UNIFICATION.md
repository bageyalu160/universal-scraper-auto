# 通知系统统一方案

## 🎯 问题背景

项目中存在两套通知实现：

1. **Python 脚本**：使用 `apprise` 库实现统一通知
2. **GitHub Actions**：使用特定的 Actions（`fifsky/dingtalk-action`、`chf007/action-wechat-work`）

这种不一致导致：

- 配置分散，难以维护
- 功能重复，增加复杂性
- 扩展困难，添加新通知渠道需要修改多处

## ✅ 统一解决方案

### 核心思路

**统一使用 Apprise 库**，通过 Python 脚本 `scripts/notify.py` 处理所有通知。

### 方案优势

1. **统一配置**：所有通知配置集中在 `config/settings.yaml`
2. **多渠道支持**：Apprise 支持 100+ 种通知服务
3. **易于扩展**：添加新渠道只需修改配置文件
4. **避免重复**：不需要在每个工作流中重复配置

## 🔧 实施细节

### 1. 依赖管理

在 `requirements.txt` 中：

```
apprise>=1.9.0  # 通用通知库，支持多种通知渠道
```

### 2. 配置文件

在 `config/settings.yaml` 中：

```yaml
notification:
  enabled: true

  # 钉钉通知
  dingtalk:
    enabled: true
    webhook_env: "DINGTALK_WEBHOOK_URL"
    secret: ""

  # 飞书通知
  feishu:
    enabled: true
    webhook_env: "FEISHU_WEBHOOK_URL"

  # 企业微信通知
  wechat:
    enabled: true
    webhook_env: "WECHAT_WORK_WEBHOOK_URL"

  # 其他 Apprise 支持的服务
  apprise_urls:
    - "tgram://bot_token/chat_id" # Telegram
    - "discord://webhook_id/token" # Discord
    - "mailto://user:pass@gmail.com" # 邮件
```

### 3. 工作流模板更新

#### 原来的方式（已废弃）：

```yaml
- name: 发送钉钉通知
  uses: fifsky/dingtalk-action@master
  with:
    url: ${{ secrets.DINGTALK_WEBHOOK }}
    type: markdown
    content: ${{ steps.prepare_message.outputs.message }}

- name: 发送企业微信通知
  uses: chf007/action-wechat-work@master
  with:
    msgtype: markdown
    content: ${{ steps.prepare_message.outputs.message }}
    key: ${{ secrets.WECHAT_WEBHOOK }}
```

#### 新的统一方式：

```yaml
- name: 检出代码
  uses: actions/checkout@v4

- name: 设置Python环境
  uses: actions/setup-python@v4
  with:
    python-version: "3.9"

- name: 安装依赖
  run: pip install -r requirements.txt

- name: 发送通知
  env:
    DINGTALK_WEBHOOK_URL: ${{ secrets.DINGTALK_WEBHOOK }}
    FEISHU_WEBHOOK_URL: ${{ secrets.FEISHU_WEBHOOK }}
    WECHAT_WORK_WEBHOOK_URL: ${{ secrets.WECHAT_WEBHOOK }}
  run: |
    python scripts/notify.py --file "$ANALYSIS_FILE" --site "$SITE_ID"
```

### 4. 通知脚本增强

`scripts/notify.py` 现在支持：

- **分析结果通知**：处理数据分析结果
- **工作流状态通知**：处理工作流执行状态
- **仪表盘状态通知**：处理仪表盘更新状态

## 📋 迁移清单

### ✅ 已完成

- [x] 更新 `config/workflow/templates/utils.libsonnet`
- [x] 更新 `config/workflow/templates/master_workflow.jsonnet`
- [x] 更新 `config/workflow/templates/update_dashboard.yml.template`
- [x] 更新 `config/workflow/templates/crawler.yml.template`
- [x] 更新 `config/workflow/templates/analyzer.yml.template`
- [x] 更新 `config/workflow/templates/proxy_pool_manager.yml.template`
- [x] 增强 `scripts/notify.py` 支持多种状态文件
  - [x] 工作流状态通知
  - [x] 仪表盘状态通知
  - [x] 爬虫状态通知
  - [x] 分析器状态通知
  - [x] 代理池状态通知

### 🔄 需要完成

- [ ] 重新生成所有工作流文件
- [ ] 创建默认配置文件 `config/settings.yaml`
- [ ] 测试通知功能

## 🧪 测试方案

### 1. 本地测试

```bash
# 测试通知脚本
python scripts/notify.py --file "test_data.json" --site "测试站点"
```

### 2. 工作流测试

1. 手动触发一个简单的工作流
2. 检查通知是否正常发送
3. 验证消息格式和内容

### 3. 多渠道测试

1. 配置多个通知渠道
2. 验证所有渠道都能正常接收通知
3. 测试失败场景的处理

## 🔮 未来扩展

### 支持更多通知服务

通过 Apprise，可以轻松添加：

- Telegram
- Discord
- Slack
- 邮件
- SMS
- Pushover
- 等 100+ 种服务

### 通知模板定制

可以为不同类型的通知定制不同的消息模板：

```yaml
notification:
  templates:
    workflow_success: "✅ {site_name} 工作流执行成功"
    workflow_failure: "❌ {site_name} 工作流执行失败"
    analysis_complete: "📊 {site_name} 数据分析完成"
```

## 📚 相关文档

- [Apprise 官方文档](https://github.com/caronc/apprise)
- [支持的通知服务列表](https://github.com/caronc/apprise/wiki)
- [配置示例](https://github.com/caronc/apprise/wiki/config)
