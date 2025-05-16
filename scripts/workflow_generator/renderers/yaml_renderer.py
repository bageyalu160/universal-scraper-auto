#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - YAML渲染器
"""

import io
from pathlib import Path
from typing import Dict, Any, Union

import ruamel.yaml
from ruamel.yaml.scalarstring import LiteralScalarString

from ..models import Workflow


class WorkflowYamlRenderer:
    """将工作流模型渲染为YAML格式"""
    
    def __init__(self):
        """初始化渲染器"""
        self.yaml = ruamel.yaml.YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 88  # 行宽限制
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        
        # 特殊设置，用于改进块字符串的格式
        self.yaml.default_flow_style = False  # 使用块样式而非流样式
    
    def render(self, workflow: Workflow) -> Dict[str, Any]:
        """将工作流模型渲染为字典"""
        workflow_dict = workflow.to_dict()
        
        # 处理字典中的所有对象，确保字段名称正确
        return self._process_dict(workflow_dict)
    
    def _process_dict(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """递归处理字典，转换字段名"""
        result = {}
        
        for key, value in input_dict.items():
            # 转换字段名
            if key == "run_command":
                new_key = "run"
            elif key == "with_params":
                new_key = "with"
            elif key == "if_condition":
                new_key = "if"
            elif key == "runs_on":
                new_key = "runs-on"
            elif key == "continue_on_error":
                new_key = "continue-on-error"
            else:
                new_key = key
            
            # 递归处理嵌套数据结构
            if isinstance(value, dict):
                result[new_key] = self._process_dict(value)
            elif isinstance(value, list):
                result[new_key] = [
                    self._process_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # 处理多行字符串
                if new_key == "run" and isinstance(value, str) and "\n" in value:
                    result[new_key] = LiteralScalarString(value)
                else:
                    result[new_key] = value
                
        return result
    
    def render_to_string(self, workflow: Workflow) -> str:
        """将工作流模型渲染为YAML字符串"""
        workflow_dict = self.render(workflow)
        
        # 使用StringIO捕获YAML输出
        string_stream = io.StringIO()
        self.yaml.dump(workflow_dict, string_stream)
        
        return string_stream.getvalue()
    
    def render_to_file(self, workflow: Workflow, output_path: Union[str, Path]) -> None:
        """将工作流模型渲染为YAML文件"""
        yaml_content = self.render_to_string(workflow)
        
        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content) 