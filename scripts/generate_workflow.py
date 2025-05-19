#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工作流生成器命令行工具

该脚本是对WorkflowGenerator类的命令行接口封装，
用于从命令行生成GitHub Actions工作流文件。
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# 设置项目根目录路径
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

# 导入工作流生成器
from scripts.workflow_generator.generator import WorkflowGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('workflow_generator_cli')


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(description="工作流生成器")
    parser.add_argument("--site", type=str, help="站点ID，不指定则生成所有站点的工作流")
    parser.add_argument("--master", action="store_true", help="是否生成主调度工作流")
    parser.add_argument("--proxy", action="store_true", help="是否生成代理池管理工作流")
    parser.add_argument("--dashboard", action="store_true", help="是否生成仪表盘更新工作流")
    parser.add_argument("--all", action="store_true", help="生成所有工作流")
    
    args = parser.parse_args()
    
    try:
        # 创建工作流生成器实例
        generator = WorkflowGenerator(logger=logger)
        
        # 确保输出目录存在
        os.makedirs(generator.output_dir, exist_ok=True)
        
        if args.all or (args.master and args.proxy and args.dashboard):
            # 生成所有通用工作流
            generator.generate_common_workflows()
        else:
            # 按需生成特定工作流
            if args.master:
                generator.generate_master_workflow()
            
            if args.proxy:
                generator.generate_proxy_manager_workflow()
                
            if args.dashboard:
                generator.generate_dashboard_workflow()
        
        if args.site:
            # 生成指定站点的工作流
            if "," in args.site:
                # 多个站点
                sites = args.site.split(",")
                for site_id in sites:
                    generator.generate_crawler_workflow_direct(site_id.strip())
            else:
                # 单个站点
                generator.generate_crawler_workflow_direct(args.site)
        elif args.all or not (args.master or args.proxy or args.dashboard):
            # 生成所有站点的工作流
            generator.generate_all_workflows()
        
        logger.info("工作流生成完成")
        return 0
    except Exception as e:
        logger.exception(f"生成工作流时出错: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 