#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 工作流模型
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from .base import BaseWorkflowModel
from .steps import Step


class Trigger(BaseWorkflowModel):
    """表示工作流触发器"""
    pass


class WorkflowDispatchTrigger(Trigger):
    """表示手动触发工作流"""
    inputs: Optional[Dict[str, Any]] = None


class ScheduleTrigger(Trigger):
    """表示定时触发工作流"""
    cron: str


class RepositoryDispatchTrigger(Trigger):
    """表示仓库事件触发工作流"""
    types: List[str]


class Job(BaseWorkflowModel):
    """表示工作流中的作业"""
    name: str
    runs_on: str = "ubuntu-latest"
    steps: List[Step]
    needs: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """重写父类的to_dict方法，确保runs_on字段被正确设置"""
        result = super().to_dict()
        
        # 确保runs_on字段有值
        if "runs_on" in result and "runs-on" not in result:
            result["runs-on"] = result.pop("runs_on")
        elif "runs-on" not in result:
            result["runs-on"] = "ubuntu-latest"
            
        return result


class Workflow(BaseWorkflowModel):
    """表示完整的GitHub Actions工作流"""
    name: str
    on: Dict[str, Any]
    env: Optional[Dict[str, str]] = None
    permissions: Optional[Dict[str, str]] = None
    jobs: Dict[str, Job]
    
    @classmethod
    def create_basic(cls, name: str) -> 'Workflow':
        """创建一个基本的工作流"""
        return cls(
            name=name,
            on={},
            jobs={}
        )
    
    def add_manual_trigger(self, inputs: Dict[str, Any] = None) -> 'Workflow':
        """添加手动触发"""
        self.on["workflow_dispatch"] = {"inputs": inputs} if inputs else {}
        return self
    
    def add_schedule_trigger(self, cron: str) -> 'Workflow':
        """添加定时触发"""
        # 确保on字典中有schedule键
        if "schedule" not in self.on:
            self.on["schedule"] = []
        
        # 添加cron表达式
        self.on["schedule"].append({"cron": cron})
        return self
    
    def add_repository_dispatch_trigger(self, types: List[str]) -> 'Workflow':
        """添加仓库事件触发"""
        self.on["repository_dispatch"] = {"types": types}
        return self
    
    def set_permissions(self, permissions: Dict[str, str]) -> 'Workflow':
        """设置权限"""
        self.permissions = permissions
        return self
    
    def set_env(self, env: Dict[str, str]) -> 'Workflow':
        """设置环境变量"""
        self.env = env
        return self
    
    def add_job(self, job_id: str, job: Job) -> 'Workflow':
        """添加作业"""
        self.jobs[job_id] = job
        return self 