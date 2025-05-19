#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 依赖项设置脚本
"""

import os
import sys
import logging
from pathlib import Path

# 将父目录添加到导入路径
parent_dir = Path(__file__).parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from utils.dependencies import setup_dependencies


def main():
    """设置工作流生成器依赖项"""
    # 设置日志记录
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('workflow_generator')
    
    # 打印欢迎信息
    print("="*80)
    print(" 工作流生成器依赖项设置 ".center(80, "="))
    print("="*80)
    
    # 设置依赖项
    success = setup_dependencies(logger)
    
    if success:
        print("\n✅ 所有依赖项已成功设置\n")
    else:
        print("\n⚠️ 部分依赖项设置失败，请检查日志并手动解决问题\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 