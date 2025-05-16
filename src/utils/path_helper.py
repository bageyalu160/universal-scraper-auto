#!/usr/bin/env python3
"""
路径辅助工具
提供目录和文件路径处理功能
"""

import os
import shutil
from datetime import datetime
from typing import Optional, List

def ensure_dir(directory: str) -> str:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        str: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def get_data_dir(site_id: Optional[str] = None, date_str: Optional[str] = None) -> str:
    """
    获取数据目录路径
    
    Args:
        site_id: 站点ID，可选
        date_str: 日期字符串，格式为YYYY-MM-DD，如果为None则使用当前日期
        
    Returns:
        str: 数据目录路径
    """
    # 基础数据目录
    data_dir = 'data'
    
    # 如果提供了日期，则添加日期子目录
    if date_str:
        data_dir = os.path.join(data_dir, 'daily', date_str)
    else:
        data_dir = os.path.join(data_dir, 'daily', datetime.now().strftime('%Y-%m-%d'))
    
    # 如果提供了站点ID，则添加站点子目录
    if site_id:
        data_dir = os.path.join(data_dir, site_id)
    
    # 确保目录存在
    ensure_dir(data_dir)
    
    return data_dir

def get_analysis_dir(site_id: Optional[str] = None, date_str: Optional[str] = None) -> str:
    """
    获取分析结果目录路径
    
    Args:
        site_id: 站点ID，可选
        date_str: 日期字符串，格式为YYYY-MM-DD，如果为None则使用当前日期
        
    Returns:
        str: 分析结果目录路径
    """
    # 基础分析目录
    analysis_dir = 'analysis'
    
    # 如果提供了日期，则添加日期子目录
    if date_str:
        analysis_dir = os.path.join(analysis_dir, 'daily', date_str)
    else:
        analysis_dir = os.path.join(analysis_dir, 'daily', datetime.now().strftime('%Y-%m-%d'))
    
    # 如果提供了站点ID，则添加站点子目录
    if site_id:
        analysis_dir = os.path.join(analysis_dir, site_id)
    
    # 确保目录存在
    ensure_dir(analysis_dir)
    
    return analysis_dir

def clean_old_data(base_dir: str, keep_days: int = 30) -> List[str]:
    """
    清理旧数据
    
    Args:
        base_dir: 基础目录
        keep_days: 保留的天数
        
    Returns:
        List[str]: 已删除的目录列表
    """
    daily_dir = os.path.join(base_dir, 'daily')
    if not os.path.exists(daily_dir):
        return []
    
    # 获取当前日期
    today = datetime.now().date()
    
    # 查找所有日期目录
    removed_dirs = []
    for date_str in os.listdir(daily_dir):
        try:
            # 尝试解析日期
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # 计算日期差
            days_diff = (today - date).days
            
            # 如果超过保留天数，则删除
            if days_diff > keep_days:
                dir_path = os.path.join(daily_dir, date_str)
                shutil.rmtree(dir_path)
                removed_dirs.append(dir_path)
        except ValueError:
            # 忽略非日期格式的目录
            continue
    
    return removed_dirs 