#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 主生成器类
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union

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
        
        # 加载设置
        self.settings = self._load_settings()
        
        # 初始化工厂和策略
        self.factory = WorkflowFactory()
        self.factory.register_strategy("crawler", CrawlerWorkflowStrategy())
        self.factory.register_strategy("analyzer", AnalyzerWorkflowStrategy())
        
        # 初始化渲染器和验证器
        self.renderer = WorkflowYamlRenderer()
        self.validator = WorkflowValidator()
    
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
        
        try:
            # 使用工厂创建工作流
            workflow = self.factory.create_workflow(workflow_type, site_config, global_config)
            
            # 使用渲染器渲染工作流 - 这一步可能会抛出 ValueError 异常
            try:
                yaml_content = self.renderer.render_to_string(workflow)
            except ValueError as e:
                self.logger.error(f"工作流渲染失败: {e}")
                return False
            
            # 验证工作流
            is_valid, errors = self.validator.validate(yaml_content)
            if not is_valid:
                self.logger.error(f"工作流验证失败: {errors}")
                return False
            
            # 检查格式问题
            warnings = self.validator.check_for_common_formatting_issues(yaml_content)
            if warnings:
                self.logger.warning(f"工作流格式问题: {warnings}")
            
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