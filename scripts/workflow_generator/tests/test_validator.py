#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 验证器测试
"""

import os
import unittest
from pathlib import Path
import tempfile
import yaml

from ..validators.workflow_validator import WorkflowValidator
from ..renderers.yaml_renderer import WorkflowYamlRenderer


class TestWorkflowValidator(unittest.TestCase):
    """测试工作流验证器"""
    
    def setUp(self):
        """设置测试环境"""
        self.validator = WorkflowValidator()
        self.renderer = WorkflowYamlRenderer()
        # 创建临时目录用于测试文件
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """清理测试环境"""
        self.temp_dir.cleanup()
    
    def test_basic_validation(self):
        """测试基本验证功能"""
        # 有效的YAML
        valid_yaml = """
name: 测试工作流
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: 检出代码
        uses: actions/checkout@v2
      - name: 运行测试
        run: echo "Running tests"
"""
        is_valid, errors = self.validator.validate(valid_yaml)
        self.assertTrue(is_valid, f"预期验证通过，但失败了: {errors}")
        
        # 无效的YAML（缺少必要字段）
        invalid_yaml = """
name: 测试工作流
on: push
# 缺少jobs字段
"""
        is_valid, errors = self.validator.validate(invalid_yaml)
        self.assertFalse(is_valid, "预期验证失败，但通过了")
        self.assertTrue(any("缺少必需的顶级键 'jobs'" in error for error in errors), 
                        f"未检测到预期的错误消息，实际错误: {errors}")
        
        # 无效的YAML（jobs不是对象）
        invalid_yaml = """
name: 测试工作流
on: push
jobs: "这不是一个对象"
"""
        is_valid, errors = self.validator.validate(invalid_yaml)
        self.assertFalse(is_valid, "预期验证失败，但通过了")
        self.assertTrue(any("'jobs' 必须是一个对象" in error for error in errors), 
                        f"未检测到预期的错误消息，实际错误: {errors}")
    
    def test_condition_expression_validation(self):
        """测试条件表达式验证"""
        # 测试未使用${{ }}包装的变量引用
        yaml_with_unwrapped_vars = """
name: 测试工作流
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: 条件步骤
        if: vars.ENABLE_TEST == 'true'
        run: echo "Test enabled"
"""
        is_valid, errors = self.validator.validate(yaml_with_unwrapped_vars)
        self.assertFalse(is_valid, "预期验证失败，但通过了")
        self.assertTrue(any("'vars.ENABLE_TEST' 引用应该使用" in error for error in errors), 
                        f"未检测到预期的错误消息，实际错误: {errors}")
        
        # 测试使用正确的${{ }}语法
        yaml_with_proper_vars = """
name: 测试工作流
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: 条件步骤
        if: ${{ vars.ENABLE_TEST == 'true' }}
        run: echo "Test enabled"
"""
        is_valid, errors = self.validator.validate(yaml_with_proper_vars)
        self.assertTrue(is_valid, f"预期验证通过，但失败了: {errors}")
        
        # 测试操作符周围缺少空格
        yaml_with_no_spaces = """
name: 测试工作流
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: 条件步骤
        if: ${{ vars.ENABLE_TEST=='true'&&env.DEBUG!='false' }}
        run: echo "Test enabled"
"""
        warnings = self.validator.check_for_common_formatting_issues(yaml_with_no_spaces)
        self.assertTrue(any("操作符两侧应该有空格" in warning for warning in warnings), 
                        f"未检测到预期的警告消息，实际警告: {warnings}")
    
    def test_environment_variable_validation(self):
        """测试环境变量验证"""
        # 测试未使用${{ }}包装的环境变量
        yaml_with_unwrapped_env_vars = """
name: 测试工作流
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      API_KEY: secrets.API_KEY
      DEBUG: vars.DEBUG_MODE
    steps:
      - name: 打印变量
        run: echo $API_KEY
"""
        is_valid, errors = self.validator.validate(yaml_with_unwrapped_env_vars)
        self.assertFalse(is_valid, "预期验证失败，但通过了")
        self.assertTrue(any("环境变量 'API_KEY' 的值应该使用 ${{ ... }} 语法" in error for error in errors), 
                        f"未检测到预期的错误消息，实际错误: {errors}")
        
        # 测试正确的环境变量语法
        yaml_with_proper_env_vars = """
name: 测试工作流
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      API_KEY: ${{ secrets.API_KEY }}
      DEBUG: ${{ vars.DEBUG_MODE }}
    steps:
      - name: 打印变量
        run: echo $API_KEY
"""
        is_valid, errors = self.validator.validate(yaml_with_proper_env_vars)
        self.assertTrue(is_valid, f"预期验证通过，但失败了: {errors}")
    
    def test_normalize_if_condition(self):
        """测试if条件表达式标准化"""
        # 测试各种条件表达式格式
        test_cases = [
            # 输入，预期输出
            ("vars.ENABLE_TEST == 'true'", "${{ vars.ENABLE_TEST == 'true' }}"),
            ("${{vars.DEBUG}}", "${{ vars.DEBUG }}"),
            ("${{ vars.A }}&&${{ vars.B }}", "${{ vars.A }} && ${{ vars.B }}"),
            ("steps.test.outputs.result=='success'", "${{ steps.test.outputs.result == 'success' }}"),
            ("github.event_name=='push'", "${{ github.event_name == 'push' }}"),
            ("${{ github.event.inputs.debug }}=='true'", "${{ github.event.inputs.debug == 'true' }}"),
        ]
        
        for input_condition, expected_output in test_cases:
            actual_output = self.renderer._normalize_if_condition(input_condition)
            self.assertEqual(expected_output, actual_output, 
                            f"条件标准化失败，输入: {input_condition}, 预期: {expected_output}, 实际: {actual_output}")
    
    def test_template_validation(self):
        """测试模板文件验证"""
        # 测试有效的模板
        valid_template = """
