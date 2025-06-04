#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Universal Scraper - Playwright爬虫模块
支持根据YAML配置文件动态爬取网站
"""

import os
import sys
import yaml
import json
import time
import random
import logging
import asyncio
import psutil
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright.sync_api import Error as PlaywrightError
from playwright_stealth import stealth_async

# 导入 undetected-playwright 库
import undetected_playwright
from undetected_playwright import stealth_async as undetected_stealth_async
from pydantic import BaseModel, Field, field_validator
from twocaptcha import TwoCaptcha

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入工具类


# Pydantic配置模型
class BrowserConfig(BaseModel):
    type: str = Field(default="chromium", description="浏览器类型")
    headless: bool = Field(default=True, description="是否使用无头模式")
    viewport: Dict[str, int] = Field(default={"width": 1280, "height": 800}, description="视口大小")
    
    @field_validator('type')
    def validate_browser_type(cls, v, info):
        if v not in ["chromium", "firefox", "webkit"]:
            raise ValueError(f"不支持的浏览器类型: {v}，只支持 chromium, firefox, webkit")
        return v


class ProxyConfig(BaseModel):
    enable: bool = Field(default=False, description="是否启用代理")
    server: str = Field(default="", description="代理服务器地址")
    username: str = Field(default="", description="代理用户名")
    password: str = Field(default="", description="代理密码")


class FingerprintConfig(BaseModel):
    enable: bool = Field(default=False, description="是否启用浏览器指纹")
    

class CaptchaConfig(BaseModel):
    enable: bool = Field(default=False, description="是否启用验证码处理")
    api_key: str = Field(default="", description="2Captcha API密钥")
    type: str = Field(default="recaptcha", description="验证码类型")
    
    @field_validator('type')
    def validate_captcha_type(cls, v, info):
        if v not in ["recaptcha", "hcaptcha", "image"]:
            raise ValueError(f"不支持的验证码类型: {v}，只支持 recaptcha, hcaptcha, image")
        return v


class NetworkConfig(BaseModel):
    timeout: int = Field(default=60, description="网络超时时间(秒)")
    retry: Dict[str, Any] = Field(default={"max_retries": 3, "backoff_factor": 1.0}, description="重试配置")
    delay: Dict[str, Dict[str, float]] = Field(
        default={
            "page_delay": {"min": 1.0, "max": 3.0},
            "category_delay": {"min": 3.0, "max": 5.0}
        },
        description="延迟配置"
    )


class ParsingConfig(BaseModel):
    product_list_selector: str = Field(default="", description="商品列表选择器")
    list_field_selectors: Dict[str, Dict[str, Any]] = Field(default={}, description="列表字段选择器")
    cleaning: Dict[str, Dict[str, Any]] = Field(default={}, description="数据清洗规则")
    validation: Dict[str, Any] = Field(default={}, description="数据验证规则")


class OutputConfig(BaseModel):
    format: str = Field(default="json", description="输出格式")
    directory: str = Field(default="data", description="输出目录")
    filename_pattern: str = Field(default="{site_id}_{timestamp}.{ext}", description="文件名模式")
    
    @field_validator('format')
    def validate_format(cls, v, info):
        if v not in ["json", "csv", "tsv"]:
            raise ValueError(f"不支持的输出格式: {v}，只支持 json, csv, tsv")
        return v


class ScrapingConfig(BaseModel):
    categories: List[Dict[str, Any]] = Field(default=[], description="分类配置")
    product_list: Dict[str, Any] = Field(default={}, description="商品列表配置")
    product_detail: Dict[str, Any] = Field(default={}, description="商品详情配置")
    interactions: List[Dict[str, Any]] = Field(default=[], description="交互操作配置")
    anti_detection: Dict[str, Any] = Field(default={}, description="反检测配置")


class SiteConfig(BaseModel):
    site_id: str = Field(..., description="站点ID")
    site_name: str = Field(..., description="站点名称")
    base_url: str = Field(..., description="基础URL")
    browser: BrowserConfig = Field(default_factory=BrowserConfig, description="浏览器配置")
    proxy: ProxyConfig = Field(default_factory=ProxyConfig, description="代理配置")
    captcha: CaptchaConfig = Field(default_factory=CaptchaConfig, description="验证码配置")
    network: NetworkConfig = Field(default_factory=NetworkConfig, description="网络配置")
    parsing: ParsingConfig = Field(default_factory=ParsingConfig, description="解析配置")
    output: OutputConfig = Field(default_factory=OutputConfig, description="输出配置")
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig, description="爬取配置")

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
    
    def __init__(self, config, output_dir: str = None, log_level: str = "INFO"):
        """
        初始化爬虫
        
        Args:
            config: 配置对象或配置文件路径
            output_dir: 输出目录
            log_level: 日志级别
        """
        self.output_dir = output_dir
        self.log_level = log_level
        
        # 判断是配置对象还是配置文件路径
        if isinstance(config, str):
            self.config_path = config
            # 加载配置文件
            self.raw_config = self._load_yaml_config()
            self.config = self._parse_config(self.raw_config)
        else:
            # 直接使用传入的配置对象
            self.config_path = None
            self.config = config
        
        # 站点信息
        self.site_id = self.config.site.id
        self.site_name = self.config.site.name
        self.base_url = self.config.site.base_url
        
        # 浏览器配置
        self.browser_config = self.config.browser
        
        # 代理配置
        self.proxy_config = self.config.proxy
        self.use_proxy = self.proxy_config.enable
        
        # 验证码配置
        self.captcha_config = self.config.captcha
        self.captcha_solver = None
        if self.captcha_config.enable and self.captcha_config.api_key:
            self.captcha_solver = TwoCaptcha(self.captcha_config.api_key)
        
        # 爬取配置
        self.scraping = self.config.scraping
        
        # 解析配置
        self.parsing = self.config.parsing
        
        # 输出配置
        self.output_config = self.config.output
        
        # 网络配置
        self.network = self.config.network
        
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
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """
        加载 YAML 配置文件
        
        Returns:
            Dict: 原始配置字典
        """
        if not self.config_path:
            raise ValueError("未指定配置文件路径")
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {str(e)}")
    
    def _parse_config(self, raw_config: Dict[str, Any]) -> SiteConfig:
        """
        解析配置并验证
        
        Args:
            raw_config: 原始配置字典
            
        Returns:
            SiteConfig: 站点配置对象
        """
        try:
            # 站点信息
            site_info = raw_config.get('site', {})
            site_id = site_info.get('id', '')
            site_name = site_info.get('name', '')
            base_url = site_info.get('base_url', '')
            
            # 浏览器配置
            browser_config = BrowserConfig(**raw_config.get('browser', {}))
            
            # 代理配置
            proxy_raw = raw_config.get('network', {}).get('proxy', {})
            proxy_config = ProxyConfig(
                enable=proxy_raw.get('enabled', False),
                server=proxy_raw.get('server', ''),
                username=proxy_raw.get('username', ''),
                password=proxy_raw.get('password', '')
            )
            
            # 验证码配置
            captcha_raw = raw_config.get('scraping', {}).get('anti_detection', {}).get('captcha', {})
            captcha_config = CaptchaConfig(
                enable=captcha_raw.get('enabled', False),
                api_key=captcha_raw.get('api_key', ''),
                type=captcha_raw.get('type', 'recaptcha')
            )
            
            # 网络配置
            network_config = NetworkConfig(**raw_config.get('network', {}))
            
            # 解析配置
            parsing_config = ParsingConfig(**raw_config.get('parsing', {}))
            
            # 输出配置
            output_config = OutputConfig(**raw_config.get('output', {}))
            
            # 爬取配置
            scraping_config = ScrapingConfig(**raw_config.get('scraping', {}))
            
            # 创建完整的站点配置
            site_config = SiteConfig(
                site_id=site_id,
                site_name=site_name,
                base_url=base_url,
                browser=browser_config,
                proxy=proxy_config,
                captcha=captcha_config,
                network=network_config,
                parsing=parsing_config,
                output=output_config,
                scraping=scraping_config
            )
            
            return site_config
            
        except Exception as e:
            raise ValueError(f"解析配置失败: {str(e)}")
    
    def _setup_logging(self):
        """设置日志记录器"""
        # 使用 Pydantic 配置对象
        log_level_str = self.config.logging.level if hasattr(self.config, 'logging') else self.log_level
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        self.logger = logging.getLogger(f"playwright_scraper_{self.site_id}")
        self.logger.setLevel(log_level)
        
        # 清除已有的处理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 创建格式化器
        log_format = self.config.logging.format if hasattr(self.config, 'logging') else '%(asctime)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        log_filename = f"{self.site_id}_scraper.log"
        if hasattr(self.config, 'logging') and hasattr(self.config.logging, 'filename'):
            log_filename = self.config.logging.filename
        os.makedirs('logs', exist_ok=True)
        file_handler = logging.FileHandler(os.path.join('logs', log_filename))
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
    async def _init_browser(self):
        """初始化浏览器，使用undetected-playwright增强反检测能力"""
        self.logger.info("初始化浏览器...")
        
        # 获取浏览器类型
        browser_type = self.browser_config.type
        headless = self.browser_config.headless
        
        # 获取视口设置
        width = self.browser_config.viewport.width
        height = self.browser_config.viewport.height
        
        # 使用undetected-playwright来隐藏浏览器特征
        self.logger.info("使用undetected-playwright来隐藏浏览器特征...")
        
        # 代理设置
        proxy = None
        if self.use_proxy and self.proxy_config.server:
            proxy = {
                "server": self.proxy_config.server,
                "username": self.proxy_config.username,
                "password": self.proxy_config.password
            }
            self.logger.info(f"使用代理: {self.proxy_config.server}")
        
        # 启动浏览器
        # 使用原生 playwright 启动，然后使用 undetected-playwright 进行增强
        self.playwright = await async_playwright().start()
        
        # 根据配置选择浏览器类型
        if browser_type == "chromium":
            browser_instance = self.playwright.chromium
        elif browser_type == "firefox":
            browser_instance = self.playwright.firefox
        elif browser_type == "webkit":
            browser_instance = self.playwright.webkit
        else:
            browser_instance = self.playwright.chromium
            
        self.logger.info(f"使用 {browser_type} 浏览器")
        
        browser_args = {}
        if headless is not None:
            browser_args['headless'] = headless
        
        # 添加自定义参数
        # Playwright 的 launch 参数分为两类：
        # 1. 直接传递给 launch 的关键字参数，如 headless, slow_mo 等
        # 2. 传递给浏览器的命令行参数，需要放在 args 列表中
        
        # 初始化 args 列表
        args = []
        
        if hasattr(self.browser_config, 'launch_args') and self.browser_config.launch_args:
            # 判断是列表还是字典
            if isinstance(self.browser_config.launch_args, list):
                # 如果是列表，则每个元素都是浏览器命令行参数
                args.extend(self.browser_config.launch_args)
            elif isinstance(self.browser_config.launch_args, dict):
                # 如果是字典，则根据键名决定是关键字参数还是命令行参数
                for key, value in self.browser_config.launch_args.items():
                    if key.startswith('--'):
                        # 命令行参数
                        if isinstance(value, bool):
                            if value:
                                args.append(key)
                        else:
                            args.append(f"{key}={value}")
                    else:
                        # 关键字参数
                        browser_args[key] = value
        
        # 如果有命令行参数，添加到 browser_args 中
        if args:
            browser_args['args'] = args
        
        # 启动浏览器 - undetected_playwright会自动添加反检测参数
        self.logger.info("使用undetected_playwright启动浏览器...")
        self.browser = await browser_instance.launch(**browser_args)
        self.logger.info("浏览器启动成功")
        
        # 创建上下文
        context_options = {
            "viewport": {"width": width, "height": height}
        }
        
        # 添加代理设置
        if proxy:
            context_options["proxy"] = proxy
        
        # 添加用户代理
        if hasattr(self.browser_config, 'user_agent') and self.browser_config.user_agent:
            context_options["user_agent"] = self.browser_config.user_agent
        
        # 添加区域设置
        if hasattr(self.browser_config, 'locale') and self.browser_config.locale:
            context_options["locale"] = self.browser_config.locale
        
        # 添加时区设置
        if hasattr(self.browser_config, 'timezone_id') and self.browser_config.timezone_id:
            context_options["timezone_id"] = self.browser_config.timezone_id
        
        # 添加颜色方案
        if hasattr(self.browser_config, 'color_scheme') and self.browser_config.color_scheme:
            context_options["color_scheme"] = self.browser_config.color_scheme
        
        # 创建浏览器上下文
        self.logger.info("创建浏览器上下文...")
        self.context = await self.browser.new_context(**context_options)
        self.logger.info("浏览器上下文创建成功")
        
        # 应用额外的stealth技术增强反检测能力
        if hasattr(self.browser_config, 'stealth') and self.browser_config.stealth:
            try:
                # 先应用 playwright-stealth
                self.logger.info("应用 playwright-stealth 技术...")
                await stealth_async(self.context)
                self.logger.info("已应用 playwright-stealth 技术")
                
                # 再应用 undetected-playwright
                self.logger.info("应用 undetected-playwright 技术...")
                await undetected_stealth_async(self.context)
                self.logger.info("已应用 undetected-playwright 技术增强反检测能力")
                
                # 注入额外的反检测脚本
                self.logger.info("注入额外的反检测脚本...")
                await self.context.add_init_script("""
                // 额外的反检测脚本
                // 修改Navigator原型
                const originalGetPrototypeOf = Object.getPrototypeOf;
                Object.getPrototypeOf = function(obj) {
                    if (obj.toString() === '[object Navigator]') {
                        return {};
                    }
                    return originalGetPrototypeOf(obj);
                };
                
                // 修改权限API
                if (navigator.permissions) {
                    const originalQuery = navigator.permissions.query;
                    navigator.permissions.query = function(parameters) {
                        if (parameters.name === 'notifications') {
                            return Promise.resolve({ state: Notification.permission });
                        }
                        return originalQuery.call(this, parameters);
                    };
                }
                
                // 模拟WebGL
                if (window.WebGLRenderingContext) {
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        // UNMASKED_VENDOR_WEBGL
                        if (parameter === 37445) {
                            return 'Google Inc. (Intel)';
                        }
                        // UNMASKED_RENDERER_WEBGL
                        if (parameter === 37446) {
                            return 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                        }
                        return getParameter.apply(this, arguments);
                    };
                }
                
                // 添加Chrome运行时
                if (!window.chrome) {
                    window.chrome = {
                        runtime: {
                            connect: function() {
                                return {
                                    onDisconnect: { addListener: function() {} },
                                    onMessage: { addListener: function() {} },
                                    postMessage: function() {}
                                };
                            }
                        }
                    };
                }
                
                // 模拟插件
                Object.defineProperty(navigator, 'plugins', {
                    get: function() {
                        return [{
                            0: {type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format'},
                            description: 'Chrome PDF Plugin',
                            filename: 'internal-pdf-viewer',
                            name: 'Chrome PDF Plugin',
                            length: 1
                        }, {
                            0: {type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format'},
                            description: 'Chrome PDF Viewer',
                            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                            name: 'Chrome PDF Viewer',
                            length: 1
                        }, {
                            0: {type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable'},
                            1: {type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable'},
                            description: 'Native Client',
                            filename: 'internal-nacl-plugin',
                            name: 'Native Client',
                            length: 2
                        }];
                    }
                });
                
                // 修改语言设置
                Object.defineProperty(navigator, 'languages', {
                    get: function() {
                        return ['zh-CN', 'zh', 'en-US', 'en'];
                    }
                });
                
                // 修改硬件并发数
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: function() {
                        return 8;
                    }
                });
                
                // 修改设备内存
                if ('deviceMemory' in navigator) {
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: function() {
                            return 8;
                        }
                    });
                }
                
                // 修改用户代理数据
                if (navigator.userAgentData) {
                    Object.defineProperty(navigator.userAgentData, 'brands', {
                        get: function() {
                            return [
                                {brand: 'Chromium', version: '122'},
                                {brand: 'Not=A?Brand', version: '24'},
                                {brand: 'Google Chrome', version: '122'}
                            ];
                        }
                    });
                    
                    Object.defineProperty(navigator.userAgentData, 'mobile', {
                        get: function() {
                            return false;
                        }
                    });
                    
                    Object.defineProperty(navigator.userAgentData, 'platform', {
                        get: function() {
                            return 'Windows';
                        }
                    });
                }
                
                // 隐藏自动化标志
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                """)
                self.logger.info("已注入额外的反检测脚本")
            except Exception as e:
                self.logger.warning(f"应用额外反检测技术时出错: {e}")
                self.logger.info("继续使用undetected-playwright内置的反检测功能")
                # 如果出错，不用担心，undetected-playwright已经提供了基本的反检测功能
        
        # 创建新页面
        self.page = await self.context.new_page()
        
        # 设置超时
        timeout = self.network.timeout * 1000  # 转换为毫秒
        self.page.set_default_timeout(timeout)
        
        self.logger.info(f"浏览器初始化完成: {browser_type}")
        
        return self.page
    
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
            has_captcha, captcha_type = await self._check_for_captcha()
            if has_captcha:
                await self._handle_captcha(captcha_type)
            
            return True
        except PlaywrightError as e:
            self.logger.error(f"导航到 {url} 时出错: {str(e)}")
            return False
    
    async def _perform_action(self, action):
        """
        执行页面交互操作
        
        Args:
            action: 操作配置（可能是字典或Pydantic模型）
            
        Returns:
            bool: 是否成功
        """
        # 获取操作类型，支持字典或Pydantic模型
        if hasattr(action, 'type'):
            action_type = action.type
        elif isinstance(action, dict):
            action_type = action.get('type', '')
        else:
            self.logger.warning(f"无效的操作配置类型: {type(action)}")
            return False
        
        try:
            # 通用函数，从字典或Pydantic模型中获取属性
            def get_value(obj, key, default_value):
                if hasattr(obj, key):
                    return getattr(obj, key)
                elif isinstance(obj, dict) and key in obj:
                    return obj.get(key, default_value)
                return default_value
            
            if action_type == 'fill':
                selector = get_value(action, 'selector', '')
                value = get_value(action, 'value', '')
                await self.page.fill(selector, value)
                self.logger.info(f"填写文本: {selector} -> {value}")
                
            elif action_type == 'click':
                selector = get_value(action, 'selector', '')
                await self.page.click(selector)
                self.logger.info(f"点击元素: {selector}")
                
            elif action_type == 'wait_for_selector':
                selector = get_value(action, 'selector', '')
                timeout = get_value(action, 'timeout', 30000)
                await self.page.wait_for_selector(selector, timeout=timeout)
                self.logger.info(f"等待元素: {selector}")
                
            elif action_type == 'wait':
                time_ms = get_value(action, 'time', 1000)
                await asyncio.sleep(time_ms / 1000)
                self.logger.info(f"等待: {time_ms}ms")
                
            elif action_type == 'scroll':
                distance = get_value(action, 'distance', 300)
                delay = get_value(action, 'delay', 100)
                count = get_value(action, 'count', 1)
                
                for i in range(count):
                    await self.page.evaluate(f"window.scrollBy(0, {distance})")
                    self.logger.info(f"滚动: {distance}px (第{i+1}次)")
                    await asyncio.sleep(delay / 1000)
            
            elif action_type == 'hover':
                selector = get_value(action, 'selector', '')
                await self.page.hover(selector)
                self.logger.info(f"悬停元素: {selector}")
                
            elif action_type == 'select':
                selector = get_value(action, 'selector', '')
                value = get_value(action, 'value', '')
                await self.page.select_option(selector, value)
                self.logger.info(f"选择选项: {selector} -> {value}")
                
            elif action_type == 'evaluate':
                script = get_value(action, 'script', '')
                await self.page.evaluate(script)
                self.logger.info(f"执行脚本: {script[:50]}...")
                
            else:
                self.logger.warning(f"未知操作类型: {action_type}")
                return False
            
            # 操作后等待
            wait_after = get_value(action, 'wait_after', 0)
            # 确保wait_after不为None
            if wait_after is None:
                wait_after = 0
            if wait_after > 0:
                await asyncio.sleep(wait_after / 1000)
            
            return True
        except Exception as e:
            self.logger.error(f"执行操作 {action_type} 时出错: {str(e)}")
            return False
    
    async def _check_for_captcha(self) -> Tuple[bool, str]:
        """
        检查页面是否包含验证码
        
        Returns:
            Tuple[bool, str]: (是否存在验证码, 验证码类型)
        """
        self.logger.info("检查页面是否包含验证码...")
        
        # 检查 reCAPTCHA v2
        recaptcha_selectors = [
            "iframe[src*='recaptcha']", 
            "iframe[title*='recaptcha']",
            "div.g-recaptcha"
        ]
        
        for selector in recaptcha_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    self.logger.warning(f"检测到 reCAPTCHA v2: {selector}")
                    return True, "recaptcha"
            except Exception as e:
                self.logger.debug(f"检查 reCAPTCHA 选择器 {selector} 时出错: {str(e)}")
        
        # 检查 hCaptcha
        hcaptcha_selectors = [
            "iframe[src*='hcaptcha']",
            "div.h-captcha"
        ]
        
        for selector in hcaptcha_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    self.logger.warning(f"检测到 hCaptcha: {selector}")
                    return True, "hcaptcha"
            except Exception as e:
                self.logger.debug(f"检查 hCaptcha 选择器 {selector} 时出错: {str(e)}")
        
        # 检查图片验证码
        image_captcha_selectors = [
            "img[alt*='captcha']",
            "img[src*='captcha']",
            "input[name*='captcha']"
        ]
        
        for selector in image_captcha_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    self.logger.warning(f"检测到图片验证码: {selector}")
                    return True, "image"
            except Exception as e:
                self.logger.debug(f"检查图片验证码选择器 {selector} 时出错: {str(e)}")
        
        # 检查页面标题或URL是否包含验证码相关关键词
        title = await self.page.title()
        url = self.page.url
        
        captcha_keywords = {"验证码": "image", "安全验证": "image", "captcha": "image", 
                          "recaptcha": "recaptcha", "hcaptcha": "hcaptcha"}
        
        for keyword, captcha_type in captcha_keywords.items():
            if keyword.lower() in title.lower() or keyword.lower() in url.lower():
                self.logger.warning(f"检测到可能的验证码页面: {title}，类型: {captcha_type}")
                return True, captcha_type
        
        return False, ""
    
    async def _handle_captcha(self, captcha_type: str = "recaptcha") -> bool:
        """
        处理验证码
        
        Args:
            captcha_type: 验证码类型
            
        Returns:
            bool: 是否成功处理
        """
        self.logger.warning(f"检测到{captcha_type}验证码，尝试处理...")
        
        if not self.captcha_config.enable:
            self.logger.warning("验证码处理未启用，等待30秒供手动处理...")
            await asyncio.sleep(30)
            return True
        
        if not self.captcha_solver:
            self.logger.error("未配置验证码求解器，无法自动处理验证码")
            return False
        
        try:
            if captcha_type == "recaptcha":
                return await self._solve_recaptcha()
            elif captcha_type == "hcaptcha":
                return await self._solve_hcaptcha()
            elif captcha_type == "image":
                return await self._solve_image_captcha()
            else:
                self.logger.warning(f"未知验证码类型: {captcha_type}，等待30秒供手动处理...")
                await asyncio.sleep(30)
                return True
        except Exception as e:
            self.logger.error(f"处理验证码时出错: {str(e)}")
            return False
    
    async def _solve_recaptcha(self) -> bool:
        """
        解决reCAPTCHA验证码
        
        Returns:
            bool: 是否成功处理
        """
        try:
            # 获取网站密钥
            site_key = await self.page.evaluate("""
                () => {
                    const recaptchaElement = document.querySelector('.g-recaptcha');
                    if (recaptchaElement) {
                        return recaptchaElement.getAttribute('data-sitekey');
                    }
                    
                    // 尝试从脚本中提取
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const content = script.textContent;
                        if (content && content.includes('sitekey')) {
                            const match = content.match(/['"]sitekey['"]: ?['"]([^'"]+)['"]/);
                            if (match) return match[1];
                        }
                    }
                    return null;
                }
            """)
            
            if not site_key:
                self.logger.error("无法获取reCAPTCHA站点密钥")
                return False
                
            self.logger.info(f"获取到reCAPTCHA站点密钥: {site_key}")
            
            # 使用2captcha解决验证码
            result = await asyncio.to_thread(
                self.captcha_solver.recaptcha,
                sitekey=site_key,
                url=self.page.url
            )
            
            self.logger.info(f"2captcha返回结果: {result}")
            
            # 将结果注入页面
            await self.page.evaluate(f"""
                (token) => {{
                    document.querySelector('#g-recaptcha-response').innerHTML = token;
                    // 尝试提交表单
                    const form = document.querySelector('form');
                    if (form) form.submit();
                }}
            """, result['code'])
            
            # 等待页面变化
            await self.page.wait_for_load_state("networkidle")
            self.logger.info("reCAPTCHA验证码处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"解决reCAPTCHA时出错: {str(e)}")
            return False
    
    async def _solve_hcaptcha(self) -> bool:
        """
        解决hCaptcha验证码
        
        Returns:
            bool: 是否成功处理
        """
        try:
            # 获取网站密钥
            site_key = await self.page.evaluate("""
                () => {
                    const hcaptchaElement = document.querySelector('.h-captcha');
                    if (hcaptchaElement) {
                        return hcaptchaElement.getAttribute('data-sitekey');
                    }
                    return null;
                }
            """)
            
            if not site_key:
                self.logger.error("无法获取hCaptcha站点密钥")
                return False
                
            self.logger.info(f"获取到hCaptcha站点密钥: {site_key}")
            
            # 使用2captcha解决验证码
            result = await asyncio.to_thread(
                self.captcha_solver.hcaptcha,
                sitekey=site_key,
                url=self.page.url
            )
            
            self.logger.info(f"2captcha返回结果: {result}")
            
            # 将结果注入页面
            await self.page.evaluate(f"""
                (token) => {{
                    document.querySelector('textarea[name="h-captcha-response"]').innerHTML = token;
                    // 尝试提交表单
                    const form = document.querySelector('form');
                    if (form) form.submit();
                }}
            """, result['code'])
            
            # 等待页面变化
            await self.page.wait_for_load_state("networkidle")
            self.logger.info("hCaptcha验证码处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"解决hCaptcha时出错: {str(e)}")
            return False
    
    async def _solve_image_captcha(self) -> bool:
        """
        解决图片验证码
        
        Returns:
            bool: 是否成功处理
        """
        try:
            # 查找验证码图片
            img_selector = "img[src*='captcha'], img[alt*='captcha']"
            img_element = await self.page.query_selector(img_selector)
            
            if not img_element:
                self.logger.error("无法找到验证码图片元素")
                return False
                
            # 获取图片内容
            img_src = await img_element.get_attribute('src')
            
            # 如果是base64编码的图片
            if img_src.startswith('data:image'):
                img_base64 = img_src.split(',')[1]
            else:
                # 下载图片
                response = await self.page.request.get(img_src)
                img_buffer = await response.body()
                img_base64 = base64.b64encode(img_buffer).decode('utf-8')
            
            # 使用2captcha解决图片验证码
            result = await asyncio.to_thread(
                self.captcha_solver.normal,
                image=img_base64
            )
            
            self.logger.info(f"2captcha返回图片验证码结果: {result}")
            
            # 查找验证码输入框
            input_selector = "input[name*='captcha'], input[placeholder*='验证码']"
            await self.page.fill(input_selector, result['code'])
            
            # 尝试提交表单
            submit_selector = "button[type='submit'], input[type='submit']"
            await self.page.click(submit_selector)
            
            # 等待页面变化
            await self.page.wait_for_load_state("networkidle")
            self.logger.info("图片验证码处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"解决图片验证码时出错: {str(e)}")
            return False
        
    async def _extract_data(self, selector: str, field_selectors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从页面提取数据
        
{{ ... }}
        Args:
            selector: 列表项选择器
            field_selectors: 字段选择器配置
            
        Returns:
            List[Dict[str, Any]]: 提取的数据列表
        """
        self.logger.info(f"开始提取数据，使用选择器: {selector}")
        
        try:
            # 等待选择器出现
            await self.page.wait_for_selector(selector, state="attached")
            
            # 获取所有匹配的元素
            elements = await self.page.query_selector_all(selector)
            self.logger.info(f"找到 {len(elements)} 个匹配元素")
            
            results = []
            for idx, element in enumerate(elements):
                item_data = {}
                
                # 提取每个字段的数据
                for field_name, field_config in field_selectors.items():
                    try:
                        # 通用函数，从字典或Pydantic模型中获取属性
                        def get_value(obj, key, default_value):
                            if hasattr(obj, key):
                                return getattr(obj, key)
                            elif isinstance(obj, dict) and key in obj:
                                return obj.get(key, default_value)
                            return default_value
                            
                        field_selector = get_value(field_config, 'selector', '')
                        attribute = get_value(field_config, 'attribute', 'text')
                        transform = get_value(field_config, 'transform', None)
                        regex = get_value(field_config, 'regex', None)
                        
                        # 在当前元素内查找
                        field_element = await element.query_selector(field_selector)
                        
                        if field_element:
                            # 根据属性类型获取值
                            if attribute == 'text':
                                value = await field_element.text_content()
                            elif attribute == 'html':
                                value = await field_element.inner_html()
                            else:
                                value = await field_element.get_attribute(attribute)
                            
                            # 应用正则表达式
                            if regex and value:
                                import re
                                match = re.search(regex, value)
                                if match and match.groups():
                                    value = match.group(1)
                            
                            # 应用转换
                            if transform and value:
                                if isinstance(transform, str):
                                    value = transform.format(value=value)
                                elif callable(transform):
                                    value = transform(value)
                            
                            # 清理数据
                            if value and isinstance(value, str):
                                value = value.strip()
                            
                            item_data[field_name] = value
                        else:
                            item_data[field_name] = None
                            
                    except Exception as e:
                        self.logger.error(f"提取字段 {field_name} 时出错: {str(e)}")
                        item_data[field_name] = None
                
                # 添加元数据
                item_data['_index'] = idx
                item_data['_timestamp'] = datetime.now().isoformat()
                item_data['_url'] = self.page.url
                
                # 应用数据清洗规则
                item_data = self._clean_data(item_data)
                
                # 验证数据
                if self._validate_data(item_data):
                    results.append(item_data)
                    self.logger.debug(f"提取到数据项 {idx+1}: {item_data}")
                else:
                    self.logger.warning(f"数据项 {idx+1} 验证失败，已跳过")
            
            self.logger.info(f"成功提取 {len(results)} 条数据")
            return results
            
        except PlaywrightError as e:
            self.logger.error(f"提取数据时出错: {str(e)}")
            return []
    
    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清洗数据
        
        Args:
            data: 原始数据
            
        Returns:
            Dict[str, Any]: 清洗后的数据
        """
        # 获取清洗规则
        cleaning_rules = {}
        if hasattr(self.parsing, 'cleaning'):
            cleaning_rules = self.parsing.cleaning
        
        for field, rules in cleaning_rules.items():
            if field in data and data[field]:
                value = data[field]
                
                # 应用清洗规则
                if isinstance(value, str):
                    # 移除指定字符
                    if 'remove' in rules:
                        for char in rules['remove'].split(','):
                            value = value.replace(char, '')
                    
                    # 类型转换
                    if 'type' in rules:
                        data_type = rules['type']
                        try:
                            if data_type == 'numeric':
                                value = float(value)
                                # 整数处理
                                if value.is_integer():
                                    value = int(value)
                            elif data_type == 'integer':
                                value = int(value)
                            elif data_type == 'boolean':
                                value = value.lower() in ['true', 'yes', '1', 'y']
                            elif data_type == 'percentage':
                                value = float(value.rstrip('%')) / 100
                        except (ValueError, TypeError):
                            self.logger.warning(f"无法将字段 {field} 转换为 {data_type} 类型")
                    
                    # 乘数
                    if 'multiplier' in rules and isinstance(value, (int, float)):
                        value = value * rules['multiplier']
                
                data[field] = value
        
        return data
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据
        
        Args:
            data: 待验证的数据
            
        Returns:
            bool: 是否通过验证
        """
        # 获取验证规则
        validation_rules = {}
        if hasattr(self.parsing, 'validation'):
            validation_rules = self.parsing.validation
        
        # 检查必填字段
        required_fields = []
        if hasattr(validation_rules, 'required_fields'):
            required_fields = validation_rules.required_fields
        elif isinstance(validation_rules, dict) and 'required_fields' in validation_rules:
            required_fields = validation_rules.get('required_fields', [])
            
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                self.logger.warning(f"数据验证失败: 缺少必填字段 {field}")
                return False
        
        # 检查数值范围
        for field, range_rules in validation_rules.items():
            if field.endswith('_range') and isinstance(range_rules, dict):
                field_name = field.replace('_range', '')
                if field_name in data and isinstance(data[field_name], (int, float)):
                    value = data[field_name]
                    
                    # 最小值检查
                    if 'min' in range_rules and value < range_rules['min']:
                        self.logger.warning(f"数据验证失败: 字段 {field_name} 值 {value} 小于最小值 {range_rules['min']}")
                        return False
                    
                    # 最大值检查
                    if 'max' in range_rules and value > range_rules['max']:
                        self.logger.warning(f"数据验证失败: 字段 {field_name} 值 {value} 大于最大值 {range_rules['max']}")
                        return False
        
        return True
    
    async def _save_data(self, data: List[Dict[str, Any]]) -> str:
        """
        保存数据
        
        Args:
            data: 要保存的数据
            
        Returns:
            str: 保存的文件路径
        """
        if not data:
            self.logger.warning("没有数据需要保存")
            return ""
        
        # 获取输出配置
        output_format = 'json'
        output_dir = self.output_dir or 'data'
        filename_pattern = '{site_id}_{timestamp}.{ext}'
        
        # 从 Pydantic 模型中获取配置
        if hasattr(self.output_config, 'format'):
            output_format = self.output_config.format
        if not self.output_dir and hasattr(self.output_config, 'directory'):
            output_dir = self.output_config.directory
        if hasattr(self.output_config, 'filename_pattern'):
            filename_pattern = self.output_config.filename_pattern
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = filename_pattern.format(
            site_id=self.site_id,
            timestamp=timestamp,
            date=datetime.now().strftime('%Y%m%d'),
            ext=output_format
        )
        
        # 完整文件路径
        file_path = os.path.join(output_dir, filename)
        
        # 根据格式保存数据
        try:
            if output_format == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif output_format == 'csv':
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    if data:
                        fieldnames = list(data[0].keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data)
            elif output_format == 'tsv':
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    if data:
                        fieldnames = list(data[0].keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
                        writer.writeheader()
                        writer.writerows(data)
            else:
                self.logger.error(f"不支持的输出格式: {output_format}")
                return ""
            
            self.logger.info(f"数据已保存到: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"保存数据时出错: {str(e)}")
            return ""
    
    async def _with_retry(self, func, *args, max_retries=3, **kwargs):
        """
        带重试机制的函数执行器
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            max_retries: 最大重试次数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        # 从Pydantic模型或字典中获取重试配置
        backoff_factor = 1.0  # 默认退避因子
        retry_delay = 2.0     # 默认重试延迟（秒）
        
        if hasattr(self.network, 'retry'):
            retry_config = self.network.retry
            if hasattr(retry_config, 'max_retries'):
                max_retries = retry_config.max_retries
            if hasattr(retry_config, 'retry_delay'):
                retry_delay = retry_config.retry_delay / 1000  # 毫秒转秒
            if hasattr(retry_config, 'backoff_factor'):
                backoff_factor = retry_config.backoff_factor
        elif isinstance(self.network, dict) and 'retry' in self.network:
            retry_config = self.network['retry']
            if 'max_retries' in retry_config:
                max_retries = retry_config.get('max_retries', max_retries)
            if 'retry_delay' in retry_config:
                retry_delay = retry_config.get('retry_delay', 2000) / 1000  # 毫秒转秒
            if 'backoff_factor' in retry_config:
                backoff_factor = retry_config.get('backoff_factor', 1.0)
        
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    self.logger.info(f"第 {retry_count} 次重试 {func.__name__}...")
                
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                retry_count += 1
                last_error = e
                self.stats["retry_count"] += 1
                
                if retry_count <= max_retries:
                    # 计算等待时间，使用指数退避策略
                    wait_time = retry_delay * (backoff_factor ** (retry_count - 1))
                    self.logger.warning(f"{func.__name__} 出错: {str(e)}, {wait_time:.1f} 秒后重试 ({retry_count}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"{func.__name__} 失败后已达到最大重试次数: {str(e)}")
                    self.stats["error_count"] += 1
                    raise last_error
    
    async def _monitor_performance(self):
        """监控系统性能"""
        # 获取当前进程
        import psutil
        process = psutil.Process(os.getpid())
        
        # 初始化指标
        metrics = {
            "memory_usage": [],
            "cpu_percent": [],
            "start_time": time.time()
        }
        
        try:
            while True:
                # 收集内存使用情况
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024  # 转换为MB
                metrics["memory_usage"].append(memory_mb)
                
                # 收集CPU使用情况
                cpu_percent = process.cpu_percent(interval=0.1)
                metrics["cpu_percent"].append(cpu_percent)
                
                # 输出当前指标
                self.logger.debug(f"性能监控: 内存使用 {memory_mb:.2f} MB, CPU使用 {cpu_percent:.1f}%")
                
                # 等待一段时间再次检测
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            # 计算平均值
            avg_memory = sum(metrics["memory_usage"]) / len(metrics["memory_usage"]) if metrics["memory_usage"] else 0
            avg_cpu = sum(metrics["cpu_percent"]) / len(metrics["cpu_percent"]) if metrics["cpu_percent"] else 0
            duration = time.time() - metrics["start_time"]
            
            self.logger.info(f"性能监控汇总: 运行时间 {duration:.1f} 秒, 平均内存使用 {avg_memory:.2f} MB, 平均CPU使用 {avg_cpu:.1f}%")
            
            return {
                "duration": duration,
                "avg_memory_usage": avg_memory,
                "avg_cpu_percent": avg_cpu,
                "peak_memory_usage": max(metrics["memory_usage"]) if metrics["memory_usage"] else 0,
                "peak_cpu_percent": max(metrics["cpu_percent"]) if metrics["cpu_percent"] else 0
            }
    
    async def crawl_category(self, category_config):
        """
        爆取指定分类
        
        Args:
            category_config: 分类配置（可能是字典或Pydantic模型）
            
        Returns:
            List[Dict[str, Any]]: 爆取的数据
        """
        # 通用函数，从字典或Pydantic模型中获取属性
        def get_value(obj, key, default_value):
            if hasattr(obj, key):
                return getattr(obj, key)
            elif isinstance(obj, dict) and key in obj:
                return obj.get(key, default_value)
            return default_value
            
        category_id = get_value(category_config, 'id', '')
        category_name = get_value(category_config, 'name', '')
        subcategories = get_value(category_config, 'subcategories', [])
        
        self.logger.info(f"开始爬取分类: {category_name} (ID: {category_id})")
        
        all_results = []
        
        # 如果有子分类，则爬取子分类
        if subcategories:
            for subcategory in subcategories:
                # 安全获取子分类属性，兼容Pydantic模型和字典
                subcategory_id = ''
                subcategory_name = ''
                depth = 1
                
                if hasattr(subcategory, 'id'):
                    subcategory_id = subcategory.id
                elif isinstance(subcategory, dict):
                    subcategory_id = subcategory.get('id', '')
                    
                if hasattr(subcategory, 'name'):
                    subcategory_name = subcategory.name
                elif isinstance(subcategory, dict):
                    subcategory_name = subcategory.get('name', '')
                    
                if hasattr(subcategory, 'depth'):
                    depth = subcategory.depth
                elif isinstance(subcategory, dict):
                    depth = subcategory.get('depth', 1)
                
                self.logger.info(f"爬取子分类: {subcategory_name} (ID: {subcategory_id})")
                
                # 构建完整分类 ID
                full_category_id = f"{category_id},{subcategory_id}"
                if depth > 2:
                    full_category_id = f"{full_category_id},0"
                
                # 获取列表页配置
                product_list_config = {}
                if hasattr(self.scraping, 'product_list'):
                    product_list_config = self.scraping.product_list
                
                # 安全获取列表页配置属性
                items_per_page = 30
                max_pages = 3
                url_format = ''
                
                if isinstance(product_list_config, dict):
                    items_per_page = product_list_config.get('items_per_page', 30)
                    max_pages = product_list_config.get('max_pages', 3)
                    url_format = product_list_config.get('url_format', '')
                else:
                    if hasattr(product_list_config, 'items_per_page'):
                        items_per_page = product_list_config.items_per_page
                    if hasattr(product_list_config, 'max_pages'):
                        max_pages = product_list_config.max_pages
                    if hasattr(product_list_config, 'url_format'):
                        url_format = product_list_config.url_format
                
                # 分页爬取
                for page in range(1, max_pages + 1):
                    # 构建 URL
                    url = url_format.format(cat_id=full_category_id, page=page)
                    
                    try:
                        # 导航到列表页
                        success = await self._with_retry(self._navigate_to_url, url)
                        if not success:
                            self.logger.error(f"无法访问列表页: {url}")
                            continue
                        
                        # 执行交互操作
                        interactions = []
                        if hasattr(self.scraping, 'interactions'):
                            interactions = self.scraping.interactions
                        
                        for action in interactions:
                            await self._with_retry(self._perform_action, action)
                        
                        # 提取数据
                        product_list_selector = ''
                        if hasattr(self.parsing, 'product_list_selector'):
                            product_list_selector = self.parsing.product_list_selector
                        # 获取列表字段选择器
                        list_field_selectors = {}
                        if hasattr(self.parsing, 'list_field_selectors'):
                            list_field_selectors = self.parsing.list_field_selectors
                        
                        page_results = await self._with_retry(self._extract_data, product_list_selector, list_field_selectors)
                        
                        # 添加分类信息
                        for item in page_results:
                            item['category_id'] = full_category_id
                            item['category_name'] = f"{category_name} > {subcategory_name}"
                            item['page'] = page
                        
                        all_results.extend(page_results)
                        self.logger.info(f"第 {page} 页爆取完成，获取 {len(page_results)} 条数据")
                        
                        # 检查是否达到最大商品数量
                        max_products = 0
                        if hasattr(self.scraping, 'product_detail'):
                            product_detail = self.scraping.product_detail
                            if hasattr(product_detail, 'max_products'):
                                max_products = product_detail.max_products
                                
                        if max_products > 0 and len(all_results) >= max_products:
                            self.logger.info(f"已达到最大商品数量限制: {max_products}")
                            break
                        
                        # 页面间延迟
                        page_delay = {}
                        if hasattr(self.network, 'delay'):
                            network_delay = self.network.delay
                            if hasattr(network_delay, 'page_delay'):
                                page_delay = network_delay.page_delay
                        # 从Pydantic模型或字典中获取延迟配置
                        min_delay = 1
                        max_delay = 3
                        if isinstance(page_delay, dict):
                            min_delay = page_delay.get('min', 1)
                            max_delay = page_delay.get('max', 3)
                        else:
                            if hasattr(page_delay, 'min'):
                                min_delay = page_delay.min
                            if hasattr(page_delay, 'max'):
                                max_delay = page_delay.max
                                
                        delay_time = random.uniform(min_delay, max_delay)
                        await asyncio.sleep(delay_time)
                        
                    except Exception as e:
                        self.logger.error(f"爬取分类 {category_name} > {subcategory_name} 第 {page} 页时出错: {str(e)}")
                        self.stats["error_count"] += 1
                
                # 分类间延迟
                category_delay = {}
                if hasattr(self.network, 'delay'):
                    network_delay = self.network.delay
                    if hasattr(network_delay, 'category_delay'):
                        category_delay = network_delay.category_delay
                
                # 安全获取分类延迟配置
                min_delay = 3
                max_delay = 5
                if isinstance(category_delay, dict):
                    min_delay = category_delay.get('min', 3)
                    max_delay = category_delay.get('max', 5)
                else:
                    if hasattr(category_delay, 'min'):
                        min_delay = category_delay.min
                    if hasattr(category_delay, 'max'):
                        max_delay = category_delay.max
                        
                delay_time = random.uniform(min_delay, max_delay)
                await asyncio.sleep(delay_time)
        
        self.logger.info(f"分类 {category_name} 爬取完成，共获取 {len(all_results)} 条数据")
        return all_results
    
    async def run(self):
        """
        运行爬虫
        
        Returns:
            Dict: 爬取结果和统计信息
        """
        self.logger.info(f"开始运行 {self.site_name} 爬虫")
        self.stats["start_time"] = time.time()
        
        all_results = []
        
        try:
            # 启动性能监控
            monitor_task = asyncio.create_task(self._monitor_performance())
            
            # 初始化浏览器
            await self._init_browser()
            
            # 获取分类配置
            categories = []
            if hasattr(self.scraping, 'categories'):
                categories = self.scraping.categories
            
            # 如果没有分类配置，则直接爬取基础URL
            if not categories:
                self.logger.info(f"未配置分类，直接爬取基础URL: {self.base_url}")
                
                # 导航到基础URL
                success = await self._with_retry(self._navigate_to_url, self.base_url)
                if success:
                    # 执行交互操作
                    interactions = []
                    if hasattr(self.scraping, 'interactions'):
                        interactions = self.scraping.interactions
                    for action in interactions:
                        await self._with_retry(self._perform_action, action)
                    
                    # 提取数据
                    selector = ''
                    if hasattr(self.parsing, 'product_list_selector'):
                        selector = self.parsing.product_list_selector
                        
                    field_selectors = {}
                    if hasattr(self.parsing, 'list_field_selectors'):
                        field_selectors = self.parsing.list_field_selectors
                    
                    results = await self._with_retry(self._extract_data, selector, field_selectors)
                    all_results.extend(results)
            else:
                # 如果有分类配置，则按分类爬取
                for category in categories:
                    category_results = await self.crawl_category(category)
                    all_results.extend(category_results)
            
            # 保存数据
            if all_results:
                self.stats["success_count"] = len(all_results)
                self.stats["total_items"] = len(all_results)
                output_path = await self._save_data(all_results)
                self.logger.info(f"数据已保存到: {output_path}")
            else:
                self.logger.warning("未爬取到数据")
            
            # 停止性能监控
            monitor_task.cancel()
            performance_stats = await monitor_task
            
        except Exception as e:
            self.logger.error(f"爬取过程中出错: {str(e)}")
            self.stats["error_count"] += 1
            raise
        finally:
            # 关闭浏览器
            await self._close_browser()
            
            # 记录结束时间和总耗时
            self.stats["end_time"] = time.time()
            self.stats["duration"] = self.stats["end_time"] - self.stats["start_time"]
            
            self.logger.info(f"爬取完成，耗时 {self.stats['duration']:.2f} 秒")
            self.logger.info(f"统计信息: 成功 {self.stats['success_count']} 项，错误 {self.stats['error_count']} 项，重试 {self.stats['retry_count']} 次")
        
        return {
            "results": all_results,
            "stats": self.stats
        }


async def main():
    """
    主函数
    """
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Playwright 网页爬虫')
    parser.add_argument('--config', type=str, required=True, help='配置文件路径')
    parser.add_argument('--output-dir', type=str, help='输出目录')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    parser.add_argument('--headless', action='store_true', help='无头模式运行')
    parser.add_argument('--disable-proxy', action='store_true', help='禁用代理')
    parser.add_argument('--disable-stealth', action='store_true', help='禁用浏览器指纹伪装')
    parser.add_argument('--max-pages', type=int, help='最大爬取页数')
    parser.add_argument('--max-products', type=int, help='最大爬取商品数')
    parser.add_argument('--disable-captcha', action='store_true', help='禁用验证码自动处理')
    
    args = parser.parse_args()
    
    # 读取配置文件
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"错误: 配置文件 {config_path} 不存在")
        return 1
    
    # 创建爬虫实例
    scraper = PlaywrightScraper(config_path, output_dir=args.output_dir, log_level=args.log_level)
    
    # 应用命令行参数覆盖配置
    if args.headless:
        scraper.browser_config.headless = True
    
    if args.disable_proxy:
        scraper.proxy_config.enable = False
    
    if args.disable_stealth:
        scraper.browser_config.stealth = False
    
    if args.disable_captcha:
        scraper.captcha_config.enable = False
    
    if args.max_pages and hasattr(scraper, 'scraping'):
        if 'product_list' not in scraper.scraping:
            scraper.scraping['product_list'] = {}
        scraper.scraping['product_list']['max_pages'] = args.max_pages
    
    if args.max_products and hasattr(scraper, 'scraping'):
        if 'product_detail' not in scraper.scraping:
            scraper.scraping['product_detail'] = {}
        scraper.scraping['product_detail']['max_products'] = args.max_products
        
    # 运行爬虫
    try:
        result = await scraper.run()
        print(f"爬取完成，共获取 {len(result['results'])} 条数据")
        print(f"统计信息: {json.dumps(result['stats'], ensure_ascii=False, indent=2)}")
        return 0
    except Exception as e:
        print(f"爬虫运行出错: {str(e)}")
        return 1

if __name__ == "__main__":
    import asyncio
    import sys
    
    # 运行异步主函数
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
