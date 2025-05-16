#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
import yaml
import json
from datetime import datetime
import importlib
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('workflow')

def load_config(site_id):
    """加载站点配置"""
    config_path = os.path.join('config', 'sites', f'{site_id}.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_global_config():
    """加载全局配置"""
    config_path = os.path.join('config', 'settings.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_crawler(site_id, config, output_dir):
    """运行爬虫"""
    from scripts.scraper import run_scraper
    
    logger.info(f"开始运行爬虫: {site_id}")
    result = run_scraper(site_id, config, output_dir)
    return result

def run_analyzer(site_id, data_file, config, output_dir):
    """运行分析器"""
    logger.info(f"开始运行分析器: {site_id}")
    
    # 为PM001站点使用专门的分析器
    if site_id == 'pm001':
        from src.analyzers.pm001_analyzer import analyze_pm001_data
        return analyze_pm001_data(data_file, config, output_dir)
    else:
        # 对于其他站点，可以使用通用分析器 (这里简化处理)
        logger.warning(f"没有为站点 {site_id} 找到专门的分析器，跳过分析阶段")
        return {"status": "warning", "message": "未找到专门的分析器"}

def run_notifier(site_id, site_name, data_file, analysis_file, summary_file, config):
    """运行通知模块"""
    logger.info(f"开始发送通知: {site_id}")
    
    # 使用简单通知器
    from src.notifiers.simple_notifier import send_notification
    return send_notification(site_name, data_file, analysis_file, summary_file, config)

def run_workflow(site_id, output_base_dir=None):
    """运行完整工作流"""
    start_time = time.time()
    
    # 加载配置
    site_config = load_config(site_id)
    global_config = load_global_config()
    
    # 获取站点名称
    site_name = site_config.get('site', {}).get('name', site_id)
    
    # 设置输出目录
    today = datetime.now().strftime('%Y-%m-%d')
    if output_base_dir:
        output_dir = os.path.join(output_base_dir, today)
    else:
        output_dir = os.path.join('data', 'daily', today)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 运行爬虫
    logger.info(f"=== 开始爬虫阶段: {site_id} ===")
    crawler_result = run_crawler(site_id, site_config, output_dir)
    
    if crawler_result and crawler_result.get('status') == 'success':
        data_file = crawler_result.get('output_path')
        logger.info(f"爬虫成功，获取了 {crawler_result.get('count')} 条数据")
        logger.info(f"数据已保存到: {data_file}")
        
        # 设置分析输出目录
        analysis_dir = os.path.join('analysis', 'daily', today)
        os.makedirs(analysis_dir, exist_ok=True)
        
        # 运行分析器
        logger.info(f"=== 开始分析阶段: {site_id} ===")
        analysis_result = run_analyzer(site_id, data_file, global_config, analysis_dir)
        
        if analysis_result and analysis_result.get('status') in ['success', 'warning']:
            analysis_file = analysis_result.get('output_path')
            summary_file = analysis_result.get('summary_path')
            
            logger.info(f"分析成功，结果已保存到: {analysis_file}")
            
            # 运行通知模块
            logger.info(f"=== 开始通知阶段: {site_id} ===")
            notification_result = run_notifier(
                site_id, 
                site_name, 
                data_file, 
                analysis_file, 
                summary_file, 
                global_config
            )
            
            if notification_result and notification_result.get('status') == 'success':
                logger.info(f"通知发送成功")
            else:
                logger.warning(f"通知发送失败: {notification_result.get('message')}")
        else:
            logger.error(f"分析失败: {analysis_result.get('message')}")
    else:
        logger.error(f"爬虫运行失败")
    
    # 计算总耗时
    elapsed_time = time.time() - start_time
    logger.info(f"=== 工作流完成: {site_id}, 总耗时: {elapsed_time:.2f} 秒 ===")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='运行完整工作流（爬虫、分析、通知）')
    parser.add_argument('--site', required=True, help='站点ID，对应config/sites/下的配置文件名')
    parser.add_argument('--output-dir', help='可选的输出目录')
    args = parser.parse_args()
    
    # 运行工作流
    run_workflow(args.site, args.output_dir)

if __name__ == "__main__":
    main() 