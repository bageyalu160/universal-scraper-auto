#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simple_notifier')

def send_notification(site_name, data_file, analysis_file, summary_file, config=None):
    """
    发送简单的通知
    
    Args:
        site_name: 站点名称
        data_file: 数据文件路径
        analysis_file: 分析文件路径
        summary_file: 摘要文件路径
        config: 配置字典
        
    Returns:
        dict: 包含通知结果的字典
    """
    logger.info(f"准备发送 {site_name} 的通知")
    
    # 读取摘要信息
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
    except Exception as e:
        logger.error(f"读取摘要文件时出错: {e}")
        summary = {}
    
    # 生成通知内容
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 提取日期范围
    date_range_start = now
    date_range_end = now
    
    # 提取总记录数
    total_records = summary.get('total_records', 0)
    
    # 生成摘要内容
    buy_count = summary.get('buy_count', 0)
    sell_count = summary.get('sell_count', 0)
    other_count = summary.get('other_count', 0)
    
    content = f"""
===== {site_name}数据更新通知 =====

**数据概览**:
- 总记录数: {total_records}
- 日期范围: {date_range_start} 至 {date_range_end}

**分析摘要**:
- 收购帖子: {buy_count}
- 出售帖子: {sell_count}
- 其他帖子: {other_count}

**原始数据**: {data_file}
**分析结果**: {analysis_file}
"""
    
    # 在控制台输出
    print("\n" + "="*60)
    print(content)
    print("="*60 + "\n")
    
    # 模拟发送到通知渠道
    logger.info("通知已发送到控制台")
    
    # 保存通知内容到文件（用于查阅）
    notification_dir = "status/notifications"
    os.makedirs(notification_dir, exist_ok=True)
    
    notification_file = os.path.join(notification_dir, f"{site_name}_notification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    with open(notification_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"通知内容已保存到 {notification_file}")
    
    return {
        "status": "success",
        "message": "通知已发送",
        "notification_file": notification_file
    }

if __name__ == "__main__":
    """直接运行此脚本的测试代码"""
    import argparse
    
    parser = argparse.ArgumentParser(description='发送简单通知')
    parser.add_argument('--site', required=True, help='站点名称')
    parser.add_argument('--data-file', required=True, help='数据文件路径')
    parser.add_argument('--analysis-file', required=True, help='分析文件路径')
    parser.add_argument('--summary-file', required=True, help='摘要文件路径')
    args = parser.parse_args()
    
    result = send_notification(
        args.site,
        args.data_file,
        args.analysis_file,
        args.summary_file
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2)) 