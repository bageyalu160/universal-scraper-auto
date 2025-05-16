#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 步骤模型
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from .base import BaseWorkflowModel


class StepWith(BaseWorkflowModel):
    """表示步骤的with参数"""
    pass


class Step(BaseWorkflowModel):
    """表示GitHub Actions工作流中的单个步骤"""
    name: str 
    id: Optional[str] = None
    uses: Optional[str] = None
    with_params: Optional[Dict[str, Any]] = None
    run_command: Optional[str] = None
    if_condition: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    continue_on_error: Optional[bool] = None
    
    def with_id(self, id: str) -> 'Step':
        """设置步骤ID"""
        self.id = id
        return self
    
    def with_condition(self, condition: str) -> 'Step':
        """设置条件"""
        self.if_condition = condition
        return self
    
    def with_env(self, env: Dict[str, str]) -> 'Step':
        """设置环境变量"""
        self.env = env
        return self
    
    def with_continue_on_error(self, value: bool = True) -> 'Step':
        """设置continue-on-error标志"""
        self.continue_on_error = value
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """重写父类的to_dict方法，确保run_command和uses字段被正确处理"""
        result = super().to_dict()
        
        # 确保至少有一个run或uses字段
        if "run" not in result and "uses" not in result:
            raise ValueError(f"步骤 '{self.name}' 必须包含 'run' 或 'uses' 字段")
            
        return result


class CheckoutStep(Step):
    """表示检出代码的步骤"""
    
    def __init__(self, fetch_depth: int = 0):
        super().__init__(
            name="检出仓库代码",
            uses="actions/checkout@v4",
            with_params={"fetch-depth": fetch_depth}
        )


class SetupPythonStep(Step):
    """表示设置Python环境的步骤"""
    
    def __init__(self, python_version: str, enable_cache: bool = True):
        with_params = {
            "python-version": python_version
        }
        if enable_cache:
            with_params["cache"] = "pip"
            
        super().__init__(
            name="设置Python环境",
            uses="actions/setup-python@v5",
            with_params=with_params
        )


class InstallDependenciesStep(Step):
    """表示安装依赖的步骤"""
    
    def __init__(self, dependencies: str = ""):
        run_command = """
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "安装必要的依赖..."
  pip install {dependencies}
fi
""".strip().format(dependencies=dependencies)
        
        super().__init__(
            name="安装依赖",
            run_command=run_command
        )


class RunCommandStep(Step):
    """表示运行命令的步骤"""
    
    def __init__(self, name: str, commands: List[str] = None, env: Dict[str, str] = None):
        if commands is None or len(commands) == 0:
            commands = ["echo \"执行步骤: " + name + "\""]
            
        run_command = "\n".join(commands)
        
        super().__init__(
            name=name,
            run_command=run_command,
            env=env
        )


class NotificationStep(Step):
    """表示发送通知的步骤"""
    
    def __init__(self, notification_script: str, 
                 analysis_dir: str = "${{ steps.params.outputs.analysis_dir }}",
                 data_date: str = "${{ steps.params.outputs.data_date }}",
                 site_id: str = "${{ steps.params.outputs.site_id }}",
                 output_extension: str = "tsv"):
        
        if not notification_script:
            notification_script = "scripts/notify.py"
            
        commands = [
            'echo "发送分析结果通知..."',
            f'python {notification_script} --file "{analysis_dir}/analysis_{data_date}.{output_extension}" --site "{site_id}"'
        ]
        
        super().__init__(
            name="发送通知",
            if_condition="steps.run-analysis.outputs.analysis_exists == 'true'",
            run_command="\n".join(commands)
        ) 