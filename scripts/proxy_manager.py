#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理池管理脚本

该脚本用于管理代理池，支持以下功能：
- 更新代理池（从各种代理源获取新代理）
- 验证现有代理的可用性
- 清理失效代理
- 完全重建代理池
- 尝试恢复失效代理

可以通过GitHub Actions工作流或命令行手动运行
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# 添加项目根目录到sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

# 导入代理池管理类
from src.utils.proxy_pool import ProxyPool

# 设置日志
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/proxy_pool.log')
    ]
)

logger = logging.getLogger('proxy_manager')

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="代理池管理工具")
    parser.add_argument("--action", type=str, required=True, 
                        choices=["update", "validate", "clear", "rebuild", "recover"],
                        help="操作类型：更新、验证、清理、重建或恢复代理池")
    parser.add_argument("--source", type=str, default="all",
                        choices=["all", "api", "file"],
                        help="代理源：全部、API或文件")
    parser.add_argument("--config", type=str, 
                        help="配置文件路径，默认使用系统配置")
    parser.add_argument("--test-url", type=str, 
                        help="用于测试代理的URL")
    parser.add_argument("--output", type=str, 
                        help="输出状态文件路径")
    parser.add_argument("--threshold", type=int, default=5,
                        help="触发恢复的代理数量阈值")
    
    return parser.parse_args()

def ensure_directories():
    """确保必要的目录存在"""
    Path("data/proxies").mkdir(parents=True, exist_ok=True)
    Path("status/proxies").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

def save_status_file(result: Dict[str, Any], proxy_pool: ProxyPool, output_path: Optional[str] = None):
    """
    保存状态文件
    
    Args:
        result: 操作结果
        proxy_pool: 代理池实例
        output_path: 输出文件路径
    """
    # 默认状态文件路径
    status_file = output_path or "status/proxies/pool_status.json"
    
    # 创建状态对象
    status = {
        "last_operation": result,
        "valid_proxies": [str(p) for p in proxy_pool.proxies],
        "failed_proxies": list(proxy_pool.failed_proxies.keys()),
        "stats": {
            "valid_count": len(proxy_pool.proxies),
            "failed_count": len(proxy_pool.failed_proxies),
            "last_update": proxy_pool.last_update
        }
    }
    
    # 写入状态文件
    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
        
    logger.info(f"状态文件已保存到: {status_file}")

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 创建必要的目录
    ensure_directories()
    
    # 初始化代理池
    logger.info(f"初始化代理池 (配置: {args.config or '默认'})")
    proxy_pool = ProxyPool(args.config)
    
    # 如果指定了阈值，更新代理池的阈值
    if args.threshold:
        proxy_pool.recovery_threshold = args.threshold
    
    # 记录起始时间
    start_time = time.time()
    
    # 使用集成函数执行操作
    logger.info(f"执行操作: {args.action} (源: {args.source})")
    result = proxy_pool.integrate_with_workflow(action=args.action, source_type=args.source)
    
    # 保存状态文件
    save_status_file(result, proxy_pool, args.output)
    
    # 输出结果摘要
    if result["status"] == "success":
        elapsed_time = result.get("elapsed_time", time.time() - start_time)
        
        if args.action == "update":
            logger.info(f"代理池更新成功，当前有 {result['valid_count']} 个有效代理，"
                       f"{result['failed_count']} 个失效代理，耗时 {elapsed_time:.2f} 秒")
        
        elif args.action == "validate":
            logger.info(f"代理验证完成，验证前: {result['before_count']} 个代理，"
                       f"验证后: {result['after_count']} 个可用代理，"
                       f"失效率: {result['fail_rate']:.2f}%，耗时 {elapsed_time:.2f} 秒")
        
        elif args.action == "clear":
            logger.info(f"已清理 {result['failed_cleared']} 个失效代理")
        
        elif args.action == "rebuild":
            logger.info(f"代理池重建完成，当前有 {result['valid_count']} 个有效代理，"
                       f"耗时 {elapsed_time:.2f} 秒")
        
        elif args.action == "recover":
            logger.info(f"代理恢复完成，恢复前: {result['before_count']} 个代理，"
                       f"恢复后: {result['after_count']} 个代理，"
                       f"成功恢复: {result['recovered_count']} 个，"
                       f"耗时 {elapsed_time:.2f} 秒")
    else:
        logger.error(f"操作失败: {result.get('error', '未知错误')}")
        sys.exit(1)

if __name__ == "__main__":
    main() 