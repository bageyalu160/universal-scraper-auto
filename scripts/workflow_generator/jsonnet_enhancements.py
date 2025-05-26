#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jsonnet引擎增强模块
为支持YAML模板完整功能而设计的扩展
"""

import json
import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path


class JsonnetEnhancements:
    """Jsonnet引擎增强功能类"""
    
    def __init__(self):
        self.github_actions_features = self._init_github_actions_features()
        self.script_processors = self._init_script_processors()
        self.condition_handlers = self._init_condition_handlers()
    
    def _init_github_actions_features(self) -> Dict[str, Any]:
        """初始化GitHub Actions特性支持"""
        return {
            'trigger_types': [
                'workflow_dispatch',
                'repository_dispatch', 
                'workflow_call',
                'push',
                'pull_request',
                'schedule'
            ],
            'job_features': [
                'needs',
                'if',
                'timeout-minutes',
                'continue-on-error',
                'outputs',
                'strategy',
                'container',
                'services'
            ],
            'step_features': [
                'if',
                'continue-on-error',
                'timeout-minutes',
                'uses',
                'run',
                'with',
                'env'
            ],
            'workflow_features': [
                'concurrency',
                'permissions',
                'defaults',
                'env'
            ]
        }
    
    def _init_script_processors(self) -> Dict[str, callable]:
        """初始化脚本处理器"""
        return {
            'bash': self._process_bash_script,
            'powershell': self._process_powershell_script,
            'python': self._process_python_script,
            'javascript': self._process_javascript_script
        }
    
    def _init_condition_handlers(self) -> Dict[str, callable]:
        """初始化条件处理器"""
        return {
            'github_context': self._handle_github_context,
            'env_vars': self._handle_env_vars,
            'secrets': self._handle_secrets,
            'vars': self._handle_vars,
            'steps': self._handle_steps,
            'needs': self._handle_needs,
            'functions': self._handle_functions
        }
    
    def enhance_workflow_object(self, workflow_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强工作流对象，添加YAML模板功能支持
        
        Args:
            workflow_obj: 原始工作流对象
            
        Returns:
            增强后的工作流对象
        """
        enhanced_obj = workflow_obj.copy()
        
        # 处理触发条件
        if 'on' in enhanced_obj:
            enhanced_obj['on'] = self._enhance_triggers(enhanced_obj['on'])
        
        # 处理并发控制
        if 'concurrency' in enhanced_obj:
            enhanced_obj['concurrency'] = self._enhance_concurrency(enhanced_obj['concurrency'])
        
        # 处理作业
        if 'jobs' in enhanced_obj:
            enhanced_obj['jobs'] = self._enhance_jobs(enhanced_obj['jobs'])
        
        return enhanced_obj
    
    def _enhance_triggers(self, triggers: Dict[str, Any]) -> Dict[str, Any]:
        """增强触发条件"""
        enhanced_triggers = triggers.copy()
        
        # 处理workflow_dispatch输入
        if 'workflow_dispatch' in enhanced_triggers:
            wd = enhanced_triggers['workflow_dispatch']
            if 'inputs' in wd:
                wd['inputs'] = self._process_workflow_inputs(wd['inputs'])
        
        # 处理workflow_call
        if 'workflow_call' in enhanced_triggers:
            wc = enhanced_triggers['workflow_call']
            if 'inputs' in wc:
                wc['inputs'] = self._process_workflow_inputs(wc['inputs'])
            if 'secrets' in wc:
                wc['secrets'] = self._process_workflow_secrets(wc['secrets'])
        
        return enhanced_triggers
    
    def _enhance_concurrency(self, concurrency: Dict[str, Any]) -> Dict[str, Any]:
        """增强并发控制"""
        enhanced_concurrency = concurrency.copy()
        
        # 处理组名中的表达式
        if 'group' in enhanced_concurrency:
            enhanced_concurrency['group'] = self._process_github_expressions(
                enhanced_concurrency['group']
            )
        
        return enhanced_concurrency
    
    def _enhance_jobs(self, jobs: Dict[str, Any]) -> Dict[str, Any]:
        """增强作业定义"""
        enhanced_jobs = {}
        
        for job_id, job_def in jobs.items():
            enhanced_jobs[job_id] = self._enhance_single_job(job_def)
        
        return enhanced_jobs
    
    def _enhance_single_job(self, job_def: Dict[str, Any]) -> Dict[str, Any]:
        """增强单个作业定义"""
        enhanced_job = job_def.copy()
        
        # 处理条件表达式
        if 'if' in enhanced_job:
            enhanced_job['if'] = self._process_condition_expression(enhanced_job['if'])
        
        # 处理环境变量
        if 'env' in enhanced_job:
            enhanced_job['env'] = self._process_env_vars(enhanced_job['env'])
        
        # 处理步骤
        if 'steps' in enhanced_job:
            enhanced_job['steps'] = self._enhance_steps(enhanced_job['steps'])
        
        # 处理输出
        if 'outputs' in enhanced_job:
            enhanced_job['outputs'] = self._process_job_outputs(enhanced_job['outputs'])
        
        return enhanced_job
    
    def _enhance_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """增强步骤定义"""
        enhanced_steps = []
        
        for step in steps:
            enhanced_step = step.copy()
            
            # 处理条件表达式
            if 'if' in enhanced_step:
                enhanced_step['if'] = self._process_condition_expression(enhanced_step['if'])
            
            # 处理运行脚本
            if 'run' in enhanced_step:
                enhanced_step['run'] = self._process_run_script(enhanced_step['run'])
            
            # 处理环境变量
            if 'env' in enhanced_step:
                enhanced_step['env'] = self._process_env_vars(enhanced_step['env'])
            
            enhanced_steps.append(enhanced_step)
        
        return enhanced_steps
    
    def _process_workflow_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流输入"""
        processed_inputs = {}
        
        for input_name, input_def in inputs.items():
            processed_input = input_def.copy()
            
            # 处理选择类型的选项
            if input_def.get('type') == 'choice' and 'options' in input_def:
                processed_input['options'] = input_def['options']
            
            processed_inputs[input_name] = processed_input
        
        return processed_inputs
    
    def _process_workflow_secrets(self, secrets: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流密钥"""
        return secrets  # 密钥定义通常不需要特殊处理
    
    def _process_github_expressions(self, expression: str) -> str:
        """处理GitHub表达式"""
        # 保持GitHub表达式的原始格式
        return expression
    
    def _process_condition_expression(self, condition: str) -> str:
        """处理条件表达式"""
        # GitHub Actions条件表达式处理
        return condition
    
    def _process_env_vars(self, env_vars: Dict[str, Any]) -> Dict[str, Any]:
        """处理环境变量"""
        processed_env = {}
        
        for key, value in env_vars.items():
            if isinstance(value, str):
                # 处理GitHub表达式
                processed_env[key] = self._process_github_expressions(value)
            else:
                processed_env[key] = value
        
        return processed_env
    
    def _process_run_script(self, script: str) -> str:
        """处理运行脚本"""
        # 处理多行脚本
        if '\n' in script:
            return self._process_multiline_script(script)
        else:
            return self._process_single_line_script(script)
    
    def _process_multiline_script(self, script: str) -> str:
        """处理多行脚本"""
        lines = script.split('\n')
        processed_lines = []
        
        for line in lines:
            # 处理GitHub表达式
            processed_line = self._process_github_expressions(line.strip())
            if processed_line:  # 跳过空行
                processed_lines.append(processed_line)
        
        return '\n'.join(processed_lines)
    
    def _process_single_line_script(self, script: str) -> str:
        """处理单行脚本"""
        return self._process_github_expressions(script.strip())
    
    def _process_job_outputs(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """处理作业输出"""
        processed_outputs = {}
        
        for output_name, output_value in outputs.items():
            if isinstance(output_value, str):
                processed_outputs[output_name] = self._process_github_expressions(output_value)
            else:
                processed_outputs[output_name] = output_value
        
        return processed_outputs
    
    def _process_bash_script(self, script: str) -> str:
        """处理Bash脚本"""
        # Bash脚本特定处理
        return script
    
    def _process_powershell_script(self, script: str) -> str:
        """处理PowerShell脚本"""
        # PowerShell脚本特定处理
        return script
    
    def _process_python_script(self, script: str) -> str:
        """处理Python脚本"""
        # Python脚本特定处理
        return script
    
    def _process_javascript_script(self, script: str) -> str:
        """处理JavaScript脚本"""
        # JavaScript脚本特定处理
        return script
    
    def _handle_github_context(self, context: str) -> str:
        """处理GitHub上下文"""
        return context
    
    def _handle_env_vars(self, env_var: str) -> str:
        """处理环境变量"""
        return env_var
    
    def _handle_secrets(self, secret: str) -> str:
        """处理密钥"""
        return secret
    
    def _handle_vars(self, var: str) -> str:
        """处理变量"""
        return var
    
    def _handle_steps(self, step_ref: str) -> str:
        """处理步骤引用"""
        return step_ref
    
    def _handle_needs(self, needs_ref: str) -> str:
        """处理依赖引用"""
        return needs_ref
    
    def _handle_functions(self, function: str) -> str:
        """处理函数"""
        return function
    
    def validate_workflow_syntax(self, workflow_obj: Dict[str, Any]) -> List[str]:
        """
        验证工作流语法
        
        Args:
            workflow_obj: 工作流对象
            
        Returns:
            验证错误列表
        """
        errors = []
        
        # 验证必需字段
        if 'name' not in workflow_obj:
            errors.append("工作流缺少必需的 'name' 字段")
        
        if 'on' not in workflow_obj:
            errors.append("工作流缺少必需的 'on' 字段")
        
        if 'jobs' not in workflow_obj:
            errors.append("工作流缺少必需的 'jobs' 字段")
        
        # 验证作业
        if 'jobs' in workflow_obj:
            for job_id, job_def in workflow_obj['jobs'].items():
                job_errors = self._validate_job(job_id, job_def)
                errors.extend(job_errors)
        
        return errors
    
    def _validate_job(self, job_id: str, job_def: Dict[str, Any]) -> List[str]:
        """验证单个作业"""
        errors = []
        
        # 验证runs-on
        if 'runs-on' not in job_def:
            errors.append(f"作业 '{job_id}' 缺少必需的 'runs-on' 字段")
        
        # 验证steps
        if 'steps' not in job_def:
            errors.append(f"作业 '{job_id}' 缺少必需的 'steps' 字段")
        elif not isinstance(job_def['steps'], list):
            errors.append(f"作业 '{job_id}' 的 'steps' 必须是数组")
        
        return errors


class JsonnetTemplateBuilder:
    """Jsonnet模板构建器"""
    
    def __init__(self):
        self.enhancements = JsonnetEnhancements()
    
    def build_analyzer_template(self, site_config: Dict[str, Any], 
                              global_config: Dict[str, Any]) -> str:
        """
        构建分析器Jsonnet模板
        
        Args:
            site_config: 站点配置
            global_config: 全局配置
            
        Returns:
            Jsonnet模板内容
        """
        template_parts = [
            self._build_template_header(),
            self._build_parameter_definitions(),
            self._build_workflow_definition(site_config, global_config),
        ]
        
        return '\n\n'.join(template_parts)
    
    def _build_template_header(self) -> str:
        """构建模板头部"""
        return '''// 增强版分析工作流模板 - 完整功能对标 analyzer.yml.template
// 由JsonnetTemplateBuilder自动生成

local params = import 'params.libsonnet';
local utils = import 'utils.libsonnet';'''
    
    def _build_parameter_definitions(self) -> str:
        """构建参数定义"""
        return '''// 外部参数
local site_id = std.extVar('site_id');
local site_config = std.parseJson(std.extVar('site_config'));
local global_config = std.parseJson(std.extVar('global_config'));

// 动态参数计算
local site_name = utils.getSiteName(site_config, site_id);
local analysis_config = utils.getAnalysisConfig(site_config);
local output_extension = utils.getOutputExtension(analysis_config);
local env_vars = utils.getEnvironmentVariables(analysis_config, global_config);'''
    
    def _build_workflow_definition(self, site_config: Dict[str, Any], 
                                  global_config: Dict[str, Any]) -> str:
        """构建工作流定义"""
        return '''{
  // 工作流基本信息
  name: site_name + ' AI分析任务',
  'run-name': '🧠 ' + site_name + '分析 #${{ github.run_number }} (${{ github.actor }} 触发)',
  
  // 复杂触发条件
  on: utils.buildTriggers(),
  
  // 全局设置
  env: utils.buildGlobalEnv(site_id, analysis_dir),
  permissions: utils.buildPermissions(),
  defaults: utils.buildDefaults(),
  concurrency: utils.buildConcurrency(site_id),
  
  // 多作业工作流
  jobs: utils.buildAnalyzerJobs(site_config, global_config)
}''' 