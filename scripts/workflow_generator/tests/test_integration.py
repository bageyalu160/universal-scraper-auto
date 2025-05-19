#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 整合测试
"""

import os
import unittest
import tempfile
import yaml
import logging
from pathlib import Path
import shutil

from ..generator import WorkflowGenerator


class TestWorkflowIntegration(unittest.TestCase):
    """测试工作流生成器整合流程"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建临时目录
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # 创建测试需要的目录结构
        self.config_dir = self.temp_path / "config"
        self.sites_dir = self.config_dir / "sites"
        self.workflow_dir = self.config_dir / "workflow"
        self.templates_dir = self.workflow_dir / "templates"
        self.output_dir = self.temp_path / ".github" / "workflows"
        
        # 确保目录存在
        self.sites_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建基本设置文件
        self.settings_path = self.config_dir / "settings.yaml"
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            yaml.dump({
                'python_version': '3.10',
                'data_dir': 'data',
                'analysis_dir': 'analysis',
                'status_dir': 'status',
                'ai_analysis': {
                    'script_path': 'scripts/ai_analyzer.py',
                    'output_file': 'analysis_result.tsv',
                    'output_format': 'tsv'
                },
                'notification': {
                    'script_path': 'scripts/notify.py',
                    'enabled': True
                }
            }, f)
        
        # 创建示例站点配置
        self.site_config = self.sites_dir / "test_site.yaml"
        with open(self.site_config, 'w', encoding='utf-8') as f:
            yaml.dump({
                'site': {
                    'name': '测试站点',
                    'url': 'https://example.com'
                },
                'scraping': {
                    'engine': 'requests',
                    'schedule': '0 0 * * *',
                    'proxy': {
                        'enabled': True
                    }
                },
                'output': {
                    'filename': 'test_site_data.json'
                },
                'analysis': {
                    'enabled': True,
                    'model': 'openai/gpt-3.5-turbo'
                }
            }, f)
        
        # 创建测试模板
        self.create_test_templates()
        
        # 配置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('test_logger')
        
        # 初始化工作流生成器
        self.generator = WorkflowGenerator(
            settings_path=self.settings_path,
            sites_dir=self.sites_dir,
            output_dir=self.output_dir,
            logger=self.logger
        )
    
    def tearDown(self):
        """清理测试环境"""
        self.temp_dir.cleanup()
    
    def create_test_templates(self):
        """创建测试用的模板文件"""
        # 简化的爬虫工作流模板
        crawler_template = """
name: {{ site_name }} 爬虫任务

on:
  workflow_dispatch:
  schedule:
    - cron: "{{ cron_schedule }}"
  push:
    branches: [ main ]
    paths:
      - 'config/sites/{{ site_id }}.yaml'

env:
  PYTHON_VERSION: "{{ python_version }}"
  SITE_ID: "{{ site_id }}"
  TZ: "Asia/Shanghai"
  USE_PROXY: vars.USE_PROXY || 'true'

jobs:
  crawl:
    name: 运行爬虫
    runs-on: ubuntu-latest
    
    steps:
      - name: 检出代码
        uses: actions/checkout@v4
      
      - name: 设置Python环境
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: 安装依赖
        run: |
          python -m pip install --upgrade pip
          pip install {{ scraper_dependencies }}

      - name: 运行爬虫
        id: run_scraper
        continue-on-error: true
        env:
{% for env_var in env_vars %}
          {{ env_var.name }}: ${{ secrets.{{ env_var.secret }} }}
{% endfor %}
          USE_PROXY: ${{ env.USE_PROXY }}
        run: |
          echo "开始运行爬虫 (站点: $SITE_ID)"
          python {{ scraper_script }} --site $SITE_ID
      
      {% if run_analysis %}
      # 触发分析工作流
      - name: 触发分析工作流
        if: steps.run_scraper.outputs.file_exists == 'true'
        uses: benc-uk/workflow-dispatch@v1
        with:
          workflow: analyzer_{{ site_id }}.yml
          token: ${{ secrets.GITHUB_TOKEN }}
      {% endif %}
"""
        with open(self.templates_dir / "crawler.yml.template", 'w', encoding='utf-8') as f:
            f.write(crawler_template)
        
        # 简化的分析工作流模板
        analyzer_template = """
name: {{ site_name }} 分析任务

on:
  workflow_dispatch:
    inputs:
      data_date:
        description: '数据日期'
        required: false
        type: string
      site_id:
        description: '站点ID'
        required: false
        type: string
        default: '{{ site_id }}'

env:
  PYTHON_VERSION: "{{ python_version }}"
  SITE_ID: {% raw %}${{ inputs.site_id || '{{ site_id }}' }}{% endraw %}
  TZ: "Asia/Shanghai"
  OPENAI_API_KEY: {% raw %}${{ secrets.OPENAI_API_KEY }}{% endraw %}
  GEMINI_API_KEY: {% raw %}${{ secrets.GEMINI_API_KEY }}{% endraw %}

jobs:
  analyze:
    name: 分析数据
    runs-on: ubuntu-latest
    
    steps:
      - name: 检出代码
        uses: actions/checkout@v4
      
      - name: 设置Python环境
        uses: actions/setup-python@v5
        with:
          python-version: {% raw %}${{ env.PYTHON_VERSION }}{% endraw %}
      
      - name: 安装依赖
        run: |
          python -m pip install --upgrade pip
          pip install {{ analysis_dependencies }}

      - name: 运行分析
        id: run_analyzer
        continue-on-error: true
        run: |
          echo "开始运行分析 (站点: $SITE_ID)"
          python {{ analyzer_script }} --site $SITE_ID
"""
        with open(self.templates_dir / "analyzer.yml.template", 'w', encoding='utf-8') as f:
            f.write(analyzer_template)
    
    def test_generate_workflow(self):
        """测试生成工作流"""
        # 测试生成爬虫工作流
        result = self.generator.generate_workflow("test_site", "crawler")
        self.assertTrue(result, "生成爬虫工作流应该成功")
        
        # 验证输出文件存在
        crawler_path = self.output_dir / "crawler_test_site.yml"
        self.assertTrue(crawler_path.exists(), "应该生成爬虫工作流文件")
        
        # 验证内容
        with open(crawler_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查必要内容
        self.assertIn("测试站点 爬虫任务", content)
        self.assertIn("python", content)
        
        # 检查条件表达式处理
        self.assertIn("${{ env.USE_PROXY }}", content)
        
        # 检查变量替换
        self.assertIn("SITE_ID: \"test_site\"", content)
        
        # 测试生成分析工作流
        result = self.generator.generate_workflow("test_site", "analyzer")
        self.assertTrue(result, "生成分析工作流应该成功")
        
        # 验证输出文件存在
        analyzer_path = self.output_dir / "analyzer_test_site.yml"
        self.assertTrue(analyzer_path.exists(), "应该生成分析工作流文件")
    
    def test_crawler_workflow_direct(self):
        """测试直接生成爬虫工作流"""
        result = self.generator.generate_crawler_workflow_direct("test_site")
        self.assertTrue(result, "直接生成爬虫工作流应该成功")
        
        # 验证输出文件存在
        crawler_path = self.output_dir / "crawler_test_site.yml"
        self.assertTrue(crawler_path.exists(), "应该生成爬虫工作流文件")
    
    def test_generate_all_workflows(self):
        """测试生成所有工作流"""
        # 创建额外的站点配置
        extra_site = self.sites_dir / "another_site.yaml"
        with open(extra_site, 'w', encoding='utf-8') as f:
            yaml.dump({
                'site': {
                    'name': '另一个测试站点',
                    'url': 'https://example.org'
                },
                'scraping': {
                    'engine': 'playwright',
                    'schedule': '0 12 * * *'
                },
                'output': {
                    'filename': 'another_site_data.json'
                }
            }, f)
        
        # 创建示例配置（应该被跳过）
        example_site = self.sites_dir / "example.yaml"
        with open(example_site, 'w', encoding='utf-8') as f:
            yaml.dump({
                'site': {
                    'name': '示例站点',
                    'url': 'https://example.net'
                }
            }, f)
            
        result = self.generator.generate_all_workflows()
        self.assertTrue(result, "生成所有工作流应该成功")
        
        # 验证输出文件
        self.assertTrue((self.output_dir / "crawler_test_site.yml").exists())
        self.assertTrue((self.output_dir / "analyzer_test_site.yml").exists())
        self.assertTrue((self.output_dir / "crawler_another_site.yml").exists())
        self.assertTrue((self.output_dir / "analyzer_another_site.yml").exists())
        
        # 验证示例站点工作流未生成
        self.assertFalse((self.output_dir / "crawler_example.yml").exists())
    
    def test_update_workflows(self):
        """测试更新指定工作流"""
        result = self.generator.update_workflows("test_site")
        self.assertTrue(result, "更新指定工作流应该成功")
        
        # 验证输出文件
        self.assertTrue((self.output_dir / "crawler_test_site.yml").exists())
        self.assertTrue((self.output_dir / "analyzer_test_site.yml").exists())


if __name__ == "__main__":
    unittest.main() 