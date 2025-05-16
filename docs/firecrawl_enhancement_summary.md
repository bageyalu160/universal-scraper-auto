# Firecrawl 集成增强摘要

本文档总结了 Universal Scraper 项目中 Firecrawl 集成功能的最新增强。

## 1. 页面交互功能增强

### 1.1 支持的交互操作

我们增加了对以下页面交互操作的支持：

- **等待操作**: 等待指定毫秒数，适合等待页面加载或动态内容渲染

  ```yaml
  - { type: "wait", milliseconds: 2000 }
  ```

- **点击操作**: 点击指定 CSS 选择器的元素，如按钮、链接等

  ```yaml
  - { type: "click", selector: "button.show-more" }
  ```

- **滚动操作**: 控制页面滚动，可设置滚动方向

  ```yaml
  - { type: "scroll", direction: "down" }
  ```

- **截图操作**: 在交互过程中捕获页面截图

  ```yaml
  - { type: "screenshot" }
  ```

- **表单填写**: 向表单元素中输入文本

  ```yaml
  - { type: "write", selector: "input.search", text: "查询内容" }
  ```

- **按键操作**: 模拟键盘操作

  ```yaml
  - { type: "press", key: "Enter" }
  ```

- **执行 JavaScript**: 在页面上下文中执行自定义 JavaScript 代码
  ```yaml
  - {
      type: "executeJavascript",
      script: "document.querySelector('.menu').click()",
    }
  ```

### 1.2 实现方式

这些操作已在`scrape_url`方法中得到支持，允许用户通过配置文件定义交互序列，以获取动态内容或执行特定操作。

## 2. 多格式输出支持

### 2.1 支持的输出格式

增强了对多种输出格式的支持：

- **Markdown**: 结构化的文本内容
- **HTML**: 原始 HTML 内容
- **rawHTML**: 未处理的 HTML 源代码
- **Screenshot**: 页面截图
- **JSON**: 结构化数据
- **Links**: 页面中的所有链接

### 2.2 配置示例

```yaml
scraping:
  firecrawl_options:
    formats: ["markdown", "html", "screenshot"]
```

## 3. 无 Schema 提取能力

### 3.1 基于提示词的提取

现在支持仅基于自然语言提示词进行数据提取，无需定义固定 Schema：

```yaml
scraping:
  firecrawl_options:
    extract_prompt: "请提取所有API名称、描述、参数和示例代码"
    enableWebSearch: true
```

### 3.2 实现方式

`extract_structured_data`方法已更新，增加了对无 Schema 提取的支持，系统会基于提示词智能构建提取逻辑。

## 4. Web 搜索增强

增加了对网络搜索的支持，允许在提取过程中引入网络搜索结果，提升提取准确性：

```yaml
scraping:
  firecrawl_options:
    enableWebSearch: true
```

## 5. 配置文件优化

### 5.1 完整配置示例

对`firecrawl_example.yaml`进行了全面更新，提供了更完整的配置示例：

```yaml
site_info:
  name: "Firecrawl API文档"
  base_url: "https://docs.firecrawl.dev"
  description: "Firecrawl API文档示例"
  output_filename: "firecrawl_api_data.json"
  output_encoding: "utf-8"

scraping:
  engine: "firecrawl"
  firecrawl_options:
    formats: ["markdown", "html", "screenshot"]
    onlyMainContent: true
    actions:
      - { type: "wait", milliseconds: 2000 }
      - { type: "click", selector: "button.expand-all" }
      - { type: "scroll", direction: "down" }
      - { type: "screenshot" }
    extract_prompt: "提取API名称、描述、参数、返回值、示例代码和使用注意事项"
    enableWebSearch: true
  # ... 其他配置
```

## 6. 使用文档增强

更新了`docs/firecrawl_usage.md`文档，添加了：

1. 详细的交互操作配置指南
2. 无 Schema 提取说明
3. 多格式输出配置说明
4. 常见问题解决方案

## 7. 下一步计划

1. **添加缓存机制**：减少重复请求，提高效率
2. **批量处理优化**：改进大规模 URL 爬取的性能
3. **结果后处理**：增加提取结果的清洗和转换功能
4. **交互式调试**：开发交互式命令行工具用于调试配置
5. **自定义提示词模板**：为特定领域提取任务创建专用提示词模板

## 8. 已知限制

1. 部分复杂 JavaScript 渲染页面可能需要更多自定义交互操作
2. AI 提取的准确性取决于提示词质量和页面内容复杂度
3. 无 Schema 提取在高度非结构化内容上可能需要额外处理

---

以上增强大大提升了 Universal Scraper 对复杂网页内容的采集和结构化能力，特别是对动态渲染网站、需要用户交互才能展示内容的网站支持更加完善。
