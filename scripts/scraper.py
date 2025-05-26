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

def run_scraper(site_id, config, output_dir=None, **kwargs):
    """根据配置运行爬虫，支持自动透传额外参数"""
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
            
            # 运行爬虫，自动透传kwargs
            logger.info(f"使用自定义模块 {module_path}.{function_name} 运行爬虫 (自动透传参数)")
            result = scrape_function(config, output_dir, **kwargs)
            
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
    parser.add_argument('--date', type=str, help='数据日期')
    parser.add_argument('--output', type=str, help='输出文件路径')
    parser.add_argument('--status', type=str, help='状态文件路径')
    parser.add_argument('--log-file', type=str, help='日志文件路径')
    args, unknown = parser.parse_known_args()

    # 自动解析未知参数为字典
    def parse_unknown_args(unknown):
        d = {}
        key = None
        for item in unknown:
            if item.startswith('--'):
                key = item.lstrip('-').replace('-', '_')
                d[key] = True  # 先设为True，后面如果有值会覆盖
            else:
                if key:
                    d[key] = item
                    key = None
        return d
    extra_args = parse_unknown_args(unknown)

    # 设置输出目录
    output_dir = args.output_dir
    if not output_dir:
        today = args.date if args.date else datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.join('data', 'daily', today)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载配置
    config = load_config(args.site, args.config)
    
    # 运行爬虫（自动透传extra_args）
    logger.info(f"开始运行爬虫: {args.site}")
    result = run_scraper(args.site, config, output_dir, **extra_args)
    
    # 处理输出文件、状态文件、日志文件参数（如有）
    if args.output and result and result.get('output_path'):
        import shutil
        try:
            shutil.copy(result['output_path'], args.output)
            logger.info(f"已将输出文件保存为: {args.output}")
        except Exception as e:
            logger.warning(f"输出文件保存失败: {e}")
    if args.status and result:
        try:
            import json
            with open(args.status, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"已将状态信息保存为: {args.status}")
        except Exception as e:
            logger.warning(f"状态文件保存失败: {e}")
    if args.log_file:
        try:
            fh = logging.FileHandler(args.log_file, encoding='utf-8')
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.info(f"日志已追加到: {args.log_file}")
        except Exception as e:
            logger.warning(f"日志文件追加失败: {e}")

    if result and result.get('status') == 'success':
        logger.info(f"爬虫运行成功，获取了 {result.get('count')} 条数据")
        return 0
    else:
        logger.error("爬虫运行失败")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 