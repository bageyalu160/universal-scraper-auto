#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import yaml
import importlib
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('universal_scraper')

def load_config(site_id, config_file=None):
    """加载站点配置文件"""
    if config_file:
        config_path = Path(config_file)
    else:
        config_path = Path('config') / 'sites' / f'{site_id}.yaml'
    
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config

def run_scraper(site_id, config, output_dir=None):
    """根据配置运行爬虫"""
    scraping = config.get('scraping', {})
    engine = scraping.get('engine', 'custom')
    
    if engine == 'custom':
        # 获取自定义模块和函数
        module_path = scraping.get('custom_module')
        function_name = scraping.get('custom_function')
        
        if not module_path or not function_name:
            logger.error("配置缺少custom_module或custom_function")
            return False
        
        try:
            # 导入模块
            module = importlib.import_module(module_path)
            scrape_function = getattr(module, function_name)
            
            # 运行爬虫
            logger.info(f"使用自定义模块 {module_path}.{function_name} 运行爬虫")
            result = scrape_function(config, output_dir)
            
            # 复制结果文件到当前目录（如果需要）
            output_config = config.get('output', {})
            output_filename = output_config.get('filename', f'{site_id}_data.json')
            if output_dir:
                source_path = Path(output_dir) / output_filename
                if source_path.exists():
                    import shutil
                    shutil.copy(source_path, output_filename)
                    logger.info(f"已将结果文件复制到当前目录: {output_filename}")
            
            return result
        except ImportError:
            logger.error(f"无法导入模块: {module_path}")
            return False
        except AttributeError:
            logger.error(f"模块 {module_path} 中没有函数 {function_name}")
            return False
        except Exception as e:
            logger.exception(f"运行爬虫时出错: {e}")
            return False
    else:
        logger.error(f"不支持的爬虫引擎: {engine}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='通用网页爬虫框架')
    parser.add_argument('--site', required=True, help='站点ID，对应config/sites/下的配置文件名')
    parser.add_argument('--config', help='可选的配置文件路径')
    parser.add_argument('--output-dir', help='可选的输出目录')
    args = parser.parse_args()
    
    # 设置输出目录
    output_dir = args.output_dir
    if not output_dir:
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.join('data', 'daily', today)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载配置
    config = load_config(args.site, args.config)
    
    # 运行爬虫
    logger.info(f"开始运行爬虫: {args.site}")
    result = run_scraper(args.site, config, output_dir)
    
    if result and result.get('status') == 'success':
        logger.info(f"爬虫运行成功，获取了 {result.get('count')} 条数据")
        return 0
    else:
        logger.error("爬虫运行失败")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 