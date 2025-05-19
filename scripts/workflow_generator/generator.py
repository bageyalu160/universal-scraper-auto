#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 主生成器类
"""

import os
import sys
import yaml
import logging
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
import jinja2
import shutil
import glob
import re

from .strategies import (
    WorkflowFactory, WorkflowStrategy, 
    CrawlerWorkflowStrategy, AnalyzerWorkflowStrategy
)
from .renderers import WorkflowYamlRenderer
from .validators import WorkflowValidator


class WorkflowGenerator:
    """工作流生成器类，用于生成GitHub Actions工作流文件"""
    
    def __init__(self, settings_path=None, sites_dir=None, output_dir=None, logger=None):
        """
        初始化工作流生成器
        
        Args:
            settings_path (str, optional): 设置文件路径
            sites_dir (str, optional): 站点配置目录
            output_dir (str, optional): 输出目录
            logger (logging.Logger, optional): 日志记录器
        """
        # 设置日志记录器
        self.logger = logger or logging.getLogger('workflow_generator')
        
        # 设置路径
        self.base_dir = Path(__file__).parent.parent.parent
        self.settings_path = settings_path or self.base_dir / "config" / "settings.yaml"
        self.sites_dir = sites_dir or self.base_dir / "config" / "sites"
        self.output_dir = output_dir or self.base_dir / ".github" / "workflows"
        self.templates_dir = self.base_dir / "config" / "workflow" / "templates"
        
        # 加载设置
        self.settings = self._load_settings()
        
        # 初始化工厂和策略
        self.factory = WorkflowFactory()
        self.factory.register_strategy("crawler", CrawlerWorkflowStrategy())
        self.factory.register_strategy("analyzer", AnalyzerWorkflowStrategy())
        
        # 初始化渲染器和验证器
        self.renderer = WorkflowYamlRenderer(logger=self.logger)
        self.validator = WorkflowValidator(logger=self.logger)

        # 创建Jinja2环境
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 添加自定义过滤器
        self.jinja_env.filters['normalize_condition'] = self._normalize_condition_filter
        self.jinja_env.filters['normalize_env_var'] = self._normalize_env_var_filter
        self.jinja_env.filters['to_yaml'] = self._to_yaml_filter
    
    def _normalize_condition_filter(self, value):
        """
        标准化条件表达式的自定义过滤器
        
        Args:
            value: 输入的条件表达式
            
        Returns:
            标准化后的条件表达式
        """
        if not value or '{{' in value:  # 跳过空值或已经包含 Jinja2 模板
            return value
            
        # 检查是否已经被 ${{ }} 包装
        is_wrapped = value.strip().startswith('${{') and value.strip().endswith('}}')
        
        # 检查是否包含需要包装的变量引用
        has_var_ref = re.search(r'\b(?:vars|env|secrets|github|steps|needs|inputs)\.[A-Za-z0-9_\.]+\b', value)
        
        if has_var_ref and not is_wrapped:
            # 标准化操作符周围的空格
            value = self._standardize_operators(value)
            return f'${{ {value.strip()} }}'
        elif is_wrapped:
            # 提取内部表达式并标准化
            inner_expr = value.strip()[3:-2].strip()
            normalized_inner = self._standardize_operators(inner_expr)
            if inner_expr != normalized_inner:
                return f'${{ {normalized_inner} }}'
                
        return value
    
    def _standardize_operators(self, expr):
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
    
    def _normalize_env_var_filter(self, value):
        """
        标准化环境变量引用的自定义过滤器
        
        Args:
            value: 输入的环境变量值
            
        Returns:
            标准化后的环境变量值
        """
        if not value or '{{' in value:  # 跳过空值或已经包含 Jinja2 模板
            return value
            
        # 检查是否已经被 ${{ }} 包装
        is_wrapped = value.strip().startswith('${{') and value.strip().endswith('}}')
        
        # 检查是否包含需要包装的变量引用
        has_var_ref = re.search(r'\b(?:vars|env|secrets|github|steps|needs|inputs)\.[A-Za-z0-9_\.]+\b', value)
        
        if has_var_ref and not is_wrapped:
            return f'${{ {value.strip()} }}'
                
        return value
    
    def _to_yaml_filter(self, value):
        """
        将Python对象转换为YAML字符串的自定义过滤器
        
        Args:
            value: 输入的Python对象
            
        Returns:
            YAML格式的字符串
        """
        return yaml.dump(value, default_flow_style=False).strip()
    
    def _load_settings(self) -> Dict[str, Any]:
        """加载设置文件"""
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
            self.logger.info(f"成功加载设置文件: {self.settings_path}")
            return settings
        except Exception as e:
            self.logger.error(f"加载设置文件失败: {e}")
            raise
    
    def _load_site_config(self, site_id: str) -> Optional[Dict[str, Any]]:
        """加载站点配置"""
        site_config_path = self.sites_dir / f"{site_id}.yaml"
        try:
            with open(site_config_path, 'r', encoding='utf-8') as f:
                site_config = yaml.safe_load(f)
                
            # 添加站点ID
            site_config['site_id'] = site_id
            
            self.logger.info(f"成功加载站点配置: {site_config_path}")
            return site_config
        except Exception as e:
            self.logger.error(f"加载站点配置失败: {e}")
            return None
    
    def _extract_global_config(self) -> Dict[str, Any]:
        """从设置中提取全局配置"""
        return {
            # 基本设置
            "python_version": self.settings.get('python_version', '3.10'),
            "data_dir": self.settings.get('data_dir', 'data'),
            "analysis_dir": self.settings.get('analysis_dir', 'analysis'),
            "status_dir": self.settings.get('status_dir', 'status'),
            
            # 爬虫设置
            "scraper_dependencies": "requests beautifulsoup4 pandas pyyaml",
            
            # 分析设置
            "analyzer_script": self.settings.get('ai_analysis', {}).get('script_path', 'scripts/ai_analyzer.py'),
            "output_file": self.settings.get('ai_analysis', {}).get('output_file', 'analysis_result.tsv'),
            "output_format": self.settings.get('ai_analysis', {}).get('output_format', 'tsv'),
            "analysis_dependencies": "requests pandas pyyaml google-generativeai openai",
            
            # 通知设置
            "notification_script": self.settings.get('notification', {}).get('script_path', 'scripts/notify.py'),
            "send_notification": self.settings.get('notification', {}).get('enabled', False)
        }
    
    def validate_template(self, template_path: Path) -> Tuple[bool, List[str]]:
        """
        验证模板文件
        
        Args:
            template_path: 模板文件路径
            
        Returns:
            (是否有效, 错误消息列表)
        """
        try:
            # 读取模板内容
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 使用验证器检查模板语法
            return self.validator.validate_template(template_content)
        except Exception as e:
            return False, [f"读取或验证模板失败: {str(e)}"]
    
    def preprocess_template(self, template_content: str) -> str:
        """
        预处理模板内容，统一格式
        
        Args:
            template_content: 模板内容
            
        Returns:
            预处理后的模板内容
        """
        # 标准化if条件中的变量引用
        def normalize_condition(match):
            condition = match.group(1).strip()
            
            # 跳过已经包含在Jinja标签中的条件
            if "{{" in condition or "{%" in condition:
                return f"if: {condition}"
                
            # 使用过滤器标准化条件表达式
            return f"if: {self._normalize_condition_filter(condition)}"
            
        # 处理if条件
        template_content = re.sub(r'if:\s*([^\n]+)', normalize_condition, template_content)
        
        # 处理环境变量引用
        def normalize_env_var(match):
            var_name = match.group(1)
            var_value = match.group(2).strip()
            
            # 跳过已经包含在Jinja标签中的值
            if "{{" in var_value or "{%" in var_value:
                return f"{var_name}: {var_value}"
                
            # 使用过滤器标准化环境变量值
            normalized_value = self._normalize_env_var_filter(var_value)
            return f"{var_name}: {normalized_value}"
            
        # 处理环境变量
        template_content = re.sub(r'([ ]*[A-Z_]+):\s*([^\n]+)', normalize_env_var, template_content)
        
        # 修复带引号的if条件
        template_content = re.sub(r'if:\s*"([^"]*?)"', r'if: \1', template_content)
        
        return template_content
    
    def generate_workflow(self, site_id: str, workflow_type: str) -> bool:
        """
        生成工作流文件
        
        Args:
            site_id: 站点ID
            workflow_type: 工作流类型 ("crawler" 或 "analyzer")
            
        Returns:
            是否成功生成
        """
        # 加载站点配置
        site_config = self._load_site_config(site_id)
        if not site_config:
            return False
        
        # 提取全局配置
        global_config = self._extract_global_config()
        
        # 检查模板文件是否存在
        template_path = self.templates_dir / f"{workflow_type}.yml.template"
        if not template_path.exists():
            self.logger.error(f"模板文件不存在: {template_path}")
            return False
            
        # 验证模板文件
        is_valid, errors = self.validate_template(template_path)
        if not is_valid:
            self.logger.error(f"模板验证失败: {errors}")
            return False
        
        try:
            # 使用工厂创建工作流
            workflow = self.factory.create_workflow(workflow_type, site_config, global_config)
            
            # 使用渲染器渲染工作流
            try:
                yaml_content = self.renderer.render_to_string(workflow)
            except ValueError as e:
                self.logger.error(f"工作流渲染失败: {e}")
                return False
            
            # 使用JSON Schema和actionlint验证工作流
            is_valid, errors = self.validator.validate(yaml_content)
            if not is_valid:
                self.logger.error(f"工作流验证失败: {errors}")
                return False
            
            # 检查格式问题
            warnings = self.validator.check_for_common_formatting_issues(yaml_content)
            if warnings:
                for warning in warnings:
                    self.logger.warning(f"工作流格式警告: {warning}")
            
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 写入文件
            output_filename = f"{workflow_type}_{site_id}.yml"
            output_path = self.output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            
            self.logger.info(f"成功生成工作流文件: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"生成工作流文件失败: {e}")
            return False
    
    def generate_all_workflows(self) -> bool:
        """为所有站点生成工作流文件"""
        # 获取所有站点ID
        site_files = list(self.sites_dir.glob("*.yaml"))
        site_ids = [site_file.stem for site_file in site_files]
        
        if not site_ids:
            self.logger.warning("未找到任何站点配置文件")
            return False
        
        success_count = 0
        total_count = len(site_ids) * 2  # 每个站点生成两个工作流（爬虫和分析）
        
        for site_id in site_ids:
            # 跳过示例配置
            if site_id == "example":
                self.logger.info(f"跳过示例配置: {site_id}")
                continue
                
            # 生成爬虫工作流
            if self.generate_workflow(site_id, "crawler"):
                success_count += 1
            
            # 生成分析工作流
            if self.generate_workflow(site_id, "analyzer"):
                success_count += 1
        
        self.logger.info(f"工作流生成完成，成功: {success_count}/{total_count}")
        return success_count > 0
    
    def update_workflows(self, sites: Optional[str] = None) -> bool:
        """更新指定站点的工作流文件，如果未指定则更新所有站点"""
        if sites:
            site_ids = sites.split(',')
            total_count = len(site_ids) * 2  # 每个站点生成两个工作流
            
            success_count = 0
            for site_id in site_ids:
                # 生成爬虫工作流
                if self.generate_workflow(site_id, "crawler"):
                    success_count += 1
                
                # 生成分析工作流
                if self.generate_workflow(site_id, "analyzer"):
                    success_count += 1
            
            self.logger.info(f"工作流更新完成，成功: {success_count}/{total_count}")
            return success_count > 0
        else:
            # 更新所有站点
            return self.generate_all_workflows()
            
    def generate_master_workflow(self) -> bool:
        """
        生成主调度工作流文件
        
        Returns:
            bool: 是否成功生成
        """
        try:
            # 获取所有站点ID
            site_files = list(self.sites_dir.glob("*.yaml"))
            site_ids = [site_file.stem for site_file in site_files if site_file.stem != "example"]
            
            template_path = self.templates_dir / "master_workflow.yml.template"
            output_path = self.output_dir / "master_workflow.yml"
            
            if not template_path.exists():
                self.logger.error(f"模板文件不存在: {template_path}")
                return False
            
            # 验证模板语法
            is_valid, errors = self.validate_template(template_path)
            if not is_valid:
                self.logger.error(f"主调度工作流模板验证失败: {errors}")
                return False
            
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 读取模板内容
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 预处理模板内容
            content = self.preprocess_template(content)
            
            # 写入修改后的内容
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 验证生成的工作流文件
            is_valid, errors = self.validator.validate(content)
            if not is_valid:
                self.logger.error(f"生成的主调度工作流验证失败: {errors}")
                return False
            
            self.logger.info(f"成功生成主调度工作流文件: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"生成主调度工作流文件失败: {e}")
            return False
            
    def generate_dashboard_workflow(self) -> bool:
        """
        生成仪表盘更新工作流文件
        
        Returns:
            bool: 是否成功生成
        """
        try:
            template_path = self.templates_dir / "update_dashboard.yml.template"
            output_path = self.output_dir / "update_dashboard.yml"
            
            if not template_path.exists():
                self.logger.error(f"模板文件不存在: {template_path}")
                return False
            
            # 验证模板语法
            is_valid, errors = self.validate_template(template_path)
            if not is_valid:
                self.logger.error(f"仪表盘更新工作流模板验证失败: {errors}")
                return False
            
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 读取模板内容
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 预处理模板内容    
            content = self.preprocess_template(content)
            
            # 写入修改后的内容
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 验证生成的工作流文件
            is_valid, errors = self.validator.validate(content)
            if not is_valid:
                self.logger.error(f"生成的仪表盘更新工作流验证失败: {errors}")
                return False
            
            self.logger.info(f"成功生成仪表盘更新工作流文件: {output_path}")
            return True
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
            template_path = self.templates_dir / "proxy_pool_manager.yml.template"
            output_path = self.output_dir / "proxy_pool_manager.yml"
            
            if not template_path.exists():
                self.logger.error(f"模板文件不存在: {template_path}")
                return False
            
            # 验证模板语法
            is_valid, errors = self.validate_template(template_path)
            if not is_valid:
                self.logger.error(f"代理池管理工作流模板验证失败: {errors}")
                return False
            
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 读取模板内容
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 预处理模板内容
            content = self.preprocess_template(content)
            
            # 写入修改后的内容
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            # 验证生成的工作流文件
            is_valid, errors = self.validator.validate(content)
            if not is_valid:
                self.logger.error(f"生成的代理池管理工作流验证失败: {errors}")
                return False
            
            self.logger.info(f"成功生成代理池管理工作流文件: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"生成代理池管理工作流文件失败: {e}")
            return False
    
    def generate_crawler_workflow_direct(self, site_id: str) -> bool:
        """
        直接生成爬虫工作流（使用简化的模板方法）
        
        Args:
            site_id: 站点ID
        
        Returns:
            bool: 是否成功生成
        """
        try:
            site_config = self._load_site_config(site_id)
            if not site_config:
                return False
            
            # 获取站点名称
            site_name = (site_config.get('site', {}).get('name') or 
                         site_config.get('site_info', {}).get('name') or 
                         site_id)
            
            # 准备模板变量
            scraping_config = site_config.get('scraping', {})
            engine = scraping_config.get('engine', 'custom')
            
            # 确定依赖项
            if engine == 'firecrawl':
                scraper_dependencies = "requests pyyaml firecrawl pandas"
            elif engine == 'playwright':
                scraper_dependencies = "requests pyyaml playwright pandas"
            else:
                scraper_dependencies = "requests pyyaml beautifulsoup4 pandas"
            
            # 确定cron表达式
            schedule = scraping_config.get('schedule', '0 0 * * *')  # 默认每天午夜执行
            
            # 确定输出文件名
            output_filename = (site_config.get('output', {}).get('filename') or 
                              site_config.get('site_info', {}).get('output_filename') or 
                              f"{site_id}_data.json")
            
            # 环境变量
            env_vars = []
            # API密钥
            if 'api' in scraping_config and scraping_config.get('api', {}).get('key_env'):
                env_vars.append({
                    'name': scraping_config['api']['key_env'],
                    'secret': scraping_config['api']['key_env']
                })
            
            # 检查是否需要运行分析
            run_analysis = site_config.get('analysis', {}).get('enabled', True)
            
            # 检查代理配置
            proxy_config = scraping_config.get('proxy', {})
            use_proxy = proxy_config.get('enabled', False)
            
            # 加载模板
            template = self.jinja_env.get_template("crawler.yml.template")
            
            # 渲染模板
            template_vars = {
                'site_id': site_id,
                'site_name': site_name,
                'python_version': '3.10',
                'cron_schedule': schedule,
                'scraper_dependencies': scraper_dependencies,
                'env_vars': env_vars,
                'output_filename': output_filename,
                'data_dir': 'data',
                'status_dir': 'status',
                'scraper_script': 'scripts/scraper.py',
                'run_analysis': run_analysis,
                'use_proxy': use_proxy
            }
            
            workflow_content = template.render(**template_vars)
            
            # 预处理模板内容
            workflow_content = self.preprocess_template(workflow_content)
            
            # 验证生成的工作流
            is_valid, errors = self.validator.validate(workflow_content)
            if not is_valid:
                self.logger.error(f"生成的爬虫工作流验证失败: {errors}")
                return False
            
            # 写入工作流文件
            output_path = self.output_dir / f"crawler_{site_id}.yml"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(workflow_content)
            
            self.logger.info(f"已生成爬虫工作流: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"生成爬虫工作流失败: {e}")
            return False
    
    def generate_common_workflows(self) -> bool:
        """
        生成所有通用工作流文件
        
        Returns:
            bool: 是否所有工作流都成功生成
        """
        success_count = 0
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