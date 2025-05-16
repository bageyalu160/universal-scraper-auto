#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 策略基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..models import Workflow


class WorkflowStrategy(ABC):
    """工作流策略基类"""
    
    @abstractmethod
    def create_workflow(self, site_config: Dict[str, Any], global_config: Dict[str, Any]) -> Workflow:
        """创建工作流"""
        pass


class WorkflowFactory:
    """工作流工厂，用于创建不同类型的工作流"""
    
    def __init__(self):
        """初始化工厂"""
        self.strategies = {}
    
    def register_strategy(self, workflow_type: str, strategy: WorkflowStrategy) -> None:
        """注册策略"""
        self.strategies[workflow_type] = strategy
    
    def get_strategy(self, workflow_type: str) -> WorkflowStrategy:
        """获取指定类型的策略"""
        if workflow_type not in self.strategies:
            raise ValueError(f"不支持的工作流类型: {workflow_type}")
        return self.strategies[workflow_type]
    
    def create_workflow(self, workflow_type: str, site_config: Dict[str, Any], global_config: Dict[str, Any]) -> Workflow:
        """创建工作流"""
        strategy = self.get_strategy(workflow_type)
        return strategy.create_workflow(site_config, global_config) 