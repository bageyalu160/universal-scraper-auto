#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - YAML渲染器
"""

import io
import re
import logging
from pathlib import Path
from typing import Dict, Any, Union, Optional

import ruamel.yaml
from ruamel.yaml.scalarstring import LiteralScalarString, FoldedScalarString, SingleQuotedScalarString
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..models import Workflow


class WorkflowYamlRenderer:
    """
    将工作流模型渲染为YAML格式，使用ruamel.yaml的高级功能
    """
    
    def __init__(self, logger=None):
        """
        初始化渲染器
        
        Args:
            logger: 可选的日志记录器
        """
        # 设置日志记录器
        self.logger = logger or logging.getLogger('workflow_yaml_renderer')
        
        # 初始化YAML解析器，保留注释和格式
        self.yaml = ruamel.yaml.YAML()
        self.yaml.preserve_quotes = True  # 保留引号
        self.yaml.width = 88  # 行宽限制
        self.yaml.indent(mapping=2, sequence=4, offset=2)  # 设置缩进
        self.yaml.default_flow_style = False  # 使用块样式而非流样式
        self.yaml.allow_duplicate_keys = False  # 不允许重复键
        # 配置引号处理
        self.yaml.emitter.open_ended = False  # 避免环境变量值中的引号被转义
        self.yaml.representer.default_scalar_style = None  # 使用最合适的标量样式
    
    def render(self, workflow: Workflow) -> Dict[str, Any]:
        """
        将工作流模型渲染为字典
        
        Args:
            workflow: 工作流模型对象
            
        Returns:
            包含工作流配置的字典
        """
        # 将模型转换为字典
        workflow_dict = workflow.to_dict()
        
        # 处理字典中的特殊格式
        return self._process_dict(workflow_dict)
    
    def _process_dict(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归处理字典，转换字段名并应用特殊格式
        
        Args:
            input_dict: 输入字典
            
        Returns:
            处理后的字典
        """
        # 使用CommentedMap以便保留注释和顺序
        result = CommentedMap()
        
        # 字段名转换映射
        field_mapping = {
            "run_command": "run",
            "with_params": "with",
            "if_condition": "if",
            "runs_on": "runs-on",
            "continue_on_error": "continue-on-error",
            "working_directory": "working-directory"
        }
        
        for key, value in input_dict.items():
            # 转换字段名
            new_key = field_mapping.get(key, key)
            
            # 递归处理嵌套数据结构
            if isinstance(value, dict):
                result[new_key] = self._process_dict(value)
            elif isinstance(value, list):
                # 使用CommentedSeq处理列表
                new_value = CommentedSeq([
                    self._process_dict(item) if isinstance(item, dict) else 
                    self._process_value(item, new_key)
                    for item in value
                ])
                result[new_key] = new_value
            else:
                # 处理标量值
                result[new_key] = self._process_value(value, new_key)
                
        return result
    
    def _process_value(self, value: Any, key: str) -> Any:
        """
        处理标量值，应用特殊格式
        
        Args:
            value: 输入值
            key: 字段名
            
        Returns:
            处理后的值
        """
        if value is None:
            return None
            
        # 处理特定类型的字段
        if key == "run" and isinstance(value, str) and "\n" in value:
            # 多行run命令使用竖线块样式
            return LiteralScalarString(value)
        elif key == "if" and isinstance(value, str):
            # 标准化条件表达式
            return self._normalize_if_condition(value)
        elif isinstance(value, str) and value.startswith("${{") and "||" in value:
            # 处理包含默认值的GitHub Actions表达式（如 ${{ vars.X || 'default' }}）
            # 这种情况不应使用额外的单引号包装，直接返回原始值
            return value
        elif isinstance(value, str) and ("\n" in value):
            # 其他多行字符串使用折叠块样式
            return FoldedScalarString(value)
        elif isinstance(value, str) and any(char in value for char in ":{}\n[],$&*#?|>%@!"):
            # 包含特殊字符的字符串使用单引号
            return SingleQuotedScalarString(value)
        else:
            return value
    
    def _normalize_if_condition(self, condition: str) -> str:
        """
        标准化条件表达式
        
        Args:
            condition: 条件表达式
            
        Returns:
            标准化后的条件表达式
        """
        # 跳过空条件或已包含Jinja2模板的条件
        if not condition or '{{' in condition:
            return condition
            
        # 移除条件两端可能存在的引号
        condition = condition.strip('"\'')
        
        # 是否已经被${{ }}包装
        is_wrapped = condition.startswith('${{') and condition.endswith('}}')
        
        # 如果尚未包装，并且条件中包含变量引用，则进行标准化
        if not is_wrapped:
            # 检查是否包含变量引用
            has_var_ref = re.search(r'\b(?:vars|env|secrets|github|steps|needs|inputs)\.[A-Za-z0-9_\.]+\b', condition)
            if has_var_ref:
                # 标准化操作符周围的空格
                condition = self._normalize_operators(condition)
                # 包装整个表达式
                return f'${{ {condition} }}'
            
        # 如果已经被包装，则确保内部格式正确    
        elif is_wrapped:
            # 提取内部表达式
            inner_expr = condition[3:-2].strip()
            # 标准化操作符
            normalized_inner = self._normalize_operators(inner_expr)
            # 重新包装
            if inner_expr != normalized_inner:
                return f'${{ {normalized_inner} }}'
                
        return condition
    
    def _normalize_operators(self, expr: str) -> str:
        """
        标准化表达式中的操作符，确保操作符周围有空格
        
        Args:
            expr: 表达式
            
        Returns:
            标准化后的表达式
        """
        # 确保比较操作符两侧有空格
        expr = re.sub(r'([=!<>])([=<>])', r'\1 \2', expr)
        expr = re.sub(r'([^=!<> ])([=!<>]{1,2})([^=!<> ])', r'\1 \2 \3', expr)
        
        # 确保逻辑操作符两侧有空格
        expr = re.sub(r'([^ ])(\&\&|\|\|)([^ ])', r'\1 \2 \3', expr)
        
        return expr
    
    def render_to_string(self, workflow: Workflow) -> str:
        """
        将工作流模型渲染为YAML字符串
        
        Args:
            workflow: 工作流模型对象
            
        Returns:
            YAML格式的字符串
        """
        workflow_dict = self.render(workflow)
        
        # 使用StringIO捕获YAML输出
        string_stream = io.StringIO()
        self.yaml.dump(workflow_dict, string_stream)
        
        yaml_content = string_stream.getvalue()
        
        # 对生成的YAML内容进行后处理
        yaml_content = self._post_process_yaml(yaml_content)
        
        return yaml_content
    
    def _post_process_yaml(self, yaml_content: str) -> str:
        """
        对生成的YAML内容进行后处理，修复可能的格式问题
        
        Args:
            yaml_content: YAML内容
            
        Returns:
            后处理的YAML内容
        """
        # 修复带引号的if条件（移除多余的引号）
        yaml_content = re.sub(r'if:\s*"([^"]+)"', r'if: \1', yaml_content)
        
        # 修复通知步骤中的条件表达式
        notification_pattern = r"if:\s*vars\.(ENABLE_NOTIFICATION.*?secrets\.[A-Z_]+\s*!=\s*'')"
        yaml_content = re.sub(notification_pattern, r"if: ${{ vars.\1 }}", yaml_content)
        
        # 修复备用操作的条件表达式
        yaml_content = re.sub(
            r'if:\s*"\(\$\{\{\s*(steps\.run_manager\.outputs\.success.*?outputs\.fallback\s*!=\s*\'\')\s*\}\}\)"',
            r'if: "(${{ \1 }})"',
            yaml_content
        )
        
        # 直接替换环境变量中的双引号问题 
        # 处理 ''false'' -> 'false'
        yaml_content = yaml_content.replace("''false''", "'false'")
        # 处理 ''none'' -> 'none'
        yaml_content = yaml_content.replace("''none''", "'none'")
        # 处理空字符串
        yaml_content = yaml_content.replace("''''", "''")
        
        # 修复环境变量中的 || 'value' 默认值引号问题
        yaml_content = re.sub(
            r'(\$\{\{\s*(?:vars|env|secrets|github)\.[A-Za-z0-9_\.]+\s*\|\|\s*)\'\'([a-zA-Z0-9_-]+)\'\'(\s*\}\})',
            r'\1\'\2\'\3',
            yaml_content
        )
        
        # 确保环境变量引用使用正确的语法
        def fix_env_vars(match):
            var_name = match.group(1)
            var_value = match.group(2).strip()
            
            # 检查是否包含变量引用但没有正确包装
            if re.search(r'\b(?:vars|env|secrets|github|steps|needs|inputs)\.[A-Za-z0-9_\.]+\b', var_value):
                if not (var_value.startswith('${{') or '${{' in var_value):
                    return f"{var_name}: ${{ {var_value} }}"
            
            return match.group(0)
        
        yaml_content = re.sub(r'([ ]*[A-Z_]+):\s*([^\n]+)', fix_env_vars, yaml_content)
        
        return yaml_content
    
    def render_to_file(self, workflow: Workflow, output_path: Union[str, Path]) -> None:
        """
        将工作流模型渲染为YAML文件
        
        Args:
            workflow: 工作流模型对象
            output_path: 输出文件路径
        """
        yaml_content = self.render_to_string(workflow)
        
        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
    
    def load_yaml(self, yaml_string: str) -> Dict[str, Any]:
        """
        将YAML字符串加载为字典
        
        Args:
            yaml_string: YAML字符串
            
        Returns:
            解析后的字典
        """
        try:
            return self.yaml.load(yaml_string) or {}
        except Exception as e:
            self.logger.error(f"解析YAML失败: {e}")
            return {}
    
    def dump_yaml(self, data: Dict[str, Any]) -> str:
        """
        将字典转换为YAML字符串
        
        Args:
            data: 要转换的字典
            
        Returns:
            YAML字符串
        """
        string_stream = io.StringIO()
        self.yaml.dump(data, string_stream)
        return string_stream.getvalue() 