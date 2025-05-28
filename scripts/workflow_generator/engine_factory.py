#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流引擎工厂 - 支持多种模板引擎
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union

# 导入生成器
from .generator import WorkflowGenerator
from .jsonnet_generator import JsonnetWorkflowGenerator


class WorkflowEngineFactory:
    """工作流引擎工厂类，用于创建不同类型的工作流生成器"""
    
    def __init__(self, settings_path=None, sites_dir=None, output_dir=None, logger=None):
        """
        初始化工作流引擎工厂
        
        Args:
            settings_path (str, optional): 设置文件路径
            sites_dir (str, optional): 站点配置目录
            output_dir (str, optional): 输出目录
            logger (logging.Logger, optional): 日志记录器
        """
        # 设置日志记录器
        self.logger = logger or logging.getLogger('workflow_engine_factory')
        
        # 设置路径
        self.base_dir = Path(__file__).parent.parent.parent
        self.settings_path = settings_path or self.base_dir / "config" / "settings.yaml"
        self.sites_dir = sites_dir or self.base_dir / "config" / "sites"
        self.output_dir = output_dir or self.base_dir / ".github" / "workflows"
        
        # 加载设置
        self.settings = self._load_settings()
        
        # 获取默认引擎配置
        self.default_engine = self._get_default_engine()
        self.allow_override = self._get_engine_override_setting()
        
        # 初始化生成器实例
        self._jinja_generator = None
        self._jsonnet_generator = None
    
    def _load_settings(self):
        """加载设置文件"""
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"加载设置文件失败: {e}")
            return {}
    
    def _get_default_engine(self):
        """从设置中获取默认引擎"""
        try:
            engine = self.settings.get('github_actions', {}).get('workflow_engine', {}).get('default_engine', 'jinja2')
            # 确保返回的是字符串类型
            if not isinstance(engine, str):
                self.logger.warning(f"默认引擎设置不是字符串: {engine}，使用jinja2作为默认引擎")
                return 'jinja2'
            return engine
        except Exception as e:
            self.logger.warning(f"获取默认引擎设置失败: {e}，使用jinja2作为默认引擎")
            return 'jinja2'
    
    def _get_engine_override_setting(self):
        """从设置中获取是否允许覆盖默认引擎的设置"""
        try:
            return self.settings.get('github_actions', {}).get('workflow_engine', {}).get('allow_override', True)
        except Exception as e:
            self.logger.warning(f"获取引擎覆盖设置失败: {e}，默认允许覆盖")
            return True
    
    def get_generator(self, engine_type: Optional[str] = None, validate_output: bool = False):
        """
        获取指定类型的工作流生成器
        
        Args:
            engine_type (str, optional): 引擎类型，'jinja2' 或 'jsonnet'。如果未指定，使用默认引擎
            
        Returns:
            WorkflowGenerator 或 JsonnetWorkflowGenerator: 工作流生成器实例
            
        Raises:
            ValueError: 如果指定的引擎类型不支持
        """
        self.logger.debug(f"开始获取工作流生成器，请求的引擎类型: {engine_type}")
        self.logger.debug(f"当前默认引擎: {self.default_engine}, 允许覆盖: {self.allow_override}")
        
        # 确保 engine_type 不是 None
        if engine_type is None:
            engine_type = self.default_engine
            self.logger.info(f"未指定引擎类型，使用默认引擎: {engine_type}")
            self.logger.debug(f"模型选择决策: 使用默认引擎 {engine_type} 构建模型")
        # 如果不允许覆盖默认引擎，则使用默认引擎
        elif engine_type != self.default_engine and not self.allow_override:
            self.logger.debug(f"策略决策: 请求的引擎 {engine_type} 与默认不同，但配置不允许覆盖")
            engine_type = self.default_engine
            self.logger.info(f"配置不允许覆盖默认引擎，使用默认引擎: {engine_type}")
        else:
            self.logger.debug(f"策略决策: 使用请求的引擎 {engine_type}")
        
        # 确保 engine_type 是字符串类型
        if not isinstance(engine_type, str):
            self.logger.warning(f"引擎类型不是字符串: {engine_type}，使用默认引擎: {self.default_engine}")
            engine_type = self.default_engine
        
        # 转换为小写以便于比较
        engine_type_lower = engine_type.lower()
        self.logger.debug(f"规范化引擎类型: {engine_type_lower}")
        
        # 根据引擎类型创建生成器
        if engine_type_lower == 'jinja2':
            self.logger.debug("模型定义: 使用 Jinja2 模板引擎定义工作流模型")
            if self._jinja_generator is None:
                self.logger.info("创建 Jinja2 工作流生成器")
                self.logger.debug("模型初始化: 构建 Jinja2 模板引擎实例")
                self._jinja_generator = WorkflowGenerator(
                    settings_path=self.settings_path,
                    sites_dir=self.sites_dir,
                    output_dir=self.output_dir,
                    logger=self.logger
                )
                self.logger.debug("模型初始化完成: Jinja2 工作流生成器已创建")
            else:
                self.logger.debug("使用现有的 Jinja2 工作流生成器实例")
            return self._jinja_generator
            
        elif engine_type_lower == 'jsonnet':
            self.logger.debug("模型定义: 使用 Jsonnet 模板引擎定义工作流模型")
            if self._jsonnet_generator is None:
                self.logger.info("创建 Jsonnet 工作流生成器")
                self.logger.debug("模型初始化: 构建 Jsonnet 模板引擎实例")
                self._jsonnet_generator = JsonnetWorkflowGenerator(
                    settings_path=self.settings_path,
                    sites_dir=self.sites_dir,
                    output_dir=self.output_dir,
                    logger=self.logger,
                    validate_output=validate_output
                )
                self.logger.debug("模型初始化完成: Jsonnet 工作流生成器已创建")
            else:
                self.logger.debug("使用现有的 Jsonnet 工作流生成器实例")
            return self._jsonnet_generator
            
        else:
            self.logger.error(f"不支持的引擎类型: {engine_type}")
            raise ValueError(f"不支持的引擎类型: {engine_type}")
    
    def generate_workflow(self, engine_type: Optional[str] = None, workflow_type: str = 'all', site_id: Optional[str] = None) -> bool:
        """
        使用指定引擎生成工作流
        
        Args:
            engine_type (str): 引擎类型，'jinja2' 或 'jsonnet'
            workflow_type (str): 工作流类型，'master', 'crawler', 'analyzer', 'dashboard', 'proxy_pool'
            site_id (str, optional): 站点ID，仅用于 'crawler' 和 'analyzer' 类型
            
        Returns:
            bool: 是否成功生成
        """
        self.logger.debug(f"开始生成工作流: 引擎={engine_type}, 类型={workflow_type}, 站点={site_id or '所有'}")
        try:
            # 获取生成器
            self.logger.debug("策略决策: 获取适合的工作流生成器")
            generator = self.get_generator(engine_type)
            self.logger.debug(f"生成器获取成功: {generator.__class__.__name__}")
            
            # 根据工作流类型调用相应的方法
            self.logger.debug(f"策略决策: 根据工作流类型 '{workflow_type}' 选择生成策略")
            
            if workflow_type == 'master':
                self.logger.debug("渲染决策: 生成主调度工作流")
                return generator.generate_master_workflow()
                
            elif workflow_type == 'crawler':
                if site_id is None:
                    self.logger.error("生成爬虫工作流需要指定站点ID")
                    return False
                
                self.logger.debug(f"渲染决策: 为站点 {site_id} 生成爬虫工作流")
                if engine_type.lower() == 'jinja2':
                    self.logger.debug(f"渲染器选择: 使用 Jinja2 渲染器生成爬虫工作流")
                    return generator.generate_workflow(site_id, 'crawler')
                else:
                    self.logger.debug(f"渲染器选择: 使用 Jsonnet 渲染器生成爬虫工作流")
                    return generator.generate_crawler_workflow(site_id)
                    
            elif workflow_type == 'analyzer':
                if site_id is None:
                    self.logger.error("生成分析工作流需要指定站点ID")
                    return False
                
                self.logger.debug(f"渲染决策: 为站点 {site_id} 生成分析工作流")
                if engine_type.lower() == 'jinja2':
                    self.logger.debug(f"渲染器选择: 使用 Jinja2 渲染器生成分析工作流")
                    return generator.generate_workflow(site_id, 'analyzer')
                else:
                    self.logger.debug(f"渲染器选择: 使用 Jsonnet 渲染器生成分析工作流")
                    return generator.generate_analyzer_workflow(site_id)
                    
            elif workflow_type == 'dashboard':
                self.logger.debug("渲染决策: 生成仪表盘更新工作流")
                return generator.generate_dashboard_workflow()
                
            elif workflow_type == 'proxy_pool':
                self.logger.debug("渲染决策: 生成代理池管理工作流")
                return generator.generate_proxy_manager_workflow()
                
            elif workflow_type == 'all':
                if site_id:
                    # 为指定站点生成工作流
                    self.logger.debug(f"渲染决策: 为站点 {site_id} 生成所有工作流")
                    if engine_type.lower() == 'jinja2':
                        self.logger.debug(f"渲染器选择: 使用 Jinja2 渲染器生成站点工作流")
                        self.logger.debug(f"开始生成站点 {site_id} 的爬虫工作流")
                        crawler_success = generator.generate_workflow(site_id, 'crawler')
                        self.logger.debug(f"开始生成站点 {site_id} 的分析工作流")
                        analyzer_success = generator.generate_workflow(site_id, 'analyzer')
                    else:
                        self.logger.debug(f"渲染器选择: 使用 Jsonnet 渲染器生成站点工作流")
                        self.logger.debug(f"开始生成站点 {site_id} 的爬虫工作流")
                        crawler_success = generator.generate_crawler_workflow(site_id)
                        self.logger.debug(f"开始生成站点 {site_id} 的分析工作流")
                        analyzer_success = generator.generate_analyzer_workflow(site_id)
                    
                    self.logger.debug(f"站点 {site_id} 工作流生成结果: 爬虫={crawler_success}, 分析={analyzer_success}")
                    return crawler_success and analyzer_success
                else:
                    # 生成所有工作流
                    self.logger.debug("渲染决策: 生成所有工作流")
                    if engine_type.lower() == 'jinja2':
                        self.logger.debug("渲染器选择: 使用 Jinja2 渲染器生成所有工作流")
                        self.logger.debug("开始生成通用工作流")
                        common_success = generator.generate_common_workflows()
                        self.logger.debug("开始生成站点工作流")
                        site_success = generator.generate_all_workflows()
                        self.logger.debug(f"工作流生成结果: 通用={common_success}, 站点={site_success}")
                        return common_success and site_success
                    else:
                        self.logger.debug("渲染器选择: 使用 Jsonnet 渲染器生成所有工作流")
                        self.logger.debug("开始生成所有工作流")
                        success = generator.generate_all_workflows()
                        self.logger.debug(f"工作流生成结果: {success}")
                        return success
            
            else:
                self.logger.error(f"不支持的工作流类型: {workflow_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"生成工作流失败: {e}")
            import traceback
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            return False
