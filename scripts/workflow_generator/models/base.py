#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 基础模型
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class BaseWorkflowModel(BaseModel):
    """所有工作流模型的基类"""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示形式，用于YAML序列化"""
        result = {}
        for field_name, field_value in self.model_dump(exclude_none=True).items():
            # 转换snake_case为适当的格式
            if field_name == "if_condition":
                key = "if"
            elif field_name == "run_command":
                key = "run"
            elif field_name == "with_params":
                key = "with"
            elif field_name == "runs_on":
                key = "runs-on"
            elif field_name == "continue_on_error":
                key = "continue-on-error"
            elif field_name.endswith("_params"):
                key = field_name[:-7]  # 去掉_params后缀
            else:
                key = field_name
                
            # 递归处理子模型
            if isinstance(field_value, BaseWorkflowModel):
                result[key] = field_value.to_dict()
            elif isinstance(field_value, list) and all(isinstance(item, BaseWorkflowModel) for item in field_value):
                result[key] = [item.to_dict() for item in field_value]
            else:
                result[key] = field_value
                
        return result 