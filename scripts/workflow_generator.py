#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 命令行入口点
"""

import os
import sys
import argparse
import logging
from pathlib import Path

from workflow_generator import WorkflowGenerator


def setup_logging(debug=False):
    """设置日志记录"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('workflow_generator')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='工作流生成器 - 生成GitHub Actions工作流')
    parser.add_argument('--settings', help='设置文件路径')
    parser.add_argument('--sites-dir', help='站点配置目录')
    parser.add_argument('--output-dir', help='输出目录')
    parser.add_argument('--site', help='指定站点ID，多个站点用逗号分隔')
    parser.add_argument('--all', action='store_true', help='生成所有站点的工作流')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logging(args.debug)
    
    try:
        # 创建工作流生成器实例
        generator = WorkflowGenerator(
            settings_path=args.settings,
            sites_dir=args.sites_dir,
            output_dir=args.output_dir,
            logger=logger
        )
        
        # 根据参数执行不同操作
        if args.all:
            if generator.generate_all_workflows():
                logger.info("所有工作流生成成功")
                return 0
            else:
                logger.error("部分或全部工作流生成失败")
                return 1
        elif args.site:
            if generator.update_workflows(args.site):
                logger.info(f"指定站点的工作流更新成功: {args.site}")
                return 0
            else:
                logger.error(f"指定站点的工作流更新失败: {args.site}")
                return 1
        else:
            logger.warning("未指定操作，请使用--all或--site参数")
            parser.print_help()
            return 1
    except Exception as e:
        logger.exception(f"工作流生成过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 