#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新生成所有工作流文件，修复格式问题
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径，以便导入工作流生成器模块
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from scripts.workflow_generator.generator import WorkflowGenerator


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger('regenerate_workflows')


def main():
    """主函数"""
    logger = setup_logging()
    logger.info("开始重新生成工作流文件...")
    
    # 初始化工作流生成器
    generator = WorkflowGenerator(logger=logger)
    
    # 重新生成所有工作流
    success = generator.generate_all_workflows()
    
    if success:
        logger.info("成功重新生成所有工作流文件！")
    else:
        logger.error("部分或全部工作流生成失败！")
        sys.exit(1)


if __name__ == "__main__":
    main() 