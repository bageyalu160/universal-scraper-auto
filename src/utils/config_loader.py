#!/usr/bin/env python3
"""
配置加载工具
提供加载站点配置文件和全局设置的功能
"""

import os
import yaml
from typing import Dict, Any, Optional

def load_site_config(site_id: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载站点配置
    
    Args:
        site_id: 站点ID
        config_path: 配置文件路径，如果为None，则使用默认路径
        
    Returns:
        Dict: 站点配置字典
    
    Raises:
        FileNotFoundError: 配置文件不存在时抛出
        ValueError: 配置文件格式错误时抛出
    """
    # 确定配置文件路径
    if config_path is None:
        config_path = os.path.join('config', 'sites', f'{site_id}.yaml')
    
    # 检查文件是否存在
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"站点配置文件不存在: {config_path}")
    
    # 加载配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件格式错误: {str(e)}")

def load_global_settings(settings_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载全局设置
    
    Args:
        settings_path: 设置文件路径，如果为None，则使用默认路径
        
    Returns:
        Dict: 全局设置字典
    
    Raises:
        FileNotFoundError: 设置文件不存在时抛出
        ValueError: 设置文件格式错误时抛出
    """
    # 确定设置文件路径
    if settings_path is None:
        settings_path = os.path.join('config', 'settings.yaml')
    
    # 检查文件是否存在
    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"全局设置文件不存在: {settings_path}")
    
    # 加载设置
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)
        return settings
    except yaml.YAMLError as e:
        raise ValueError(f"设置文件格式错误: {str(e)}")

def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并配置
    
    Args:
        base_config: 基础配置
        override_config: 覆盖配置
        
    Returns:
        Dict: 合并后的配置
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            # 递归合并嵌套字典
            result[key] = merge_configs(result[key], value)
        else:
            # 直接覆盖值
            result[key] = value
    
    return result 