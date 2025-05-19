#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 命令行入口点
使用workflow_generator包中的WorkflowGenerator类来处理工作流生成逻辑
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import yaml

# 导入工作流生成器类
from workflow_generator import WorkflowGenerator

# 全局常量
CONFIG_DIR = Path("config")
SITES_DIR = CONFIG_DIR / "sites"
WORKFLOW_DIR = CONFIG_DIR / "workflow"
TEMPLATES_DIR = WORKFLOW_DIR / "templates"  # 模板子目录
GITHUB_DIR = Path(".github")
GITHUB_WORKFLOW_DIR = GITHUB_DIR / "workflows"

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
    parser.add_argument('--type', choices=["crawler", "analyzer", "both", "common", "all"], default="both",
                      help="要生成的工作流类型 (crawler/analyzer/both/common/all)")
    parser.add_argument('--common', action='store_true', help='生成通用工作流（主工作流和仪表盘更新工作流）')
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logging(args.debug)
    
    try:
        # 设置参数
        settings_path = args.settings or CONFIG_DIR / "settings.yaml"
        sites_dir = args.sites_dir or SITES_DIR
        output_dir = args.output_dir or GITHUB_WORKFLOW_DIR
        
        # 实例化工作流生成器
        generator = WorkflowGenerator(
            settings_path=settings_path,
            sites_dir=sites_dir,
            output_dir=output_dir,
            logger=logger
        )
        
        # 检查是否要生成通用工作流
        if args.type in ["common", "all"] or args.common:
            logger.info("开始生成通用工作流文件...")
            if generator.generate_common_workflows():
                logger.info("成功生成通用工作流文件")
            else:
                logger.error("生成通用工作流文件时发生错误")
                if args.type == "common":  # 如果只是生成通用工作流，则返回错误代码
                    return 1
        
        # 如果只要求生成通用工作流，则不继续处理站点特定工作流
        if args.type == "common":
            return 0
        
        # 确定要处理的站点
        site_ids = []
        if args.all or args.type == "all":
            # 获取所有站点配置文件
            site_files = list(Path(sites_dir).glob("*.yaml"))
            site_ids = [site_file.stem for site_file in site_files if site_file.stem != "example"]
            
            if not site_ids:
                logger.error("错误: 未找到任何站点配置文件")
                return 1
        elif args.site:
            if ',' in args.site:
                site_ids = [site.strip() for site in args.site.split(',')]
            else:
                site_ids = [args.site]
        else:
            if args.type != "common":  # 如果不是只生成通用工作流，则需要指定站点
                logger.error("错误: 生成站点工作流时必须指定 --site 或 --all 参数")
                return 1
        
        # 生成站点特定工作流文件
        if args.type in ["both", "all"] and site_ids:
            success_count = 0
            total_count = len(site_ids) * 2
            
            for site_id in site_ids:
                # 生成爬虫工作流
                if generator.generate_workflow(site_id, "crawler"):
                    success_count += 1
                
                # 生成分析工作流
                if generator.generate_workflow(site_id, "analyzer"):
                    success_count += 1
                    
            logger.info(f"完成: 成功生成 {success_count}/{total_count} 个站点工作流文件")
            return 0 if success_count == total_count else 1
        elif args.type == "crawler" and site_ids:
            success_count = 0
            total_count = len(site_ids)
            
            for site_id in site_ids:
                if generator.generate_workflow(site_id, "crawler"):
                    success_count += 1
                    
            logger.info(f"完成: 成功生成 {success_count}/{total_count} 个爬虫工作流文件")
            return 0 if success_count == total_count else 1
        elif args.type == "analyzer" and site_ids:
            success_count = 0
            total_count = len(site_ids)
            
            for site_id in site_ids:
                if generator.generate_workflow(site_id, "analyzer"):
                    success_count += 1
                    
            logger.info(f"完成: 成功生成 {success_count}/{total_count} 个分析工作流文件")
            return 0 if success_count == total_count else 1
        
        return 0
    
    except Exception as e:
        logger.exception(f"工作流生成过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 