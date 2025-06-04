#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
小红书爬虫模块

使用Playwright引擎实现小红书探索页面的爬取功能。
支持自动处理验证码、模拟人类行为和数据提取。
"""

import os
import json
import time
import logging
import random
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from playwright_stealth import stealth_sync

# 导入基类
from src.scrapers.base_scraper import BaseScraper

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/xiaohongshu_scraper.log', encoding='utf-8')
    ]
)

class XiaohongshuScraper(BaseScraper):
    """小红书爬虫实现类"""
    
    def __init__(self, site_id: str, config: Dict[str, Any] = None, output_dir: Optional[str] = None):
        """初始化小红书爬虫"""
        super().__init__(site_id, config, output_dir)
        self.logger = logging.getLogger('scraper.xiaohongshu')
        self.browser = None
        self.context = None
        self.page = None
        
        # 爬取配置
        self.crawl_config = self.config.get('crawl', {})
        self.browser_config = self.config.get('browser', {})
        self.network_config = self.config.get('network', {})
        
        # 输出配置
        self.output_config = self.config.get('output', {})
        
    def _setup_browser(self):
        """设置浏览器环境"""
        self.logger.info("启动浏览器...")
        
        playwright = sync_playwright().start()
        
        # 获取浏览器类型
        browser_type = self.browser_config.get('type', 'chromium')
        browser_types = {
            'chromium': playwright.chromium,
            'firefox': playwright.firefox,
            'webkit': playwright.webkit
        }
        
        # 浏览器启动参数
        launch_args = self.browser_config.get('launch_args', [])
        
        # 启动浏览器
        self.browser = browser_types.get(browser_type, playwright.chromium).launch(
            headless=self.browser_config.get('headless', False),
            args=launch_args
        )
        
        # 创建上下文
        viewport = self.browser_config.get('viewport', {'width': 1920, 'height': 1080})
        self.context = self.browser.new_context(
            viewport=viewport,
            user_agent=self.browser_config.get('user_agent'),
            locale=self.browser_config.get('locale', 'zh-CN'),
            timezone_id=self.browser_config.get('timezone_id', 'Asia/Shanghai'),
            color_scheme=self.browser_config.get('color_scheme', 'light'),
        )
        
        # 创建页面
        self.page = self.context.new_page()
        
        # 应用隐身模式
        if self.browser_config.get('stealth', True):
            self.logger.info("应用浏览器隐身模式...")
            stealth_sync(self.page)
            
        # 设置页面超时
        timeout = self.network_config.get('timeout', 30) * 1000
        self.page.set_default_timeout(timeout)
        
        return self.page
        
    def _perform_interactions(self, interactions):
        """执行页面交互操作"""
        self.logger.info("执行页面交互操作...")
        
        for interaction in interactions:
            interaction_type = interaction.get('type')
            
            try:
                if interaction_type == 'wait':
                    time_ms = interaction.get('time', 1000)
                    self.logger.debug(f"等待 {time_ms}ms")
                    self.page.wait_for_timeout(time_ms)
                    
                elif interaction_type == 'scroll':
                    distance = interaction.get('distance', 300)
                    delay = interaction.get('delay', 100)
                    count = interaction.get('count', 1)
                    
                    self.logger.debug(f"滚动页面 {count} 次，每次 {distance}px")
                    for i in range(count):
                        self.page.evaluate(f"window.scrollBy(0, {distance})")
                        self.page.wait_for_timeout(delay)
                        
                elif interaction_type == 'click':
                    selector = interaction.get('selector')
                    if selector:
                        self.logger.debug(f"点击元素: {selector}")
                        self.page.click(selector)
                        
                elif interaction_type == 'execute_script':
                    script = interaction.get('script')
                    if script:
                        self.logger.debug(f"执行脚本: {script}")
                        self.page.evaluate(script)
                        
                else:
                    self.logger.warning(f"未知交互类型: {interaction_type}")
                    
            except Exception as e:
                self.logger.error(f"执行交互操作失败: {e}")
                
    def _extract_data(self, selectors, item=None):
        """从页面提取数据"""
        if item:
            # 从列表项提取数据
            result = {}
            for field, selector_info in selectors.items():
                selector = selector_info
                attribute = 'textContent'
                
                if isinstance(selector_info, dict):
                    selector = selector_info.get('selector')
                    attribute = selector_info.get('attribute', 'textContent')
                
                try:
                    element = item.query_selector(selector)
                    if element:
                        if attribute == 'text' or attribute == 'textContent':
                            value = element.text_content().strip()
                        elif attribute == 'html' or attribute == 'innerHTML':
                            value = element.inner_html().strip()
                        else:
                            value = element.get_attribute(attribute)
                            
                        result[field] = value
                except Exception as e:
                    self.logger.error(f"提取字段 {field} 失败: {e}")
                    result[field] = None
                    
            return result
        else:
            # 从页面提取数据
            result = {}
            for field, selector_info in selectors.items():
                selector = selector_info
                attribute = 'textContent'
                
                if isinstance(selector_info, dict):
                    selector = selector_info.get('selector')
                    attribute = selector_info.get('attribute', 'textContent')
                
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        if attribute == 'text' or attribute == 'textContent':
                            value = element.text_content().strip()
                        elif attribute == 'html' or attribute == 'innerHTML':
                            value = element.inner_html().strip()
                        else:
                            value = element.get_attribute(attribute)
                            
                        result[field] = value
                except Exception as e:
                    self.logger.error(f"提取字段 {field} 失败: {e}")
                    result[field] = None
                    
            return result
            
    def _extract_list_data(self, category):
        """提取列表页数据"""
        self.logger.info(f"提取列表页数据: {category['name']}")
        
        results = []
        selectors = category.get('selectors', {})
        list_selector = selectors.get('list')
        item_selectors = selectors.get('item', {})
        
        # 获取列表项
        list_items = self.page.query_selector_all(list_selector)
        self.logger.info(f"找到 {len(list_items)} 个列表项")
        
        # 提取每个列表项的数据
        for item in list_items:
            item_data = self._extract_data(item_selectors, item)
            
            # 获取链接
            link_selector = item_selectors.get('link')
            if link_selector:
                link_element = item.query_selector(link_selector)
                if link_element:
                    href = link_element.get_attribute('href')
                    if href:
                        if href.startswith('http'):
                            item_data['link'] = href
                        else:
                            item_data['link'] = f"https://www.xiaohongshu.com{href}"
            
            results.append(item_data)
            
        return results
    
    def _process_detail_page(self, item_data):
        """处理详情页"""
        self.logger.info(f"处理详情页: {item_data.get('title', '未知标题')}")
        
        detail_config = self.crawl_config.get('detail', {})
        if not detail_config.get('enabled', True):
            return item_data
            
        # 打开详情页
        link = item_data.get('link')
        if not link:
            self.logger.warning("详情页链接不存在，跳过")
            return item_data
            
        try:
            # 打开新标签页
            detail_page = self.context.new_page()
            
            # 应用隐身模式
            if self.browser_config.get('stealth', True):
                stealth_sync(detail_page)
                
            # 访问详情页
            self.logger.info(f"访问详情页: {link}")
            detail_page.goto(link, wait_until='networkidle')
            
            # 执行交互操作
            interactions = detail_config.get('interactions', [])
            for interaction in interactions:
                interaction_type = interaction.get('type')
                
                if interaction_type == 'wait':
                    time_ms = interaction.get('time', 1000)
                    detail_page.wait_for_timeout(time_ms)
                    
                elif interaction_type == 'scroll':
                    distance = interaction.get('distance', 300)
                    delay = interaction.get('delay', 100)
                    count = interaction.get('count', 1)
                    
                    for i in range(count):
                        detail_page.evaluate(f"window.scrollBy(0, {distance})")
                        detail_page.wait_for_timeout(delay)
            
            # 提取详情页数据
            selectors = detail_config.get('selectors', {})
            detail_data = {}
            
            for field, selector in selectors.items():
                try:
                    elements = detail_page.query_selector_all(selector)
                    if field == 'images':
                        # 提取所有图片URL
                        image_urls = []
                        for element in elements:
                            src = element.get_attribute('src')
                            if src:
                                image_urls.append(src)
                        detail_data[field] = image_urls
                    else:
                        # 提取文本内容
                        element = detail_page.query_selector(selector)
                        if element:
                            detail_data[field] = element.text_content().strip()
                except Exception as e:
                    self.logger.error(f"提取详情页字段 {field} 失败: {e}")
            
            # 合并数据
            item_data.update(detail_data)
            
            # 关闭详情页
            detail_page.close()
            
        except Exception as e:
            self.logger.error(f"处理详情页失败: {e}")
            
        return item_data
    
    def _process_pagination(self, category):
        """处理分页"""
        pagination = category.get('pagination', {})
        pagination_type = pagination.get('type')
        max_pages = pagination.get('max_pages', 1)
        
        self.logger.info(f"处理分页，类型: {pagination_type}, 最大页数: {max_pages}")
        
        if pagination_type == 'scroll':
            # 滚动加载更多
            scroll_delay = pagination.get('scroll_delay', 2000)
            load_more_selector = pagination.get('load_more_selector')
            
            for page in range(2, max_pages + 1):
                self.logger.info(f"加载第 {page} 页...")
                
                # 滚动到页面底部
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.page.wait_for_timeout(scroll_delay)
                
                # 等待新内容加载
                if load_more_selector:
                    try:
                        # 获取当前元素数量
                        current_count = self.page.eval_on_selector_all(load_more_selector, "elements => elements.length")
                        
                        # 滚动并等待更多元素加载
                        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        self.page.wait_for_timeout(scroll_delay)
                        
                        # 检查是否加载了新元素
                        new_count = self.page.eval_on_selector_all(load_more_selector, "elements => elements.length")
                        
                        if new_count <= current_count:
                            self.logger.warning(f"未加载新内容，停止分页")
                            break
                    except Exception as e:
                        self.logger.error(f"等待加载更多内容失败: {e}")
                        break
    
    def scrape(self):
        """执行爬取操作"""
        self.logger.info(f"开始爬取 {self.site_name}")
        
        try:
            # 设置浏览器
            self._setup_browser()
            
            # 获取入口URL
            entry_url = self.crawl_config.get('entry_url', 'https://www.xiaohongshu.com/explore')
            
            # 访问入口页面
            self.logger.info(f"访问入口页面: {entry_url}")
            self.page.goto(entry_url, wait_until='networkidle')
            
            # 获取所有分类
            categories = self.crawl_config.get('categories', [])
            
            all_results = []
            
            # 处理每个分类
            for category in categories:
                category_name = category.get('name', '未命名分类')
                category_url = category.get('url', entry_url)
                
                self.logger.info(f"处理分类: {category_name}, URL: {category_url}")
                
                # 如果不是入口页面，则导航到分类页面
                if category_url != entry_url:
                    self.page.goto(category_url, wait_until='networkidle')
                
                # 执行页面交互操作
                interactions = category.get('interactions', [])
                self._perform_interactions(interactions)
                
                # 处理分页
                self._process_pagination(category)
                
                # 提取列表数据
                list_results = self._extract_list_data(category)
                
                # 处理详情页
                detail_enabled = self.crawl_config.get('detail', {}).get('enabled', True)
                if detail_enabled:
                    for i, item_data in enumerate(list_results):
                        self.logger.info(f"处理第 {i+1}/{len(list_results)} 个详情页")
                        list_results[i] = self._process_detail_page(item_data)
                        
                        # 添加分类信息
                        list_results[i]['category'] = category_name
                        
                        # 随机延迟，避免请求过快
                        delay = random.uniform(1, 3)
                        time.sleep(delay)
                
                # 合并结果
                all_results.extend(list_results)
            
            # 保存数据
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = self.output_config.get('filename', f"xiaohongshu_{timestamp}.json")
            filename = filename.replace('#{date.now(\'yyyyMMdd_HHmmss\')}', timestamp)
            
            output_path = self.save_data(all_results, filename)
            
            # 统计信息
            stats = {
                'status': 'success',
                'total_items': len(all_results),
                'categories': len(categories),
                'output_file': output_path,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.logger.info(f"爬取完成，共获取 {stats['total_items']} 条数据")
            return stats
            
        except Exception as e:
            self.logger.error(f"爬取过程中发生错误: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        finally:
            # 关闭浏览器
            if self.browser:
                self.browser.close()
                
def scrape_xiaohongshu(config, output_dir=None, **kwargs):
    """
    爬取小红书数据的入口函数
    
    Args:
        config: 配置字典
        output_dir: 输出目录
        **kwargs: 额外参数
        
    Returns:
        Dict: 包含状态和统计信息的字典
    """
    site_id = 'xiaohongshu'
    scraper = XiaohongshuScraper(site_id, config, output_dir)
    return scraper.scrape()
