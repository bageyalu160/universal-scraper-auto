#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 渲染器测试
"""

import os
import unittest
from pathlib import Path
import tempfile
import yaml

from ..renderers.yaml_renderer import WorkflowYamlRenderer
from ..models.base import BaseWorkflowModel
from ..models.steps import Step, Job
from ..models.workflow import Workflow


class MockStep(BaseWorkflowModel):
    """模拟测试用的步骤类"""
    name: str
    run_command: str = None
    uses: str = None
    if_condition: str = None
    
    
class MockJob(BaseWorkflowModel):
    """模拟测试用的作业类"""
    name: str
    runs_on: str
    steps: list[MockStep]


class MockWorkflow(BaseWorkflowModel):
    """模拟测试用的工作流类"""
    name: str
    on: dict
    jobs: dict[str, MockJob]


class TestYamlRenderer(unittest.TestCase):
    """测试YAML渲染器"""
    
    def setUp(self):
        """设置测试环境"""
        self.renderer = WorkflowYamlRenderer()
        # 创建临时目录用于测试文件
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """清理测试环境"""
        self.temp_dir.cleanup()
    
    def test_normalize_if_condition(self):
        """测试if条件标准化"""
        test_cases = [
            # 输入, 预期输出
            ("vars.DEBUG == 'true'", "${{ vars.DEBUG == 'true' }}"),
            ("${{vars.DEBUG}}", "${{ vars.DEBUG }}"),
            ("steps.build.outputs.result=='success'", "${{ steps.build.outputs.result == 'success' }}"),
            ("github.event_name == 'push'", "${{ github.event_name == 'push' }}"),
            ("vars.ENABLE == 'true' && secrets.API_KEY != ''", "${{ vars.ENABLE == 'true' && secrets.API_KEY != '' }}"),
            ("steps.test.outcome=='failure'||steps.build.outcome=='failure'", 
             "${{ steps.test.outcome == 'failure' || steps.build.outcome == 'failure' }}"),
        ]
        
        for input_text, expected in test_cases:
            result = self.renderer._normalize_if_condition(input_text)
            self.assertEqual(expected, result, f"标准化失败: '{input_text}' -> '{result}' (预期 '{expected}')")
    
    def test_post_process_yaml(self):
        """测试YAML后处理"""
        yaml_with_issues = """
name: Test Workflow

on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v2
      
      - name: Run if condition
        if: "steps.previous.outputs.result == 'success'"
        run: echo "Step executed"
      
      - name: Another condition
        if: vars.ENABLE_FEATURE == 'true' && secrets.API_KEY != ''
        run: echo "Another step"
"""
        
        processed = self.renderer._post_process_yaml(yaml_with_issues)
        
        # 检查引号被移除
        self.assertNotIn('if: "steps.previous.outputs.result', processed)
        
        # 检查变量引用被正确包装
        self.assertIn('if: ${{ vars.ENABLE_FEATURE', processed)
        
    def test_render_workflow_model(self):
        """测试渲染工作流模型"""
        # 创建测试工作流
        workflow = MockWorkflow(
            name="测试工作流",
            on={"push": {"branches": ["main"]}},
            jobs={
                "test": MockJob(
                    name="测试作业",
                    runs_on="ubuntu-latest",
                    steps=[
                        MockStep(
                            name="检出代码",
                            uses="actions/checkout@v2"
                        ),
                        MockStep(
                            name="条件步骤",
                            run_command="echo 'Hello World'",
                            if_condition="vars.DEBUG == 'true'"
                        )
                    ]
                )
            }
        )
        
        # 渲染为YAML
        yaml_str = self.renderer.render_to_string(workflow)
        
        # 检查字段名称转换
        self.assertIn("runs-on:", yaml_str)
        self.assertNotIn("runs_on:", yaml_str)
        
        self.assertIn("if:", yaml_str)
        self.assertNotIn("if_condition:", yaml_str)
        
        self.assertIn("run:", yaml_str)
        self.assertNotIn("run_command:", yaml_str)
        
        # 检查条件表达式标准化
        self.assertIn("if: ${{ vars.DEBUG == 'true' }}", yaml_str)
        
        # 渲染到文件
        output_path = self.temp_path / "test_workflow.yml"
        self.renderer.render_to_file(workflow, output_path)
        
        # 验证文件存在
        self.assertTrue(output_path.exists())
        
        # 验证文件内容
        with open(output_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        self.assertEqual(yaml_str, file_content)
    
    def test_multiline_run_command(self):
        """测试多行运行命令渲染"""
        workflow = MockWorkflow(
            name="多行命令测试",
            on={"push": {}},
            jobs={
                "test": MockJob(
                    name="测试作业",
                    runs_on="ubuntu-latest",
                    steps=[
                        MockStep(
                            name="多行命令",
                            run_command="""
echo "第一行"
echo "第二行"
echo "第三行"
"""
                        )
                    ]
                )
            }
        )
        
        yaml_str = self.renderer.render_to_string(workflow)
        
        # 检查多行命令使用折叠块样式 (|)
        self.assertIn("run: |", yaml_str)
    
    def test_complex_workflow_rendering(self):
        """测试复杂工作流渲染"""
        # 创建更复杂的工作流
        workflow = MockWorkflow(
            name="复杂工作流测试",
            on={
                "workflow_dispatch": {
                    "inputs": {
                        "debug": {
                            "description": "启用调试模式",
                            "required": False,
                            "type": "boolean",
                            "default": False
                        }
                    }
                },
                "schedule": [{"cron": "0 0 * * *"}]
            },
            jobs={
                "build": MockJob(
                    name="构建",
                    runs_on="ubuntu-latest",
                    steps=[
                        MockStep(
                            name="检出代码",
                            uses="actions/checkout@v2"
                        ),
                        MockStep(
                            name="设置环境",
                            run_command="""
echo "设置环境变量"
export PYTHONPATH=$PWD
"""
                        )
                    ]
                ),
                "test": MockJob(
                    name="测试",
                    runs_on="ubuntu-latest",
                    steps=[
                        MockStep(
                            name="检出代码",
                            uses="actions/checkout@v2"
                        ),
                        MockStep(
                            name="运行测试",
                            run_command="python -m unittest discover",
                            if_condition="github.event_name == 'push' || github.event.inputs.debug == 'true'"
                        )
                    ]
                )
            }
        )
        
        yaml_str = self.renderer.render_to_string(workflow)
        
        # 验证结果
        parsed = yaml.safe_load(yaml_str)
        
        # 确认重要字段
        self.assertEqual("复杂工作流测试", parsed["name"])
        self.assertEqual(2, len(parsed["jobs"]))
        self.assertIn("workflow_dispatch", parsed["on"])
        self.assertIn("schedule", parsed["on"])
        
        # 检查条件表达式
        test_job = parsed["jobs"]["test"]
        run_test_step = test_job["steps"][1]
        self.assertIn("${{", run_test_step["if"])


if __name__ == '__main__':
    unittest.main() 