name: {{ workflow_name }}
on: {% raw %}${{ github.event_name }}{% endraw %}

jobs:
  test:
    runs-on: {{ runner_os }}
    steps:
      - name: 打印信息
        run: echo "{{ message }}"
        if: {% raw %}${{ vars.ENABLE_TEST == 'true' }}{% endraw %}
"""
        is_valid, errors = self.validator.validate_template(valid_template)
        self.assertTrue(is_valid, f"预期模板验证通过，但失败了: {errors}")
        
        # 测试无效的模板（缺少结束标记）
        invalid_template = """
name: {{ workflow_name
on: push

jobs:
  test:
    runs-on: {{ runner_os }}
    steps:
      - name: 打印信息
        run: echo "{{ message }}"
"""
        is_valid, errors = self.validator.validate_template(invalid_template)
        self.assertFalse(is_valid, "预期模板验证失败，但通过了")
        self.assertTrue(any("变量引用缺少结束标记" in error for error in errors), 
                        f"未检测到预期的错误消息，实际错误: {errors}")
        
        # 测试if/endif不匹配
        invalid_template = """
name: Test
on: push

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: 条件步骤
        run: |
          {% if condition %}
          echo "条件为真"
          {% if nested %}
          echo "嵌套条件"
          {% endif %}
"""
        is_valid, errors = self.validator.validate_template(invalid_template)
        self.assertFalse(is_valid, "预期模板验证失败，但通过了")
        self.assertTrue(any("if/endif 标签不匹配" in error for error in errors), 
                        f"未检测到预期的错误消息，实际错误: {errors}")
    
    def test_complex_validation_scenario(self):
        """测试复杂验证场景"""
        # 创建一个完整的工作流文件进行测试
        complex_workflow = """
name: 复杂工作流测试
run-name: "测试工作流 #${{ github.run_number }}"

# 多种触发方式
on:
  workflow_dispatch:
    inputs:
      date:
        description: '数据日期'
        required: false
        type: string
      debug:
        description: '调试模式'
        required: false
        default: false
        type: boolean
  
  schedule:
    - cron: "0 0 * * *"
  
  push:
    branches: [ main ]
    paths:
      - 'config/**'
      - 'src/**'

env:
  PYTHON_VERSION: "3.10"
  TZ: "Asia/Shanghai"
  RUN_DATE: ${{ github.event.inputs.date || '' }}
  USE_PROXY: ${{ vars.USE_PROXY || 'true' }}
  API_KEY: ${{ secrets.API_KEY }}

jobs:
  pre-check:
    name: 检查环境
    runs-on: ubuntu-latest
    outputs:
      run_date: ${{ steps.prepare_env.outputs.date }}
      cache_key: ${{ steps.prepare_env.outputs.cache_key }}
    
    steps:
      - name: 检出代码
        uses: actions/checkout@v4
      
      - name: 准备环境变量
        id: prepare_env
        run: |
          if [ -n "$RUN_DATE" ]; then
            echo "date=$RUN_DATE" >> $GITHUB_OUTPUT
          else
            echo "date=$(date +%Y-%m-%d)" >> $GITHUB_OUTPUT
          fi
          echo "cache_key=deps-test-$(date +%s)" >> $GITHUB_OUTPUT
      
      - name: 验证配置
        id: validate_config
        if: ${{ github.event_name == 'push' || github.event_name == 'workflow_dispatch' }}
        run: echo "valid=true" >> $GITHUB_OUTPUT

  main:
    name: 主任务
    needs: pre-check
    runs-on: ubuntu-latest
    if: ${{ needs.pre-check.outputs.run_date != '' && needs.pre-check.outputs.cache_key != '' }}
    env:
      RUN_DATE: ${{ needs.pre-check.outputs.run_date }}
    
    steps:
      - name: 检出代码
        uses: actions/checkout@v4
      
      - name: 运行命令
        id: run_command
        continue-on-error: true
        run: |
          echo "执行命令..."
          echo "status=success" >> $GITHUB_OUTPUT
      
      - name: 条件步骤
        if: ${{ steps.run_command.outputs.status == 'success' && env.USE_PROXY == 'true' }}
        run: echo "条件满足"
"""
        is_valid, errors = self.validator.validate(complex_workflow)
        self.assertTrue(is_valid, f"复杂工作流验证应该通过，但失败了: {errors}")
        
        # 检查格式问题
        warnings = self.validator.check_for_common_formatting_issues(complex_workflow)
        self.assertEqual(0, len(warnings), f"复杂工作流不应有格式问题，但发现: {warnings}")


if __name__ == '__main__':
    unittest.main() 