#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 工作流验证器
"""

import re
from typing import Dict, Any, List, Tuple
import ruamel.yaml


class WorkflowValidator:
    """验证工作流YAML格式是否有效"""
    
    def __init__(self):
        """初始化验证器"""
        self.yaml = ruamel.yaml.YAML(typ='safe')
    
    def validate(self, yaml_content: str) -> Tuple[bool, List[str]]:
        """
        验证YAML内容
        
        Args:
            yaml_content: YAML字符串
            
        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []
        
        # 检查YAML是否可以解析
        try:
            workflow_dict = self.yaml.load(yaml_content)
        except Exception as e:
            errors.append(f"YAML解析错误: {str(e)}")
            return False, errors
        
        # 检查必需的顶级键
        required_keys = ['name', 'on', 'jobs']
        for key in required_keys:
            if key not in workflow_dict:
                errors.append(f"缺少必需的顶级键 '{key}'")
        
        # 如果缺少必需的键，直接返回
        if errors:
            return False, errors
        
        # 检查jobs
        if not isinstance(workflow_dict['jobs'], dict):
            errors.append("'jobs' 必须是一个对象")
        else:
            for job_id, job in workflow_dict['jobs'].items():
                job_errors = self._validate_job(job_id, job)
                errors.extend(job_errors)
        
        # 检查触发器
        triggers = workflow_dict['on']
        if isinstance(triggers, dict):
            # 可以进一步验证各种触发器
            pass
        elif isinstance(triggers, list):
            # 如果是列表，通常是单一事件的列表
            pass
        else:
            errors.append("'on' 必须是一个对象或字符串")
        
        return len(errors) == 0, errors
    
    def _validate_job(self, job_id: str, job: Dict[str, Any]) -> List[str]:
        """验证作业配置"""
        errors = []
        
        # 检查必需的作业键
        # 转换 runs_on 和 runs-on
        if 'runs-on' not in job and 'runs_on' in job:
            job['runs-on'] = job['runs_on']
        
        if 'runs-on' not in job:
            errors.append(f"作业 '{job_id}' 缺少必需的 'runs-on' 字段")
        
        if 'steps' not in job:
            errors.append(f"作业 '{job_id}' 缺少必需的 'steps' 字段")
        else:
            if not isinstance(job['steps'], list):
                errors.append(f"作业 '{job_id}' 的 'steps' 必须是一个数组")
            else:
                for i, step in enumerate(job['steps']):
                    step_errors = self._validate_step(job_id, i, step)
                    errors.extend(step_errors)
        
        return errors
    
    def _validate_step(self, job_id: str, step_index: int, step: Dict[str, Any]) -> List[str]:
        """验证步骤配置"""
        errors = []
        step_name = step.get('name', f'#{step_index}')
        
        # 检查步骤是否有名称
        if 'name' not in step:
            errors.append(f"作业 '{job_id}' 的步骤 #{step_index} 缺少必需的 'name' 字段")
        
        # 规范化 run_command 为 run
        if 'run_command' in step and 'run' not in step:
            step['run'] = step['run_command']
        
        # 规范化 with_params 为 with
        if 'with_params' in step and 'with' not in step:
            step['with'] = step['with_params']
            
        # 规范化 if_condition 为 if
        if 'if_condition' in step and 'if' not in step:
            step['if'] = step['if_condition']
            
        # 规范化 continue_on_error 为 continue-on-error
        if 'continue_on_error' in step and 'continue-on-error' not in step:
            step['continue-on-error'] = step['continue_on_error']
        
        # 检查步骤是否有有效的操作（run或uses）
        if 'run' not in step and 'uses' not in step:
            errors.append(f"作业 '{job_id}' 的步骤 '{step_name}' 必须包含 'run' 或 'uses' 字段")
        
        # 检查 run 字段是否为空
        if 'run' in step and (not isinstance(step['run'], str) or not step['run'].strip()):
            errors.append(f"作业 '{job_id}' 的步骤 '{step_name}' 的 'run' 字段不能为空")
        
        # 检查 uses 字段是否为空
        if 'uses' in step and (not isinstance(step['uses'], str) or not step['uses'].strip()):
            errors.append(f"作业 '{job_id}' 的步骤 '{step_name}' 的 'uses' 字段不能为空")
        
        # 如果步骤有with参数，则检查是否是一个对象
        if 'with' in step and not isinstance(step['with'], dict):
            errors.append(f"作业 '{job_id}' 的步骤 '{step_name}' 的 'with' 必须是一个对象")
        
        return errors
    
    def check_for_common_formatting_issues(self, yaml_content: str) -> List[str]:
        """检查常见的格式问题"""
        warnings = []
        
        # 检查环境变量是否在同一行
        env_var_pattern = r'([A-Z_]+: \$\{\{ [a-z\.]+\.[A-Z_]+ (?:\|\| \'[^\']*\')? \}\})[ ]+([A-Z_]+:)'
        if re.search(env_var_pattern, yaml_content):
            warnings.append("环境变量定义可能在同一行，应该每个变量占一行")
        
        # 检查run块中的缩进
        run_blocks = re.findall(r'run: \|\n((?:[ ]+.*\n)+)', yaml_content)
        for block in run_blocks:
            lines = block.split('\n')
            indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
            if indents and (min(indents) < 8 or max(indents) > 12):
                warnings.append("run块中的命令可能缩进不一致")
        
        # 检查if条件和其他标记混在一起
        if_mixed_pattern = r'if: [^\n]+[ ]+(run:|uses:|env:)'
        if re.search(if_mixed_pattern, yaml_content):
            warnings.append("if条件和其他标记可能在同一行")
        
        # 检查步骤8通知格式问题
        notification_pattern = r'# 步骤8: 发送通知\n[ ]+- name: 发送通知\n[ ]+if: [^\n]+\n[ ]+env:run:'
        if re.search(notification_pattern, yaml_content):
            warnings.append("步骤8发送通知的格式可能有误（env:run:）")
            
        # 检查 continue_on_error 格式
        continue_error_pattern = r'continue_on_error:'
        if re.search(continue_error_pattern, yaml_content):
            warnings.append("使用了错误的格式 'continue_on_error'，应使用 'continue-on-error'")
        
        return warnings 