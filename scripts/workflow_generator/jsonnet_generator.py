#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - Jsonnet版本
"""

import os
import sys
import json
import logging
import _jsonnet
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString, PlainScalarString
import re

from .validators import WorkflowValidator


class JsonnetWorkflowGenerator:
    """基于Jsonnet的工作流生成器类，用于生成GitHub Actions工作流文件"""
    
    def __init__(self, settings_path=None, sites_dir=None, output_dir=None, logger=None, validate_output=False):
        """
        初始化工作流生成器
        
        Args:
            settings_path (str, optional): 设置文件路径
            sites_dir (str, optional): 站点配置目录
            output_dir (str, optional): 输出目录
            logger (logging.Logger, optional): 日志记录器
            validate_output (bool, optional): 是否验证生成的工作流文件
        """
        # 设置日志记录器
        self.logger = logger or logging.getLogger('jsonnet_workflow_generator')
        
        # 设置路径
        self.base_dir = Path(__file__).parent.parent.parent
        self.settings_path = settings_path or self.base_dir / "config" / "settings.yaml"
        self.sites_dir = sites_dir or self.base_dir / "config" / "sites"
        self.output_dir = output_dir or self.base_dir / ".github" / "workflows"
        self.templates_dir = self.base_dir / "config" / "workflow" / "templates"
        
        # 加载设置
        self.settings = self._load_settings()
        
        # 提取全局配置
        self.global_config = self._extract_global_config()
        
        # 创建输出目录（如果不存在）
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 是否验证生成的工作流文件
        self.validate_output = validate_output
        
        # 创建验证器
        if self.validate_output:
            self.validator = WorkflowValidator(logger=self.logger)
    
    def _load_settings(self):
        """加载设置文件"""
        self.logger.debug(f"开始加载设置文件: {self.settings_path}")
        try:
            yaml = YAML(typ='safe')
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                settings = yaml.load(f)
                self.logger.debug(f"成功加载设置文件，包含 {len(settings)} 个顶级配置项")
                return settings
        except Exception as e:
            self.logger.error(f"加载设置文件失败: {e}")
            return {}
    
    def _load_site_config(self, site_id: str):
        """加载站点配置"""
        self.logger.debug(f"开始加载站点 {site_id} 的配置")
        try:
            site_path = self.sites_dir / f"{site_id}.yaml"
            if not site_path.exists():
                self.logger.error(f"站点配置文件不存在: {site_path}")
                return None
                
            yaml = YAML(typ='safe')
            with open(site_path, 'r', encoding='utf-8') as f:
                config = yaml.load(f)
                self.logger.debug(f"成功加载站点 {site_id} 配置，包含 {len(config)} 个顶级配置项")
                if self.logger.level == logging.DEBUG:
                    self.logger.debug(f"站点 {site_id} 配置包含以下模块: {', '.join(config.keys())}")
                return config
        except Exception as e:
            self.logger.error(f"加载站点配置失败: {e}")
            return None
    
    def _extract_global_config(self):
        """从设置中提取全局配置"""
        self.logger.debug("开始提取全局配置")
        try:
            global_config = {}
            
            # 提取运行时设置
            runtime = self.settings.get('runtime', {})
            global_config['runtime'] = {
                'mode': runtime.get('mode', 'local'),
                'runner': runtime.get('runner', 'ubuntu-latest'),
                'python_version': runtime.get('python_version', '3.10'),
                'timeout_minutes': runtime.get('timeout_minutes', 30),
                'timezone': runtime.get('timezone', 'Asia/Shanghai'),
                'debug': runtime.get('debug', False)
            }
            self.logger.debug(f"提取运行时设置: runner={global_config['runtime']['runner']}, python_version={global_config['runtime']['python_version']}")
            
            # 提取路径设置
            paths = self.settings.get('paths', {})
            global_config['paths'] = {
                'data': paths.get('data', 'data'),
                'data_daily': paths.get('data_daily', 'data/daily'),
                'analysis': paths.get('analysis', 'analysis'),
                'analysis_daily': paths.get('analysis_daily', 'analysis/daily'),
                'status': paths.get('status', 'status'),
                'logs': paths.get('logs', 'logs'),
                'config': paths.get('config', 'config'),
                'config_sites': paths.get('config_sites', 'config/sites')
            }
            self.logger.debug(f"提取路径设置: data_daily={global_config['paths']['data_daily']}, config_sites={global_config['paths']['config_sites']}")
            
            # 提取通知设置
            notification = self.settings.get('notification', {})
            global_config['notification'] = {
                'enabled': notification.get('enabled', False),
                'type': notification.get('type', 'none'),
                'webhooks': notification.get('webhooks', {}),
                'template': notification.get('template', ''),
                'channels': notification.get('channels', {})
            }
            self.logger.debug(f"提取通知设置: enabled={global_config['notification']['enabled']}, type={global_config['notification']['type']}")
            
            # 提取代理设置
            proxy_pool = self.settings.get('proxy_pool', {})
            global_config['proxy'] = {
                'enabled': proxy_pool.get('enabled', False),
                'pool_size': proxy_pool.get('pool_size', 20),
                'update_interval': proxy_pool.get('update_interval', '0 0 * * *'),
                'validation': proxy_pool.get('validation', {'timeout': 10, 'retry_count': 3})
            }
            self.logger.debug(f"提取代理设置: enabled={global_config['proxy']['enabled']}, pool_size={global_config['proxy']['pool_size']}")
            
            # 提取分析设置
            analysis = self.settings.get('analysis', {})
            global_config['analysis'] = {
                'enabled': analysis.get('enabled', True),
                'provider': analysis.get('provider', 'gemini'),
                'prompt_dir': analysis.get('prompt_dir', 'config/analysis/prompts'),
                'batch_size': analysis.get('batch_size', 100),
                'max_retry': analysis.get('max_retry', 3)
            }
            self.logger.debug(f"提取分析设置: provider={global_config['analysis']['provider']}, prompt_dir={global_config['analysis']['prompt_dir']}")
            
            # 提取其他全局设置
            global_config['github_actions'] = self.settings.get('github_actions', {})
            global_config['schedules'] = self.settings.get('schedules', {})
            global_config['scripts'] = self.settings.get('scripts', {})
            global_config['dependencies'] = self.settings.get('dependencies', {})
            global_config['project'] = self.settings.get('project', {})
            
            self.logger.debug(f"全局配置提取完成，包含 {len(global_config)} 个顶级配置项")
            return global_config
        except Exception as e:
            self.logger.error(f"提取全局配置失败: {e}")
            return {}
    
    def _process_workflow_keys(self, workflow_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理工作流对象中的键，确保顺序正确并且 'on' 键不会被引号包围
        
        Args:
            workflow_obj: 工作流对象
            
        Returns:
            处理后的工作流对象
        """
        # 递归处理对象中的所有字符串值
        def process_obj(obj):
            if isinstance(obj, dict):
                # 处理顶级工作流对象
                if 'name' in obj or 'on' in obj or 'jobs' in obj:
                    # 创建新字典，按照标准顺序排列键
                    new_dict = {}
                    
                    # 标准顺序：name, run-name, on, permissions, env, defaults, concurrency, jobs
                    standard_order = ['name', 'run-name', 'on', 'permissions', 'env', 'defaults', 'concurrency', 'jobs']
                    
                    # 首先按标准顺序添加存在的键
                    for key in standard_order:
                        if key in obj:
                            # 特殊处理 'on' 键，确保它不会被引号包围
                            if key == 'on':
                                new_dict['on'] = process_obj(obj['on'])
                            # 特殊处理 'jobs' 键，保持作业顺序
                            elif key == 'jobs':
                                new_dict['jobs'] = self._process_jobs_order(obj['jobs'])
                            else:
                                new_dict[key] = process_obj(obj[key])
                    
                    # 添加任何其他不在标准顺序中的键
                    for k, v in obj.items():
                        if k not in standard_order:
                            new_dict[k] = process_obj(v)
                            
                    return new_dict
                else:
                    # 对于非顶级对象，保持原有顺序但转换为普通dict
                    new_dict = {}
                    for k, v in obj.items():
                        new_dict[k] = process_obj(v)
                    return new_dict
            elif isinstance(obj, list):
                return [process_obj(item) for item in obj]
            else:
                return obj
        
        return process_obj(workflow_obj)
    
    def _process_jobs_order(self, jobs_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理作业对象，确保作业按依赖关系排序
        
        Args:
            jobs_obj: 作业对象
            
        Returns:
            排序后的作业对象（普通dict）
        """
        # 理想的作业执行顺序（基于依赖关系）
        preferred_order = [
            'setup',
            'update_proxy_pool', 
            'crawl', 
            'analyze', 
            'update_dashboard',
            'workflow_summary',
            'notify_completion'
        ]
        
        ordered_jobs = {}  # 使用普通dict而不是OrderedDict
        
        # 首先按照推荐顺序添加存在的作业
        for job_id in preferred_order:
            if job_id in jobs_obj:
                ordered_jobs[job_id] = self._process_single_job(jobs_obj[job_id])
        
        # 然后添加任何其他不在推荐顺序中的作业
        for job_id, job_def in jobs_obj.items():
            if job_id not in preferred_order:
                ordered_jobs[job_id] = self._process_single_job(job_def)
        
        return ordered_jobs
    
    def _process_single_job(self, job_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个作业定义
        
        Args:
            job_def: 作业定义
            
        Returns:
            处理后的作业定义（普通dict）
        """
        # 作业级别的键顺序
        job_key_order = [
            'name', 'if', 'needs', 'runs-on', 'environment', 'concurrency',
            'outputs', 'env', 'defaults', 'permissions', 'timeout-minutes',
            'strategy', 'continue-on-error', 'container', 'services',
            'uses', 'with', 'secrets', 'steps'
        ]
        
        ordered_job = {}  # 使用普通dict而不是OrderedDict
        
        # 按照标准顺序添加存在的键
        for key in job_key_order:
            if key in job_def:
                ordered_job[key] = job_def[key]
        
        # 添加任何其他键
        for k, v in job_def.items():
            if k not in job_key_order:
                ordered_job[k] = v
        
        return ordered_job
    
    def _prepare_data_for_yaml_dump(self, data: Any, current_key: Optional[str] = None) -> Any:
        """
        Recursively prepares data loaded from JSON for dumping with ruamel.yaml.
        Handles specific string conversions and type transformations.
        """
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                new_dict[k] = self._prepare_data_for_yaml_dump(v, k)
            return new_dict
        elif isinstance(data, list):
            return [self._prepare_data_for_yaml_dump(item, current_key) for item in data]
        elif isinstance(data, str):
            # First, process escaped sequences that might come from JSON strings
            # (e.g., if Jsonnet emits a string like "foo\\\\nbar", json.loads gives "foo\\nbar")
            processed_str = data
            # Check for literal backslashes, which might indicate escaped sequences
            if '\\' in processed_str: 
                try:
                    # This attempts to decode json-style string escapes within the string itself.
                    processed_str = processed_str.replace(r'\\n', '\n')
                    processed_str = processed_str.replace(r'\\"', '"')
                    processed_str = processed_str.replace(r"\\\'", "'")
                    processed_str = processed_str.replace(r'\\\\', r'\\') # handle literal escaped backslash for paths
                except Exception:
                    pass # Fallback to original string if any error

            # Rule 1: Multi-line 'run' scripts
            if current_key == 'run' and '\n' in processed_str:
                # Ensure that the string is clean of leading/trailing quotes before making it a LiteralScalarString
                return LiteralScalarString(processed_str.strip('"\''))

            # Rule 2: GitHub expressions ${{ ... }}
            if processed_str.startswith('${{') and processed_str.endswith('}}'):
                return PlainScalarString(processed_str)

            # Rule 3: Booleans as strings "true" / "false"
            if processed_str.lower() == 'true': # Case-insensitive for robustness
                return True
            if processed_str.lower() == 'false': # Case-insensitive
                return False

            # Rule 4: Numbers as strings "123"
            # Ensure it's a simple integer and not part of something like a cron string or version.
            if processed_str.isdigit() and current_key != 'cron':
                if not (current_key and ('version' in current_key.lower() or 'id' in current_key.lower() or 'name' in current_key.lower())):
                    try:
                        return int(processed_str)
                    except ValueError:
                        pass 

            # Default string handling (already processed for basic escapes)
            return processed_str
        else:
            # For other types (int, bool, float, NoneType), return as is.
            return data

    def generate_workflow(self, template_name: str, output_name: str, ext_vars: Optional[Dict[str, Any]] = None):
        """
        使用Jsonnet模板生成工作流文件
        
        Args:
            template_name: 模板文件名（不含扩展名）
            output_name: 输出文件名
            ext_vars: 传递给Jsonnet的外部变量
            
        Returns:
            bool: 是否成功生成
        """
        self.logger.debug(f"开始生成工作流: 模板={template_name}, 输出={output_name}")
        try:
            # 准备模板路径和输出路径
            template_path = self.templates_dir / f"{template_name}.jsonnet"
            output_path = self.output_dir / f"{output_name}.yml"
            
            self.logger.debug(f"模板路径: {template_path}")
            self.logger.debug(f"输出路径: {output_path}")
            
            # 确保模板文件存在
            if not template_path.exists():
                self.logger.error(f"模板文件不存在: {template_path}")
                return False
            
            # 准备外部变量
            ext_vars = ext_vars or {}
            self.logger.debug(f"外部变量: {', '.join(ext_vars.keys())}")
            ext_vars_json = {k: json.dumps(v) for k, v in ext_vars.items()}
            
            # 渲染Jsonnet模板
            self.logger.debug(f"开始渲染 Jsonnet 模板: {template_name}")
            json_str = _jsonnet.evaluate_file(
                str(template_path),
                ext_vars=ext_vars_json
            )
            self.logger.debug(f"Jsonnet 模板渲染完成，生成 JSON 数据长度: {len(json_str)} 字节")
            
            # 解析JSON
            workflow_obj = json.loads(json_str)
            self.logger.debug(f"JSON 解析完成，工作流对象包含 {len(workflow_obj)} 个顶级键")
            
            # 处理工作流对象，确保键的顺序正确
            self.logger.debug("开始处理工作流对象键的顺序")
            workflow_obj = self._process_workflow_keys(workflow_obj)
            
            # 处理作业顺序
            if 'jobs' in workflow_obj:
                self.logger.debug(f"开始处理作业顺序，共 {len(workflow_obj['jobs'])} 个作业")
                workflow_obj['jobs'] = self._process_jobs_order(workflow_obj['jobs'])
            
            # 准备YAML输出
            self.logger.debug("准备 YAML 输出")
            yaml = YAML()
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.preserve_quotes = True
            
            # 准备数据以便更好地输出为YAML
            self.logger.debug("准备数据以便更好地输出为YAML")
            workflow_data = self._prepare_data_for_yaml_dump(workflow_obj)
            
            # 写入YAML文件
            self.logger.debug(f"开始写入 YAML 文件: {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(workflow_data, f)
            self.logger.debug(f"YAML 文件写入完成: {output_path}")
            
            # 验证生成的工作流文件（如果启用）
            if self.validate_output:
                self.logger.debug(f"验证步骤: 开始验证工作流文件 {output_path}")
                try:
                    self.logger.debug("验证步骤: 读取工作流文件内容")
                    with open(output_path, 'r', encoding='utf-8') as f:
                        workflow_content = f.read()
                    
                    self.logger.debug("验证步骤: 调用 WorkflowValidator.validate 方法")
                    is_valid, errors = self.validator.validate(workflow_content)
                    
                    if not is_valid:
                        self.logger.warning(f"验证步骤: 工作流文件验证失败 {output_path}")
                        self.logger.debug(f"验证步骤: 发现 {len(errors)} 个验证错误")
                        for i, error in enumerate(errors):
                            self.logger.warning(f"验证错误 {i+1}/{len(errors)}: {error}")
                        self.logger.debug("验证步骤: 尽管有验证错误，但仍然继续生成工作流文件")
                        # 不返回False，因为文件已经生成，只是有警告
                    else:
                        self.logger.debug(f"验证步骤: 工作流文件验证通过 {output_path}")
                except Exception as e:
                    self.logger.warning(f"验证步骤: 验证过程中发生错误: {e}")
                    import traceback
                    self.logger.debug(f"验证步骤: 验证错误详情: {traceback.format_exc()}")
                    # 验证错误不应该影响文件生成
            
            self.logger.info(f"成功生成工作流文件: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"生成工作流文件失败: {e}")
            import traceback
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            return False
    def generate_crawler_workflow(self, site_id: str) -> bool:
        """
        生成爬虫工作流文件
        
        Args:
            site_id: 站点ID
            
        Returns:
            bool: 是否成功生成
        """
        self.logger.debug(f"开始为站点 {site_id} 生成爬虫工作流")
        try:
            # 加载站点配置
            self.logger.debug(f"加载站点 {site_id} 配置")
            site_config = self._load_site_config(site_id)
            if not site_config:
                self.logger.error(f"无法加载站点 {site_id} 配置，取消生成爬虫工作流")
                return False
            
            # 准备外部变量
            self.logger.debug(f"准备站点 {site_id} 爬虫工作流的外部变量")
            ext_vars = {
                "site_id": site_id,
                "site_config": site_config,
                "global_config": self.global_config
            }
            
            # 生成工作流文件
            self.logger.debug(f"开始生成站点 {site_id} 的爬虫工作流文件")
            return self.generate_workflow("crawler", f"crawler_{site_id}", ext_vars)
            
        except Exception as e:
            self.logger.error(f"生成爬虫工作流文件失败: {e}")
            import traceback
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            return False
    
    def generate_analyzer_workflow(self, site_id: str) -> bool:
        """
        生成分析工作流文件
        
        Args:
            site_id: 站点ID
            
        Returns:
            bool: 是否成功生成
        """
        self.logger.debug(f"开始为站点 {site_id} 生成分析工作流")
        try:
            # 加载站点配置
            self.logger.debug(f"加载站点 {site_id} 配置")
            site_config = self._load_site_config(site_id)
            if not site_config:
                self.logger.error(f"无法加载站点 {site_id} 配置，取消生成分析工作流")
                return False
            
            # 准备外部变量
            self.logger.debug(f"准备站点 {site_id} 分析工作流的外部变量")
            ext_vars = {
                "site_id": site_id,
                "site_config": site_config,
                "global_config": self.global_config
            }
            
            # 生成工作流文件
            self.logger.debug(f"开始生成站点 {site_id} 的分析工作流文件")
            return self.generate_workflow("analyzer", f"analyzer_{site_id}", ext_vars)
            
        except Exception as e:
            self.logger.error(f"生成分析工作流文件失败: {e}")
            import traceback
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            return False
    
    def generate_enhanced_analyzer_workflow(self, site_id: str) -> bool:
        """
        生成增强版分析工作流文件（完整功能对标YAML模板）
{{ ... }}
        Args:
            site_id: 站点ID
            
        Returns:
            bool: 是否成功生成
        """
        try:
            self.logger.info(f"开始生成增强版分析工作流: {site_id}")
            
            # 加载站点配置
            site_config_path = self.sites_dir / f"{site_id}.yaml"
            if not site_config_path.exists():
                self.logger.error(f"站点配置文件不存在: {site_config_path}")
                return False
            
            with open(site_config_path, 'r', encoding='utf-8') as f:
                site_config = self.yaml.load(f)
            
            # 准备外部变量
            ext_vars = {
                "site_id": site_id,
                "site_config": json.dumps(site_config, ensure_ascii=False),
                "global_config": json.dumps(self.global_config, ensure_ascii=False)
            }
            
            # 使用增强版模板
            template_name = "analyzer_enhanced"
            output_name = f"analyzer_{site_id}"
            
            success = self.generate_workflow(template_name, output_name, ext_vars)
            
            if success:
                self.logger.info(f"✅ 成功生成增强版分析工作流: {output_name}.yml")
            else:
                self.logger.error(f"❌ 生成增强版分析工作流失败: {site_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"生成增强版分析工作流异常: {site_id}, {e}")
            return False
    
    def generate_dashboard_workflow(self) -> bool:
        """
        生成仪表盘更新工作流文件
        
        Returns:
            bool: 是否成功生成
        """
        try:
            # 准备外部变量
            ext_vars = {
                "global_config": self.global_config
            }
            
            # 生成工作流文件
            return self.generate_workflow("dashboard", "update_dashboard", ext_vars)
            
        except Exception as e:
            self.logger.error(f"生成仪表盘更新工作流文件失败: {e}")
            return False
    
    def generate_proxy_manager_workflow(self) -> bool:
        """
        生成代理池管理工作流文件
        
        Returns:
            bool: 是否成功生成
        """
        try:
            # 准备外部变量
            ext_vars = {
                "global_config": self.global_config
            }
            
            # 生成工作流文件
            return self.generate_workflow("proxy_pool", "proxy_pool_manager", ext_vars)
            
        except Exception as e:
            self.logger.error(f"生成代理池管理工作流文件失败: {e}")
            return False
    
    def generate_master_workflow(self) -> bool:
        """
        生成主调度工作流文件
        
        Returns:
            bool: 是否成功生成
        """
        try:
            # 准备外部变量
            ext_vars = {
                "global_config": self.global_config
            }
            
            # 生成工作流文件
            return self.generate_workflow("master_workflow", "master_workflow", ext_vars)
            
        except Exception as e:
            self.logger.error(f"生成主调度工作流文件失败: {e}")
            return False
    
    def generate_common_workflows(self) -> bool:
        """
        生成所有通用工作流文件
        
        Returns:
            bool: 是否所有工作流都成功生成
        """
        success_count = 0
        total_count = 4  # 主工作流、仪表盘工作流、代理池管理工作流和主调度工作流
        total_count = 3  # 主工作流、仪表盘工作流和代理池管理工作流
        
        # 生成主调度工作流
        if self.generate_master_workflow():
            success_count += 1
        
        # 生成仪表盘更新工作流
        if self.generate_dashboard_workflow():
            success_count += 1
        
        # 生成代理池管理工作流
        if self.generate_proxy_manager_workflow():
            success_count += 1
        
        self.logger.info(f"通用工作流生成完成，成功: {success_count}/{total_count}")
        return success_count == total_count
    
    def generate_all_site_workflows(self) -> bool:
        """
        为所有站点生成工作流文件
        
        Returns:
            bool: 是否所有工作流都成功生成
        """
        try:
            # 获取所有站点ID
            site_files = list(self.sites_dir.glob("*.yaml"))
            site_ids = [site_file.stem for site_file in site_files if site_file.stem != "example"]
            
            success_count = 0
            total_count = len(site_ids) * 2  # 每个站点有爬虫和分析两个工作流
            
            for site_id in site_ids:
                # 生成爬虫工作流
                if self.generate_crawler_workflow(site_id):
                    success_count += 1
                
                # 生成分析工作流
                if self.generate_analyzer_workflow(site_id):
                    success_count += 1
            
            self.logger.info(f"站点工作流生成完成，成功: {success_count}/{total_count}")
            return success_count == total_count
            
        except Exception as e:
            self.logger.error(f"生成所有站点工作流文件失败: {e}")
            return False
    
    def generate_all_workflows(self) -> bool:
        """
        生成所有工作流文件
        
        Returns:
            bool: 是否所有工作流都成功生成
        """
        # 生成通用工作流
        common_success = self.generate_common_workflows()
        
        # 生成站点工作流
        site_success = self.generate_all_site_workflows()
        
        return common_success and site_success

# 在脚本末尾添加主执行块（如果需要）
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('jsonnet_workflow_generator_main')
    
    # 示例用法
    generator = JsonnetWorkflowGenerator(logger=logger)
    
    # 生成通用工作流
    generator.generate_common_workflows()
    
    # 为所有站点生成工作流
    generator.generate_all_site_workflows()

    # 为特定站点生成增强版分析器工作流（如果需要测试）
    # example_site_id = "example_site" # 替换为实际的站点ID
    # if (generator.sites_dir / f"{example_site_id}.yaml").exists():
    #     logger.info(f"尝试为站点 {example_site_id} 生成增强版分析工作流...")
    #     generator.generate_enhanced_analyzer_workflow(example_site_id)
    # else:
    #     logger.warning(f"站点配置文件 {example_site_id}.yaml 不存在，跳过增强版分析工作流生成。")

    logger.info("所有工作流生成任务完成。")
