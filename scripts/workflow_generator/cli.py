#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 命令行接口
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# 将父目录添加到导入路径
parent_dir = Path(__file__).parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from utils.dependencies import setup_dependencies
from generator import WorkflowGenerator


def setup_logging(verbose=False):
    """
    设置日志记录
    
    Args:
        verbose: 是否启用详细日志
        
    Returns:
        日志记录器
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return logging.getLogger('workflow_generator')


def parse_args():
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="工作流生成器 - 生成GitHub Actions工作流文件"
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 生成特定工作流命令
    generate_parser = subparsers.add_parser('generate', help='生成工作流')
    generate_parser.add_argument(
        'site_id', 
        help='站点ID'
    )
    generate_parser.add_argument(
        'workflow_type', 
        choices=['crawler', 'analyzer'], 
        help='工作流类型'
    )
    
    # 生成所有工作流命令
    generate_all_parser = subparsers.add_parser('generate-all', help='生成所有工作流')
    
    # 更新工作流命令
    update_parser = subparsers.add_parser('update', help='更新工作流')
    update_parser.add_argument(
        '--sites', 
        help='要更新的站点ID列表，逗号分隔'
    )
    
    # 生成通用工作流命令
    common_parser = subparsers.add_parser('generate-common', help='生成通用工作流')
    
    # 安装依赖项命令
    setup_parser = subparsers.add_parser('setup', help='安装并设置依赖项')
    
    # 全局选项
    parser.add_argument(
        '--settings', 
        help='设置文件路径'
    )
    parser.add_argument(
        '--sites-dir', 
        help='站点配置目录'
    )
    parser.add_argument(
        '--output-dir', 
        help='输出目录'
    )
    parser.add_argument(
        '-v', '--verbose', 
        action='store_true', 
        help='启用详细日志'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志记录
    logger = setup_logging(args.verbose)
    
    # 检查命令
    if args.command == 'setup':
        # 设置依赖项
        return 0 if setup_dependencies(logger) else 1
    
    # 初始化生成器
    generator = WorkflowGenerator(
        settings_path=args.settings,
        sites_dir=args.sites_dir,
        output_dir=args.output_dir,
        logger=logger
    )
    
    # 执行命令
    if args.command == 'generate':
        success = generator.generate_workflow(args.site_id, args.workflow_type)
        return 0 if success else 1
    
    elif args.command == 'generate-all':
        success = generator.generate_all_workflows()
        return 0 if success else 1
    
    elif args.command == 'update':
        success = generator.update_workflows(args.sites)
        return 0 if success else 1
    
    elif args.command == 'generate-common':
        success = generator.generate_common_workflows()
        return 0 if success else 1
    
    else:
        # 如果没有指定命令，显示帮助
        print("错误: 未指定命令\n")
        parse_args(['--help'])
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1) 