#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成脚本 - 双引擎版本（支持 Jinja2 和 Jsonnet）
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from scripts.workflow_generator.engine_factory import WorkflowEngineFactory


def setup_logger():
    """设置日志记录器"""
    logger = logging.getLogger('workflow_generator')
    logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    
    return logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成GitHub Actions工作流文件（支持Jinja2和Jsonnet引擎）')
    parser.add_argument('--site', '-s', help='指定站点ID，不指定则生成所有站点的工作流')
    parser.add_argument('--type', '-t', choices=['master', 'crawler', 'analyzer', 'dashboard', 'proxy_pool', 'all'], 
                        default='all', help='指定要生成的工作流类型')
    parser.add_argument('--engine', '-e', choices=['jinja2', 'jsonnet'], 
                        help='指定使用的模板引擎（默认使用设置文件中的配置）')
    parser.add_argument('--output-dir', '-o', help='指定输出目录')
    parser.add_argument('--settings', help='指定设置文件路径')
    parser.add_argument('--sites-dir', help='指定站点配置目录')
    parser.add_argument('--force-engine', '-f', action='store_true', 
                        help='强制使用指定的引擎，即使设置文件中配置不允许覆盖默认引擎')
    
    args = parser.parse_args()
    
    # 设置日志记录器
    logger = setup_logger()
    
    # 创建工作流引擎工厂
    factory = WorkflowEngineFactory(
        settings_path=args.settings,
        sites_dir=args.sites_dir,
        output_dir=args.output_dir,
        logger=logger
    )
    
    # 获取默认引擎信息
    default_engine = factory.default_engine
    logger.info(f"设置文件中的默认引擎: {default_engine}")
    
    # 如果指定了强制使用引擎选项，则修改设置
    if args.force_engine and args.engine:
        factory.allow_override = True
        logger.info(f"强制使用指定引擎: {args.engine}")
    
    # 根据参数生成工作流
    success = factory.generate_workflow(
        engine_type=args.engine,
        workflow_type=args.type,
        site_id=args.site
    )
    
    # 获取实际使用的引擎
    actual_engine = args.engine if args.engine and (factory.allow_override or args.engine == factory.default_engine) else factory.default_engine
    
    if success:
        logger.info(f"使用 {actual_engine} 引擎生成工作流成功")
    else:
        logger.error(f"使用 {actual_engine} 引擎生成工作流失败")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
