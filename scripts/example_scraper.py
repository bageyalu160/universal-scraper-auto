#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
示例爬虫脚本
演示如何使用重构后的PlaywrightScraper和Pydantic配置模型
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime

# 导入配置模型
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_models import load_config
# 导入爬虫类
from scripts.playwright_scraper import PlaywrightScraper

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('example_scraper')

async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Universal Scraper示例')
    parser.add_argument('--config', type=str, required=True, help='配置文件路径')
    parser.add_argument('--headless', action='store_true', help='启用无头模式')
    parser.add_argument('--no-stealth', action='store_true', help='禁用浏览器指纹伪装')
    parser.add_argument('--no-captcha', action='store_true', help='禁用验证码自动处理')
    parser.add_argument('--max-pages', type=int, help='最大爬取页数')
    parser.add_argument('--max-products', type=int, help='最大爬取商品数')
    parser.add_argument('--proxy', type=str, help='代理地址 (格式: http://user:pass@host:port)')
    
    args = parser.parse_args()
    
    try:
        # 加载配置
        logger.info(f"加载配置文件: {args.config}")
        config = load_config(args.config)
        
        # 根据命令行参数覆盖配置
        if args.headless:
            config.browser.headless = True
            logger.info("已启用无头模式")
            
        if args.no_stealth:
            config.browser.stealth = False
            logger.info("已禁用浏览器指纹伪装")
            
        if args.no_captcha:
            config.captcha.enable = False
            logger.info("已禁用验证码自动处理")
            
        if args.max_pages:
            config.scraping.product_list.max_pages = args.max_pages
            logger.info(f"已设置最大爬取页数: {args.max_pages}")
            
        if args.max_products:
            config.scraping.product_detail.max_products = args.max_products
            logger.info(f"已设置最大爬取商品数: {args.max_products}")
            
        if args.proxy:
            # 解析代理地址
            if '@' in args.proxy:
                auth, address = args.proxy.split('@')
                protocol = auth.split('://')[0]
                username, password = auth.split('://')[1].split(':')
                host, port = address.split(':')
                
                config.proxy.enable = True
                config.proxy.type = protocol
                config.proxy.host = host
                config.proxy.port = int(port)
                config.proxy.username = username
                config.proxy.password = password
            else:
                protocol = args.proxy.split('://')[0]
                host, port = args.proxy.split('://')[1].split(':')
                
                config.proxy.enable = True
                config.proxy.type = protocol
                config.proxy.host = host
                config.proxy.port = int(port)
                
            logger.info(f"已设置代理: {args.proxy}")
        
        # 创建爬虫实例
        logger.info("初始化爬虫...")
        scraper = PlaywrightScraper(config)
        
        # 运行爬虫
        logger.info("开始爬取...")
        start_time = datetime.now()
        results = await scraper.run()
        end_time = datetime.now()
        
        # 打印结果摘要
        duration = (end_time - start_time).total_seconds()
        logger.info(f"爬取完成! 耗时: {duration:.2f}秒")
        logger.info(f"爬取结果: {results['stats']}")
        
        return 0
    except Exception as e:
        logger.error(f"爬虫运行出错: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    # 运行异步主函数
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
