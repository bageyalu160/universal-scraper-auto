#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成脚本 - Jsonnet版本
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import json

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from scripts.workflow_generator.jsonnet_generator import JsonnetWorkflowGenerator
from scripts.workflow_generator.validators import WorkflowValidator


def setup_logger(debug=False):
    """设置日志记录器"""
    logger = logging.getLogger('workflow_generator')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    
    return logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='使用Jsonnet生成GitHub Actions工作流文件')
    parser.add_argument('--site', '-s', help='指定站点ID，不指定则生成所有站点的工作流')
    parser.add_argument('--type', '-t', choices=['master', 'crawler', 'analyzer', 'dashboard', 'proxy', 'all'], 
                        default='all', help='指定要生成的工作流类型')
    parser.add_argument('--output-dir', '-o', help='指定输出目录')
    parser.add_argument('--settings', help='指定设置文件路径')
    parser.add_argument('--sites-dir', help='指定站点配置目录')
    parser.add_argument('--debug', '-d', action='store_true', help='启用调试模式，输出更详细的日志')
    parser.add_argument('--validate-only', '-v', action='store_true', 
                        help='仅验证工作流文件而不生成，需要与--file参数一起使用')
    parser.add_argument('--file', '-f', help='指定要验证的工作流文件路径，与--validate-only一起使用')
    
    args = parser.parse_args()
    
    # 设置日志记录器
    logger = setup_logger(args.debug)
    
    # 如果只是验证工作流文件，则直接验证并返回
    if args.validate_only:
        if not args.file:
            logger.error("使用--validate-only时必须指定--file参数")
            return 1
            
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"指定的文件不存在: {file_path}")
            return 1
            
        validator = WorkflowValidator(logger=logger)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            is_valid, errors, warnings = validator.validate_with_warnings(content)
            
            # 输出警告信息（如果有）
            if warnings:
                logger.warning(f"工作流文件验证警告: {file_path}")
                for warning in warnings:
                    logger.warning(f"  - {warning}")
            
            # 如果有严重错误，返回错误代码
            if not is_valid:
                logger.error(f"工作流文件验证失败: {file_path}")
                for error in errors:
                    logger.error(f"  - {error}")
                return 1
            else:
                # 没有严重错误，只有警告或没有问题
                logger.info(f"工作流文件验证通过: {file_path}")
                return 0
                
        except Exception as e:
            logger.error(f"验证过程中发生错误: {e}")
            return 1
    
    # 创建工作流生成器
    generator = JsonnetWorkflowGenerator(
        settings_path=args.settings,
        sites_dir=args.sites_dir,
        output_dir=args.output_dir,
        logger=logger,
        validate_output=True  # 启用对生成的工作流文件进行验证
    )
    
    # 根据参数生成工作流
    if args.type == 'master':
        success = generator.generate_master_workflow()
        logger.info(f"主调度工作流生成{'成功' if success else '失败'}")
    elif args.type == 'dashboard':
        success = generator.generate_dashboard_workflow()
        logger.info(f"仪表盘更新工作流生成{'成功' if success else '失败'}")
    elif args.type == 'proxy':
        success = generator.generate_proxy_manager_workflow()
        logger.info(f"代理池管理工作流生成{'成功' if success else '失败'}")
    elif args.type == 'crawler':
        if args.site:
            success = generator.generate_crawler_workflow(args.site)
            logger.info(f"爬虫工作流生成{'成功' if success else '失败'}: {args.site}")
        else:
            logger.error("生成爬虫工作流需要指定站点ID")
            return 1
    elif args.type == 'analyzer':
        if args.site:
            success = generator.generate_analyzer_workflow(args.site)
            logger.info(f"分析工作流生成{'成功' if success else '失败'}: {args.site}")
        else:
            logger.error("生成分析工作流需要指定站点ID")
            return 1
    else:  # all
        if args.site:
            # 为指定站点生成爬虫和分析工作流
            crawler_success = generator.generate_crawler_workflow(args.site)
            analyzer_success = generator.generate_analyzer_workflow(args.site)
            success = crawler_success and analyzer_success
            logger.info(f"站点工作流生成{'成功' if success else '部分失败'}: {args.site}")
        else:
            # 生成所有工作流
            success = generator.generate_all_workflows()
            logger.info(f"所有工作流生成{'成功' if success else '部分失败'}")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
