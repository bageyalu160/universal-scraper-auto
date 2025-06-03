#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Universal Scraper - Playwright爬虫模块
支持根据YAML配置文件动态爬取网站
"""

import asyncio
import os
import sys
import time
import json
import random
import logging
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Error as PlaywrightError

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入工具类
try:
    from src.utils.proxy_pool import get_proxy, report_proxy_status
    from src.utils.anti_detect import get_user_agent, get_browser_fingerprint, get_playwright_options
except ImportError:
    # 如果找不到工具类，使用默认实现
    def get_proxy(**kwargs):
        return None
    
    def report_proxy_status(**kwargs):
        pass
    
    def get_user_agent():
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
    
    def get_browser_fingerprint(**kwargs):
        return {}
    
    def get_playwright_options(**kwargs):
        return {}

class PlaywrightScraper:
    """Playwright爬虫类，支持根据配置文件动态爬取网站"""
    
    def __init__(self, site_id: str, config_file: Optional[str] = None, output_dir: Optional[str] = None):
        """
        初始化Playwright爬虫
        
        Args:
            site_id: 站点ID
            config_file: 配置文件路径，为None则从默认路径加载
            output_dir: 输出目录
        """
        self.site_id = site_id
        self.config_file = config_file
        self.output_dir = output_dir
        
        # 加载配置
        self.config = self._load_config()
        
        # 站点信息
        self.site_info = self.config.get('site', {})
        self.site_name = self.site_info.get('name', site_id)
        self.base_url = self.site_info.get('base_url', '')
        
        # 爬取配置
        self.scraping = self.config.get('scraping', {})
        self.engine = self.scraping.get('engine', 'playwright')
        self.browser_config = self.scraping.get('browser', {})
        
        # 解析配置
        self.parsing = self.config.get('parsing', {})
        
        # 输出配置
        self.output_config = self.config.get('output', {})
        
        # 网络配置
        self.network = self.config.get('network', {})
        self.proxy_config = self.network.get('proxy', {})
        self.use_proxy = self.proxy_config.get('enabled', False)
        
        # 设置日志
        self._setup_logging()
        
        # 爬虫状态
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # 数据存储
        self.results = []
        self.stats = {
            "start_time": None,
            "end_time": None,
            "success_count": 0,
            "error_count": 0,
            "retry_count": 0,
            "total_items": 0
        }
        
        self.logger.info(f"初始化 {self.site_name} Playwright爬虫")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        # 如果提供了配置文件路径，直接加载
        if self.config_file and os.path.exists(self.config_file):
            config_path = self.config_file
        else:
            # 否则从默认路径加载
            config_path = os.path.join(PROJECT_ROOT, 'config', 'sites', f'{self.site_id}.yaml')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {str(e)}")
    
    def _setup_logging(self):
        """设置日志记录器"""
        log_config = self.config.get('logging', {})
        log_level_str = log_config.get('level', 'INFO')
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        self.logger = logging.getLogger(f"playwright_scraper_{self.site_id}")
        self.logger.setLevel(log_level)
        
        # 清除已有的处理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 创建格式化器
        log_format = log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter(log_format)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        log_filename = log_config.get('filename', f"{self.site_id}_scraper.log")
        os.makedirs('logs', exist_ok=True)
        file_handler = logging.FileHandler(os.path.join('logs', log_filename))
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
    async def _init_browser(self):
        """初始化浏览器"""
        self.logger.info("初始化浏览器...")
        
        # 获取浏览器类型
        browser_type = self.browser_config.get('type', 'chromium')
        headless = self.browser_config.get('headless', True)
        
        # 获取视口设置
        viewport = self.browser_config.get('viewport', {})
        width = viewport.get('width', 1280)
        height = viewport.get('height', 800)
        
        # 代理设置
        proxy = None
        if self.use_proxy:
            proxy_server = self.proxy_config.get('server', '')
            if proxy_server:
                proxy = {
                    "server": proxy_server,
                    "username": self.proxy_config.get('username', ''),
                    "password": self.proxy_config.get('password', '')
                }
                self.logger.info(f"使用代理: {proxy_server}")
        
        # 获取浏览器指纹
        fingerprint = None
        if self.scraping.get('anti_detection', {}).get('browser_fingerprint', {}).get('enable', False):
            fp_id = f"{self.site_id}_{random.randint(1000, 9999)}"
            fingerprint = get_playwright_options(fp_id)
            self.logger.info(f"使用浏览器指纹: {fp_id}")
        
        # 启动浏览器
        self.playwright = await async_playwright().start()
        browser_launcher = getattr(self.playwright, browser_type)
        
        # 浏览器启动参数
        browser_args = {}
        if headless is not None:
            browser_args['headless'] = headless
        
        self.browser = await browser_launcher.launch(**browser_args)
        
        # 创建上下文
        context_options = {
            "viewport": {"width": width, "height": height}
        }
        
        # 添加代理设置
        if proxy:
            context_options["proxy"] = proxy
        
        # 添加指纹设置
        if fingerprint:
            if "user_agent" in fingerprint:
                context_options["user_agent"] = fingerprint["user_agent"]
            if "locale" in fingerprint:
                context_options["locale"] = fingerprint["locale"]
            if "timezone_id" in fingerprint:
                context_options["timezone_id"] = fingerprint["timezone_id"]
            if "color_scheme" in fingerprint:
                context_options["color_scheme"] = fingerprint["color_scheme"]
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        
        # 设置超时
        timeout = self.network.get('timeout', 60) * 1000  # 转换为毫秒
        self.page.set_default_timeout(timeout)
        
        self.logger.info(f"浏览器初始化完成: {browser_type}")
    
    async def _close_browser(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        self.logger.info("浏览器已关闭")
    
    async def _navigate_to_url(self, url: str) -> bool:
        """
        导航到指定URL
        
        Args:
            url: 目标URL
            
        Returns:
            bool: 是否成功
        """
        try:
            self.logger.info(f"正在访问: {url}")
            response = await self.page.goto(url, wait_until="domcontentloaded")
            
            # 检查响应状态
            if response and response.status >= 400:
                self.logger.error(f"页面加载失败，状态码: {response.status}")
                return False
            
            # 等待页面加载完成
            await self.page.wait_for_load_state("networkidle")
            
            # 检查页面标题
            title = await self.page.title()
            self.logger.info(f"页面标题: {title}")
            
            # 检查是否需要处理验证码
            if await self._check_for_captcha():
                await self._handle_captcha()
            
            return True
        except PlaywrightError as e:
            self.logger.error(f"导航到 {url} 时出错: {str(e)}")
            return False
    
    async def _perform_action(self, action: Dict[str, Any]) -> bool:
        """
        执行页面操作
        
        Args:
            action: 操作配置
            
        Returns:
            bool: 是否成功
        """
        action_type = action.get('type', '')
        
        try:
            if action_type == 'fill':
                selector = action.get('selector', '')
                value = action.get('value', '')
                await self.page.fill(selector, value)
                self.logger.info(f"填写文本: {selector} -> {value}")
                
            elif action_type == 'click':
                selector = action.get('selector', '')
                await self.page.click(selector)
                self.logger.info(f"点击元素: {selector}")
                
            elif action_type == 'wait_for_selector':
                selector = action.get('selector', '')
                timeout = action.get('timeout', 30000)
                await self.page.wait_for_selector(selector, timeout=timeout)
                self.logger.info(f"等待元素: {selector}")
                
            elif action_type == 'wait':
                time_ms = action.get('time', 1000)
                await asyncio.sleep(time_ms / 1000)
                self.logger.info(f"等待: {time_ms}ms")
                
            elif action_type == 'scroll':
                distance = action.get('distance', 300)
                delay = action.get('delay', 100)
                count = action.get('count', 1)
                
                for i in range(count):
                    await self.page.evaluate(f"window.scrollBy(0, {distance})")
                    self.logger.info(f"滚动: {distance}px (第{i+1}次)")
                    await asyncio.sleep(delay / 1000)
            
            elif action_type == 'hover':
                selector = action.get('selector', '')
                await self.page.hover(selector)
                self.logger.info(f"悬停元素: {selector}")
                
            elif action_type == 'select':
                selector = action.get('selector', '')
                value = action.get('value', '')
                await self.page.select_option(selector, value)
                self.logger.info(f"选择选项: {selector} -> {value}")
                
            elif action_type == 'evaluate':
                script = action.get('script', '')
                await self.page.evaluate(script)
                self.logger.info(f"执行脚本: {script[:50]}...")
                
            else:
                self.logger.warning(f"未知操作类型: {action_type}")
                return False
            
            # 操作后等待
            if action.get('wait_after', 0) > 0:
                await asyncio.sleep(action.get('wait_after') / 1000)
            
            return True
        except PlaywrightError as e:
            self.logger.error(f"执行操作 {action_type} 时出错: {str(e)}")
            return False
    
    async def _check_for_captcha(self) -> bool:
        """
        检查页面是否包含验证码
        
        Returns:
            bool: 是否存在验证码
        """
        # 常见验证码选择器
        captcha_selectors = [
            ".captcha",
            "#captcha",
            ".verify-code",
            ".verification-code",
            ".slidecode-container",
            ".geetest_panel",
            "#nc_1_wrapper",
            ".vcode-spin"
        ]
        
        for selector in captcha_selectors:
            try:
                captcha_element = await self.page.query_selector(selector)
                if captcha_element:
                    self.logger.warning(f"检测到验证码: {selector}")
                    return True
            except:
                pass
        
        # 检查页面标题或URL是否包含验证码相关关键词
        title = await self.page.title()
        url = self.page.url
        
        captcha_keywords = ["验证码", "安全验证", "captcha", "verify", "verification"]
        for keyword in captcha_keywords:
            if keyword in title.lower() or keyword in url.lower():
                self.logger.warning(f"检测到验证码页面: {title}")
                return True
        
        return False
    
    async def _handle_captcha(self) -> bool:
        """
        处理验证码
        
        Returns:
            bool: 是否成功处理
        """
        self.logger.info("尝试处理验证码...")
        
        # 这里可以集成验证码处理逻辑
        # 目前只是简单等待，假设用户手动处理
        await asyncio.sleep(10)
        
        self.logger.info("验证码处理完成")
        return True
