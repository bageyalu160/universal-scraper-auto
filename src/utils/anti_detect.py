#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反爬虫检测和规避工具模块

提供浏览器指纹伪装、验证码处理、请求头生成等功能，
帮助爬虫绕过常见的反爬机制。
"""

import os
import json
import random
import logging
import string
import time
import re
import math
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from datetime import datetime
from pathlib import Path
import hashlib
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/anti_detect.log')
    ]
)
logger = logging.getLogger('anti_detect')

# 浏览器指纹数据目录
DATA_DIR = Path('data/fingerprints')
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 验证码临时存储目录
CAPTCHA_DIR = Path('temp/captchas')
CAPTCHA_DIR.mkdir(parents=True, exist_ok=True)

# 导入代理池工具（如果存在）
try:
    from .proxy_pool import get_proxy, report_proxy_status
    PROXY_AVAILABLE = True
except ImportError:
    logger.warning("代理池模块未找到，将禁用代理相关功能")
    PROXY_AVAILABLE = False

class UserAgentManager:
    """用户代理管理类，提供随机合理的UA"""
    
    # 常用浏览器及其版本范围
    BROWSERS = {
        'chrome': {
            'name': 'Chrome',
            'min_version': 90,
            'max_version': 116,
            'template': 'Mozilla/5.0 ({os}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36'
        },
        'firefox': {
            'name': 'Firefox',
            'min_version': 90,
            'max_version': 111,
            'template': 'Mozilla/5.0 ({os}; rv:{version}.0) Gecko/20100101 Firefox/{version}.0'
        },
        'edge': {
            'name': 'Edge',
            'min_version': 90,
            'max_version': 111,
            'template': 'Mozilla/5.0 ({os}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36 Edg/{version}'
        },
        'safari': {
            'name': 'Safari',
            'min_version': 14,
            'max_version': 16,
            'template': 'Mozilla/5.0 ({mac_os}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15'
        }
    }
    
    # 操作系统模板
    OS_TEMPLATES = {
        'windows': 'Windows NT {windows_version}',
        'mac': 'Macintosh; Intel Mac OS X {mac_version}',
        'linux': 'X11; Linux x86_64',
        'android': 'Linux; Android {android_version}; {android_device}',
        'ios': 'iPhone; CPU iPhone OS {ios_version} like Mac OS X'
    }
    
    # 具体版本映射
    WINDOWS_VERSIONS = ['10.0', '11.0']
    MAC_VERSIONS = ['10_15', '11_0', '12_0', '13_0']
    ANDROID_VERSIONS = ['10', '11', '12', '13']
    IOS_VERSIONS = ['14_0', '15_0', '16_0']
    ANDROID_DEVICES = [
        'SM-G981B', 'SM-G986B', 'SM-G988B',  # Samsung Galaxy S20 系列
        'SM-G991B', 'SM-G996B', 'SM-G998B',  # Samsung Galaxy S21 系列
        'SM-S901B', 'SM-S906B', 'SM-S908B',  # Samsung Galaxy S22 系列
        'Pixel 5', 'Pixel 6', 'Pixel 7',      # Google Pixel 系列
        'M2102J20SG', 'M2012K11AG', 'M2007J3SG'  # Xiaomi 系列
    ]
    
    def __init__(self):
        """初始化用户代理管理器"""
        self.ua_cache = {}  # 用于缓存生成的UA
    
    def _generate_windows_ua(self, browser_type='chrome'):
        """生成Windows系统的用户代理"""
        browser = self.BROWSERS[browser_type]
        version = random.randint(browser['min_version'], browser['max_version'])
        chrome_version = random.randint(90, 116) if browser_type == 'edge' else version
        windows_version = random.choice(self.WINDOWS_VERSIONS)
        
        os_string = self.OS_TEMPLATES['windows'].format(windows_version=windows_version)
        
        if browser_type == 'edge':
            return browser['template'].format(os=os_string, chrome_version=chrome_version, version=version)
        else:
            return browser['template'].format(os=os_string, version=version)
    
    def _generate_mac_ua(self, browser_type='safari'):
        """生成Mac系统的用户代理"""
        browser = self.BROWSERS[browser_type]
        version = random.randint(browser['min_version'], browser['max_version'])
        mac_version = random.choice(self.MAC_VERSIONS)
        
        os_string = self.OS_TEMPLATES['mac'].format(mac_version=mac_version)
        
        if browser_type == 'safari':
            return browser['template'].format(mac_os=os_string, version=f'{version}.0')
        else:
            return browser['template'].format(os=os_string, version=version)
    
    def _generate_mobile_ua(self, os_type='android'):
        """生成移动设备的用户代理"""
        if os_type == 'android':
            browser_type = 'chrome'
            browser = self.BROWSERS[browser_type]
            version = random.randint(browser['min_version'], browser['max_version'])
            android_version = random.choice(self.ANDROID_VERSIONS)
            android_device = random.choice(self.ANDROID_DEVICES)
            
            os_string = self.OS_TEMPLATES['android'].format(
                android_version=android_version,
                android_device=android_device
            )
            
            return browser['template'].format(os=os_string, version=version)
        else:  # iOS
            browser_type = 'safari'
            browser = self.BROWSERS[browser_type]
            version = random.randint(browser['min_version'], browser['max_version'])
            ios_version = random.choice(self.IOS_VERSIONS)
            
            os_string = self.OS_TEMPLATES['ios'].format(ios_version=ios_version)
            
            return browser['template'].format(mac_os=os_string, version=f'{version}.0')
    
    def get_random_ua(self, device_type=None, browser_type=None, consistent=False, key=None):
        """
        获取随机用户代理
        
        Args:
            device_type: 设备类型，可选 'desktop' 或 'mobile'，默认随机
            browser_type: 浏览器类型，可选 'chrome', 'firefox', 'edge', 'safari'，默认随机
            consistent: 是否返回一致的UA，如果为True则相同key返回相同UA
            key: 缓存键，用于consistent=True时
            
        Returns:
            str: 用户代理字符串
        """
        # 如果需要一致的UA且有key，尝试从缓存获取
        cache_key = f"{device_type}_{browser_type}_{key}"
        if consistent and key and cache_key in self.ua_cache:
            return self.ua_cache[cache_key]
        
        # 随机设备类型
        if not device_type:
            device_type = random.choice(['desktop', 'mobile'])
        
        # 根据设备类型确定浏览器选项
        if device_type == 'desktop':
            browser_options = ['chrome', 'firefox', 'edge', 'safari']
            if not browser_type or browser_type not in browser_options:
                browser_type = random.choice(browser_options)
            
            # 生成桌面UA
            if browser_type in ['chrome', 'firefox', 'edge']:
                ua = self._generate_windows_ua(browser_type)
            else:  # safari
                ua = self._generate_mac_ua(browser_type)
        else:  # mobile
            os_options = ['android', 'ios']
            os_type = random.choice(os_options)
            
            # 根据移动操作系统确定浏览器
            if os_type == 'android':
                browser_type = 'chrome'
            else:  # ios
                browser_type = 'safari'
            
            # 生成移动UA
            ua = self._generate_mobile_ua(os_type)
        
        # 如果需要一致的UA且有key，存入缓存
        if consistent and key:
            self.ua_cache[cache_key] = ua
        
        return ua

class BrowserFingerprintManager:
    """浏览器指纹管理，提供一致的浏览器参数"""
    
    def __init__(self):
        """初始化浏览器指纹管理器"""
        self.ua_manager = UserAgentManager()
        self.fingerprints = {}
    
    def _generate_headers(self, user_agent):
        """根据UA生成匹配的请求头"""
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # 根据UA调整某些头部
        if 'Chrome' in user_agent:
            headers['sec-ch-ua'] = '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"'
            headers['sec-ch-ua-mobile'] = '?0'
            headers['sec-ch-ua-platform'] = '"Windows"' if 'Windows' in user_agent else '"macOS"'
        
        return headers
    
    def _generate_browser_params(self, user_agent):
        """生成与UA匹配的浏览器参数，用于Playwright等"""
        params = {}
        
        # 根据UA设置设备信息
        is_mobile = 'Android' in user_agent or 'iPhone' in user_agent
        is_windows = 'Windows' in user_agent
        is_mac = 'Mac OS X' in user_agent and 'iPhone' not in user_agent
        
        # 设置视口大小
        if is_mobile:
            params['viewport'] = {'width': random.randint(360, 428), 'height': random.randint(640, 926)}
        else:
            params['viewport'] = {'width': random.randint(1024, 1920), 'height': random.randint(768, 1080)}
        
        # 设置用户代理
        params['user_agent'] = user_agent
        
        # 设置平台信息
        if is_windows:
            params['platform'] = 'Windows'
        elif is_mac:
            params['platform'] = 'Darwin'
        elif 'Android' in user_agent:
            params['platform'] = 'Android'
        elif 'iPhone' in user_agent:
            params['platform'] = 'iOS'
        else:
            params['platform'] = 'Linux'
        
        # 设置语言
        params['locale'] = random.choice(['zh-CN', 'en-US', 'en-GB', 'zh-TW'])
        
        # 设置时区
        params['timezone_id'] = random.choice([
            'Asia/Shanghai', 'America/New_York', 'Europe/London', 
            'Asia/Tokyo', 'Australia/Sydney'
        ])
        
        # 设置设备内存
        params['device_memory'] = random.choice([2, 4, 8, 16])
        
        # 设置硬件并发
        params['hardware_concurrency'] = random.choice([2, 4, 8, 12, 16])
        
        return params
    
    def get_fingerprint(self, fp_id=None, regenerate=False):
        """
        获取一个一致的浏览器指纹
        
        Args:
            fp_id: 指纹ID，用于获取相同的指纹
            regenerate: 是否重新生成指纹，即使缓存中存在
            
        Returns:
            dict: 包含浏览器指纹信息的字典
        """
        # 如果没有指定ID，生成一个随机ID
        if not fp_id:
            fp_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # 如果需要重新生成或者缓存中不存在，生成新指纹
        if regenerate or fp_id not in self.fingerprints:
            # 随机决定是桌面还是移动设备
            device_type = random.choice(['desktop', 'mobile'])
            
            # 生成用户代理
            user_agent = self.ua_manager.get_random_ua(device_type=device_type, consistent=True, key=fp_id)
            
            # 生成浏览器头和参数
            headers = self._generate_headers(user_agent)
            browser_params = self._generate_browser_params(user_agent)
            
            # 创建指纹
            fingerprint = {
                'id': fp_id,
                'user_agent': user_agent,
                'headers': headers,
                'browser_params': browser_params,
                'created_at': datetime.now().isoformat(),
            }
            
            # 缓存指纹
            self.fingerprints[fp_id] = fingerprint
        
        return self.fingerprints[fp_id]
    
    def get_playwright_options(self, fp_id=None):
        """
        获取用于Playwright的浏览器选项
        
        Args:
            fp_id: 指纹ID
            
        Returns:
            dict: Playwright浏览器选项
        """
        fingerprint = self.get_fingerprint(fp_id)
        browser_params = fingerprint['browser_params']
        
        options = {
            'user_agent': browser_params['user_agent'],
            'viewport': browser_params['viewport'],
            'locale': browser_params['locale'],
            'timezone_id': browser_params['timezone_id'],
            'device_scale_factor': 1.0,
            'is_mobile': 'Android' in browser_params['user_agent'] or 'iPhone' in browser_params['user_agent'],
            'has_touch': 'Android' in browser_params['user_agent'] or 'iPhone' in browser_params['user_agent'],
        }
        
        return options
    
    def get_selenium_options(self, fp_id=None, browser_type='chrome'):
        """
        获取用于Selenium的浏览器选项
        
        Args:
            fp_id: 指纹ID
            browser_type: 浏览器类型
            
        Returns:
            dict: Selenium浏览器配置
        """
        fingerprint = self.get_fingerprint(fp_id)
        
        options = {
            'user_agent': fingerprint['user_agent'],
            'arguments': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                f'--window-size={fingerprint["browser_params"]["viewport"]["width"]},{fingerprint["browser_params"]["viewport"]["height"]}',
            ],
            'preferences': {},
            'experimental_options': {
                'excludeSwitches': ['enable-automation'],
                'useAutomationExtension': False
            }
        }
        
        # Chrome特定选项
        if browser_type.lower() == 'chrome':
            options['experimental_options']['prefs'] = {
                'intl.accept_languages': fingerprint['browser_params']['locale'],
                'profile.default_content_setting_values.notifications': 2,  # 禁用通知
            }
        
        return options

class DelayManager:
    """
    请求延迟管理器
    
    特性：
    - 基于正态分布的随机延迟
    - 自适应延迟，根据响应状态自动调整
    - 支持动态调整延迟策略
    """
    
    # 预设延迟策略
    DELAY_STRATEGIES = {
        'ultra_fast': {
            'base_delay': 0.1,  # 基础延迟时间（秒）
            'variance': 0.05,   # 波动范围
            'increment': 0.05,  # 检测到阻塞时的增量
            'max_delay': 0.5    # 最大延迟
        },
        'fast': {
            'base_delay': 0.5,
            'variance': 0.2,
            'increment': 0.1,
            'max_delay': 2.0
        },
        'normal': {
            'base_delay': 1.0,
            'variance': 0.5,
            'increment': 0.3,
            'max_delay': 5.0
        },
        'slow': {
            'base_delay': 2.0,
            'variance': 1.0,
            'increment': 0.5,
            'max_delay': 10.0
        },
        'stealth': {
            'base_delay': 3.0,
            'variance': 2.0,
            'increment': 1.0,
            'max_delay': 20.0
        }
    }
    
    def __init__(self, strategy='normal', custom_strategy=None):
        """
        初始化延迟管理器
        
        Args:
            strategy (str): 预设策略名称，可选 'ultra_fast', 'fast', 'normal', 'slow', 'stealth'
            custom_strategy (dict): 自定义策略，优先于预设策略
        """
        if custom_strategy:
            self.strategy = custom_strategy
        else:
            if strategy not in self.DELAY_STRATEGIES:
                logger.warning(f"未知延迟策略 '{strategy}'，使用 'normal' 策略替代")
                strategy = 'normal'
            
            self.strategy = self.DELAY_STRATEGIES[strategy]
        
        self.current_delay = self.strategy['base_delay']
        self.consecutive_failures = 0
        logger.info(f"延迟管理器初始化，使用策略: {strategy}, 基础延迟: {self.current_delay}秒")
    
    def get_delay(self) -> float:
        """
        获取下一次请求应该使用的延迟时间
        
        Returns:
            float: 推荐的延迟时间（秒）
        """
        # 使用正态分布生成随机延迟，使延迟更贴近真实人类行为
        variance = self.strategy['variance']
        delay = random.normalvariate(self.current_delay, variance)
        
        # 确保延迟在合理范围内
        delay = max(0.1, min(delay, self.strategy['max_delay']))
        
        return delay
    
    def delay(self):
        """执行延迟"""
        sleep_time = self.get_delay()
        logger.debug(f"延迟 {sleep_time:.2f} 秒")
        time.sleep(sleep_time)
    
    def report_success(self):
        """报告成功请求，可能降低延迟"""
        if self.consecutive_failures > 0:
            self.consecutive_failures = 0
        
        # 成功后稍微降低延迟，但不低于基础延迟
        if self.current_delay > self.strategy['base_delay']:
            self.current_delay = max(
                self.strategy['base_delay'],
                self.current_delay - self.strategy['increment'] / 2
            )
    
    def report_failure(self, is_blocking=False):
        """
        报告失败请求，增加延迟
        
        Args:
            is_blocking (bool): 是否因为被阻塞而失败
        """
        self.consecutive_failures += 1
        
        # 阻塞失败比普通失败增加更多延迟
        if is_blocking:
            multiplier = min(self.consecutive_failures, 5)  # 最多5倍增量
            self.current_delay += self.strategy['increment'] * multiplier
        else:
            self.current_delay += self.strategy['increment']
        
        # 确保不超过最大延迟
        self.current_delay = min(self.current_delay, self.strategy['max_delay'])
        
        logger.debug(f"增加延迟至 {self.current_delay:.2f} 秒, 连续失败: {self.consecutive_failures}")
    
    def reset(self):
        """重置延迟到初始状态"""
        self.current_delay = self.strategy['base_delay']
        self.consecutive_failures = 0

class CaptchaSolver:
    """验证码处理类，提供多种验证码识别方法"""
    
    def __init__(self, config=None):
        """
        初始化验证码处理器
        
        Args:
            config: 配置字典，包含API密钥等
        """
        self.config = config or {}
        self.providers = self.config.get('providers', [])
        self.default_provider = self.config.get('default_provider', 'local')
    
    def solve_text_captcha(self, image_path=None, image_base64=None, provider=None):
        """
        解决文本验证码
        
        Args:
            image_path: 验证码图片路径
            image_base64: 验证码图片的Base64编码
            provider: 使用的服务提供商
            
        Returns:
            str: 识别结果
        """
        provider = provider or self.default_provider
        
        # 根据提供商调用不同的解决方法
        if provider == 'local':
            return self._solve_locally(image_path, image_base64)
        elif provider == '2captcha':
            return self._solve_with_2captcha(image_path, image_base64)
        elif provider == 'anti-captcha':
            return self._solve_with_anticaptcha(image_path, image_base64)
        else:
            logger.error(f"不支持的验证码服务提供商: {provider}")
            return None
    
    def _solve_locally(self, image_path, image_base64):
        """本地解决验证码（依赖于本地OCR库）"""
        logger.info("尝试使用本地OCR识别验证码")
        
        try:
            # 尝试导入Tesseract OCR
            import pytesseract
            from PIL import Image
            import io
            import base64
            
            # 从路径或Base64加载图片
            if image_path:
                img = Image.open(image_path)
            elif image_base64:
                img_data = base64.b64decode(image_base64)
                img = Image.open(io.BytesIO(img_data))
            else:
                logger.error("未提供图片路径或Base64数据")
                return None
            
            # 预处理图片（可选）
            # img = img.convert('L')  # 转为灰度
            # img = img.point(lambda x: 0 if x < 128 else 255, '1')  # 二值化
            
            # 识别文本
            text = pytesseract.image_to_string(img, config='--psm 8 --oem 3')
            text = text.strip()
            
            logger.info(f"本地OCR识别结果: {text}")
            return text
        except ImportError:
            logger.error("本地OCR缺少依赖库: pytesseract")
            return None
        except Exception as e:
            logger.error(f"本地OCR识别出错: {e}")
            return None
    
    def _solve_with_2captcha(self, image_path, image_base64):
        """使用2Captcha服务解决验证码"""
        logger.info("尝试使用2Captcha服务识别验证码")
        
        # 获取API密钥
        api_key = self._get_api_key('2captcha')
        if not api_key:
            logger.error("未配置2Captcha API密钥")
            return None
        
        try:
            import base64
            import requests
            import time
            
            # 准备图片数据
            if image_path:
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
            elif image_base64:
                image_data = image_base64
            else:
                logger.error("未提供图片路径或Base64数据")
                return None
            
            # 发送验证码到2Captcha
            url = 'https://2captcha.com/in.php'
            data = {
                'key': api_key,
                'method': 'base64',
                'body': image_data,
                'json': 1
            }
            
            response = requests.post(url, data=data)
            result = response.json()
            
            if result['status'] == 1:
                request_id = result['request']
                logger.info(f"2Captcha已接收验证码，请求ID: {request_id}")
                
                # 等待验证码解决
                url = f'https://2captcha.com/res.php?key={api_key}&action=get&id={request_id}&json=1'
                
                for _ in range(30):  # 最多等待30次，每次5秒
                    time.sleep(5)
                    response = requests.get(url)
                    result = response.json()
                    
                    if result['status'] == 1:
                        text = result['request']
                        logger.info(f"2Captcha识别结果: {text}")
                        return text
                    elif result['request'] != 'CAPCHA_NOT_READY':
                        logger.error(f"2Captcha识别失败: {result['request']}")
                        return None
                
                logger.error("2Captcha识别超时")
                return None
            else:
                logger.error(f"提交到2Captcha失败: {result['request']}")
                return None
        except Exception as e:
            logger.error(f"2Captcha识别出错: {e}")
            return None
    
    def _solve_with_anticaptcha(self, image_path, image_base64):
        """使用Anti-Captcha服务解决验证码"""
        logger.info("尝试使用Anti-Captcha服务识别验证码")
        
        # 获取API密钥
        api_key = self._get_api_key('anti-captcha')
        if not api_key:
            logger.error("未配置Anti-Captcha API密钥")
            return None
        
        try:
            import base64
            import requests
            import time
            
            # 准备图片数据
            if image_path:
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
            elif image_base64:
                image_data = image_base64
            else:
                logger.error("未提供图片路径或Base64数据")
                return None
            
            # 发送验证码到Anti-Captcha
            url = 'https://api.anti-captcha.com/createTask'
            data = {
                'clientKey': api_key,
                'task': {
                    'type': 'ImageToTextTask',
                    'body': image_data,
                    'phrase': False,
                    'case': True,
                    'numeric': 0,
                    'math': False,
                    'minLength': 0,
                    'maxLength': 0
                }
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if result['errorId'] == 0:
                task_id = result['taskId']
                logger.info(f"Anti-Captcha已接收验证码，任务ID: {task_id}")
                
                # 等待验证码解决
                url = 'https://api.anti-captcha.com/getTaskResult'
                data = {
                    'clientKey': api_key,
                    'taskId': task_id
                }
                
                for _ in range(30):  # 最多等待30次，每次5秒
                    time.sleep(5)
                    response = requests.post(url, json=data)
                    result = response.json()
                    
                    if result['errorId'] == 0 and result['status'] == 'ready':
                        text = result['solution']['text']
                        logger.info(f"Anti-Captcha识别结果: {text}")
                        return text
                
                logger.error("Anti-Captcha识别超时")
                return None
            else:
                logger.error(f"提交到Anti-Captcha失败: {result['errorDescription']}")
                return None
        except Exception as e:
            logger.error(f"Anti-Captcha识别出错: {e}")
            return None
    
    def _get_api_key(self, provider):
        """获取API密钥"""
        for p in self.providers:
            if p.get('name') == provider:
                return p.get('api_key')
        return None

class RequestPatternManager:
    """
    请求模式管理器，模拟真实用户的浏览行为
    
    功能：
    - 随机化请求顺序
    - 模拟用户浏览行为（如先访问首页，再访问内页）
    - 动态调整请求频率
    - 处理Cookie和会话状态
    """
    
    def __init__(self, site_name='unknown', config=None):
        """
        初始化请求模式管理器
        
        Args:
            site_name (str): 网站名称，用于记录和统计
            config (dict): 配置字典
        """
        self.site_name = site_name
        self.config = config or {}
        self.session_id = f"{site_name}_{int(time.time())}_{random.randint(1000, 9999)}"
        self.delay_manager = DelayManager(
            strategy=self.config.get('delay_strategy', 'normal'),
            custom_strategy=self.config.get('custom_delay', None)
        )
        self.visit_count = 0
        self.page_history = []
        self.last_visit_time = 0
        self.blocking_patterns = self.config.get('blocking_patterns', [
            r'robot', r'captcha', r'blocked', r'banned', r'security check',
            r'unusual activity', r'suspicious', r'too many requests'
        ])
        
        # 代理轮换策略
        self.proxy_config = self.config.get('proxy', {})
        self.proxy_rotation_count = self.proxy_config.get('rotation_count', 5)  # 多少次请求后轮换代理
        self.rotate_on_failure = self.proxy_config.get('rotate_on_failure', True)  # 失败时是否轮换代理
        self.current_proxy = None
        self.proxy_request_count = 0
        
        logger.info(f"请求模式管理器初始化，站点: {site_name}, 会话ID: {self.session_id}")
    
    def prepare_request(self, url, headers=None, previous_url=None):
        """
        准备请求参数，包括代理、UA、Referer等
        
        Args:
            url (str): 请求URL
            headers (dict): 自定义头部
            previous_url (str): 上一个访问的URL，用于设置Referer
            
        Returns:
            dict: 请求参数
        """
        request_args = {}
        headers = headers or {}
        
        # 添加Referer模拟正常浏览行为
        if previous_url:
            headers['Referer'] = previous_url
        elif self.page_history and random.random() < 0.95:  # 95%的概率带Referer
            headers['Referer'] = random.choice(self.page_history[-3:] if len(self.page_history) > 3 else self.page_history)
        
        # 使用代理池
        if PROXY_AVAILABLE and self.proxy_config.get('enabled', False):
            # 检查是否需要轮换代理
            if not self.current_proxy or self.proxy_request_count >= self.proxy_rotation_count:
                self.current_proxy = get_proxy(rotate=True)
                self.proxy_request_count = 0
                logger.debug(f"轮换代理: {self.current_proxy}")
            
            self.proxy_request_count += 1
            request_args['proxies'] = self.current_proxy
        
        # 添加请求头
        request_args['headers'] = headers
        
        # 模拟请求间延迟
        current_time = time.time()
        elapsed = current_time - self.last_visit_time
        
        # 如果距离上次请求时间不够长，则延迟
        min_delay = self.delay_manager.get_delay()
        if elapsed < min_delay:
            delay_needed = min_delay - elapsed
            logger.debug(f"请求延迟: {delay_needed:.2f}秒")
            time.sleep(delay_needed)
        
        self.last_visit_time = time.time()
        return request_args
    
    def process_response(self, response, url):
        """
        处理响应，检测是否被封锁，更新统计信息
        
        Args:
            response: 响应对象
            url (str): 请求的URL
            
        Returns:
            bool: 是否被检测/封锁
        """
        self.visit_count += 1
        self.page_history.append(url)
        
        # 检查是否被封锁
        is_blocked = False
        
        # 检查状态码
        if response.status_code in [403, 429, 503]:
            is_blocked = True
            logger.warning(f"检测到可能的封锁 (状态码: {response.status_code})")
        
        # 检查响应内容中是否包含封锁关键词
        if not is_blocked and hasattr(response, 'text'):
            text = response.text.lower()
            for pattern in self.blocking_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    is_blocked = True
                    logger.warning(f"检测到可能的封锁 (匹配模式: {pattern})")
                    break
        
        # 调整延迟和代理
        if is_blocked:
            self.delay_manager.report_failure(is_blocking=True)
            
            # 如果启用了代理且配置了失败时轮换，则更换代理
            if PROXY_AVAILABLE and self.proxy_config.get('enabled', False) and self.rotate_on_failure:
                if self.current_proxy:
                    report_proxy_status(self.current_proxy, success=False)
                self.current_proxy = get_proxy(rotate=True)
                self.proxy_request_count = 0
                logger.info(f"遇到封锁，轮换代理: {self.current_proxy}")
        else:
            self.delay_manager.report_success()
            
            # 报告代理使用成功
            if PROXY_AVAILABLE and self.proxy_config.get('enabled', False) and self.current_proxy:
                report_proxy_status(self.current_proxy, success=True)
        
        return is_blocked
    
    def randomize_requests(self, urls, max_requests=None):
        """
        随机化请求顺序，模拟真实用户行为
        
        Args:
            urls (list): URL列表
            max_requests (int): 最大请求数量
            
        Returns:
            list: 重新排序的URL列表
        """
        if not urls:
            return []
        
        # 限制请求数量
        if max_requests and max_requests < len(urls):
            urls = random.sample(urls, max_requests)
        
        # 复制URL列表避免修改原始数据
        urls = urls.copy()
        
        # 模拟真实用户的浏览模式，可能会先浏览主要页面，然后是次要页面
        if len(urls) > 3 and random.random() < 0.7:  # 70%的概率使用特殊顺序
            # 打乱顺序但保持一些聚集
            clusters = []
            while urls:
                # 取一个随机的起始URL
                start_idx = random.randint(0, len(urls)-1)
                start_url = urls.pop(start_idx)
                
                # 创建一个聚集，大小在1到min(5, 剩余URLs)之间
                cluster_size = min(5, len(urls))
                if cluster_size > 0:
                    cluster_size = random.randint(1, cluster_size)
                    cluster = [start_url]
                    
                    for _ in range(cluster_size):
                        if not urls:
                            break
                        idx = random.randint(0, len(urls)-1)
                        cluster.append(urls.pop(idx))
                    
                    clusters.append(cluster)
                else:
                    clusters.append([start_url])
            
            # 展平聚集
            result = []
            for cluster in clusters:
                result.extend(cluster)
            return result
        else:
            # 简单地随机排序
            random.shuffle(urls)
            return urls
    
    def execute_with_retry(self, request_func, url, max_retries=3, **kwargs):
        """
        使用重试机制执行请求
        
        Args:
            request_func (callable): 请求函数
            url (str): 请求URL
            max_retries (int): 最大重试次数
            **kwargs: 传递给请求函数的其他参数
            
        Returns:
            tuple: (响应对象, 是否成功)
        """
        retries = 0
        while retries <= max_retries:
            try:
                # 准备请求参数
                previous_url = self.page_history[-1] if self.page_history else None
                request_args = self.prepare_request(url, previous_url=previous_url)
                
                # 合并自定义参数
                for key, value in kwargs.items():
                    if key == 'headers' and 'headers' in request_args:
                        # 合并头部
                        request_args['headers'].update(value)
                    else:
                        request_args[key] = value
                
                # 执行请求
                response = request_func(url, **request_args)
                
                # 处理响应
                is_blocked = self.process_response(response, url)
                
                if is_blocked:
                    retries += 1
                    if retries <= max_retries:
                        logger.warning(f"检测到封锁，将在{self.delay_manager.current_delay:.1f}秒后重试 ({retries}/{max_retries})")
                        time.sleep(self.delay_manager.current_delay)
                        continue
                    else:
                        logger.error(f"达到最大重试次数({max_retries})，无法绕过封锁")
                        return response, False
                
                return response, True
                
            except Exception as e:
                retries += 1
                logger.error(f"请求异常: {str(e)}, 重试 ({retries}/{max_retries})")
                
                # 请求失败，报告并延迟
                self.delay_manager.report_failure()
                
                # 如果启用了代理且配置了失败时轮换，则更换代理
                if PROXY_AVAILABLE and self.proxy_config.get('enabled', False) and self.rotate_on_failure:
                    if self.current_proxy:
                        report_proxy_status(self.current_proxy, success=False)
                    self.current_proxy = get_proxy(rotate=True)
                    self.proxy_request_count = 0
                    logger.info(f"请求失败，轮换代理: {self.current_proxy}")
                
                if retries <= max_retries:
                    time.sleep(self.delay_manager.current_delay)
                else:
                    logger.error(f"达到最大重试次数({max_retries})，放弃请求")
                    return None, False
        
        return None, False

# 创建全局实例
_ua_manager = UserAgentManager()
_fp_manager = BrowserFingerprintManager()
_captcha_solver = None

def get_user_agent(device_type=None, browser_type=None, consistent=False, key=None):
    """
    获取随机用户代理字符串
    
    Args:
        device_type: 设备类型，可选 'desktop' 或 'mobile'，默认随机
        browser_type: 浏览器类型，可选 'chrome', 'firefox', 'edge', 'safari'，默认随机
        consistent: 是否返回一致的UA，如果为True则相同key返回相同UA
        key: 缓存键，用于consistent=True时
        
    Returns:
        str: 用户代理字符串
    """
    global _ua_manager
    return _ua_manager.get_random_ua(device_type, browser_type, consistent, key)

def get_browser_fingerprint(fp_id=None, regenerate=False):
    """
    获取浏览器指纹
    
    Args:
        fp_id: 指纹ID，用于获取相同的指纹
        regenerate: 是否重新生成指纹，即使缓存中存在
        
    Returns:
        dict: 包含浏览器指纹信息的字典
    """
    global _fp_manager
    return _fp_manager.get_fingerprint(fp_id, regenerate)

def get_playwright_options(fp_id=None):
    """
    获取用于Playwright的浏览器选项
    
    Args:
        fp_id: 指纹ID
        
    Returns:
        dict: Playwright浏览器选项
    """
    global _fp_manager
    return _fp_manager.get_playwright_options(fp_id)

def get_selenium_options(fp_id=None, browser_type='chrome'):
    """
    获取用于Selenium的浏览器选项
    
    Args:
        fp_id: 指纹ID
        browser_type: 浏览器类型
        
    Returns:
        dict: Selenium浏览器配置
    """
    global _fp_manager
    return _fp_manager.get_selenium_options(fp_id, browser_type)

def solve_captcha(image_path=None, image_base64=None, provider=None, config=None):
    """
    解决验证码
    
    Args:
        image_path: 验证码图片路径
        image_base64: 验证码图片的Base64编码
        provider: 使用的服务提供商
        config: 配置信息，用于初始化CaptchaSolver
        
    Returns:
        str: 识别结果
    """
    global _captcha_solver
    if _captcha_solver is None:
        _captcha_solver = CaptchaSolver(config)
    
    return _captcha_solver.solve_text_captcha(image_path, image_base64, provider)

def create_delay_manager(strategy='normal', custom_strategy=None):
    """创建延迟管理器"""
    return DelayManager(strategy, custom_strategy)

def create_request_pattern_manager(site_name='unknown', config=None):
    """创建请求模式管理器"""
    return RequestPatternManager(site_name, config)

def get_timezone_name(offset_minutes: int) -> str:
    """
    根据时区偏移量获取时区名称
    
    Args:
        offset_minutes: 与UTC的偏移分钟数
        
    Returns:
        str: 时区名称
    """
    # 常见时区映射表
    timezone_map = {
        -480: "America/Los_Angeles",  # UTC-8
        -420: "America/Denver",        # UTC-7
        -360: "America/Chicago",       # UTC-6
        -300: "America/New_York",      # UTC-5
        -240: "America/Halifax",       # UTC-4
        -180: "America/Sao_Paulo",     # UTC-3
        -120: "Atlantic/South_Georgia", # UTC-2
        -60: "Atlantic/Azores",        # UTC-1
        0: "Europe/London",           # UTC
        60: "Europe/Paris",           # UTC+1
        120: "Europe/Helsinki",       # UTC+2
        180: "Europe/Moscow",         # UTC+3
        240: "Asia/Dubai",            # UTC+4
        300: "Asia/Karachi",          # UTC+5
        330: "Asia/Kolkata",          # UTC+5:30
        345: "Asia/Kathmandu",        # UTC+5:45
        360: "Asia/Dhaka",            # UTC+6
        480: "Asia/Shanghai",         # UTC+8
        540: "Asia/Tokyo",            # UTC+9
        600: "Australia/Sydney",      # UTC+10
        720: "Pacific/Auckland"       # UTC+12
    }
    
    # 尝试查找精确匹配
    if offset_minutes in timezone_map:
        return timezone_map[offset_minutes]
    
    # 没有精确匹配，返回一个接近的时区
    closest_offset = min(timezone_map.keys(), key=lambda x: abs(x - offset_minutes))
    return timezone_map[closest_offset]

def is_captcha_page(html_content: str) -> bool:
    """
    检测页面是否包含验证码
    
    Args:
        html_content: HTML内容
        
    Returns:
        bool: 是否为验证码页面
    """
    # 常见验证码特征
    captcha_indicators = [
        'captcha', 'CAPTCHA', 
        'recaptcha', 'reCAPTCHA', 'g-recaptcha',
        'verification', 'verify', 'verification code',
        'security check', 'security verification',
        'robot', 'bot', 'human verification',
        'hcaptcha', 'h-captcha',
        'verify you are human', 'prove you are human',
        'I\'m not a robot', 'Are you human',
        'verification image', 'security image',
        'sliding validation', 'slide to verify',
        'validate', 'verification slider',
        '验证码', '安全验证', '人机验证', '滑动验证', '拖动滑块'
    ]
    
    # 检查HTML中是否包含验证码特征
    for indicator in captcha_indicators:
        if indicator in html_content:
            return True
    
    return False

def generate_random_delay() -> float:
    """
    生成随机延迟时间，模拟人类行为
    
    Returns:
        float: 随机延迟时间（秒）
    """
    # 基本延迟
    base_delay = random.uniform(0.5, 2.0)
    
    # 偶尔添加更长延迟
    if random.random() < 0.1:  # 10%概率
        base_delay += random.uniform(1.0, 3.0)
    
    return base_delay

def check_blocking_patterns(html_content: str, patterns: List[str] = None) -> Tuple[bool, str]:
    """
    检查HTML内容是否包含封锁模式
    
    Args:
        html_content (str): HTML内容
        patterns (List[str]): 自定义封锁模式，默认使用常见模式
        
    Returns:
        Tuple[bool, str]: (是否被封锁, 匹配的模式)
    """
    if not patterns:
        patterns = [
            r'robot', r'captcha', r'blocked', r'banned', r'security check',
            r'unusual activity', r'suspicious', r'too many requests',
            r'访问频率', r'访问过于频繁', r'频繁访问', r'请求太多',
            r'访问受限', r'拒绝访问', r'限制访问', r'验证码'
        ]
    
    html_lower = html_content.lower()
    for pattern in patterns:
        if re.search(pattern, html_lower, re.IGNORECASE):
            return True, pattern
    
    return False, None

def simulate_human_behavior(session, url, config=None):
    """
    模拟人类访问行为
    
    Args:
        session: 请求会话对象 
        url (str): 目标URL
        config (dict): 配置字典
        
    Returns:
        requests.Response: 响应对象
    """
    config = config or {}
    
    # 创建延迟管理器
    delay_mgr = DelayManager(strategy=config.get('delay_strategy', 'normal'))
    
    # 获取浏览器指纹
    fp_id = f"human_simulation_{int(time.time())}"
    fingerprint = get_browser_fingerprint(fp_id=fp_id)
    
    # 访问主页或前置页面
    if 'referer_url' in config:
        referer_url = config['referer_url']
        logger.info(f"访问引荐页面: {referer_url}")
        
        headers = fingerprint['headers'].copy()
        delay_mgr.delay()
        session.get(referer_url, headers=headers)
    
    # 随机停留
    wait_time = random.uniform(1, 3)
    logger.debug(f"页面停留时间: {wait_time:.1f}秒")
    time.sleep(wait_time)
    
    # 访问目标页面
    logger.info(f"访问目标页面: {url}")
    headers = fingerprint['headers'].copy()
    
    if 'referer_url' in config:
        headers['Referer'] = config['referer_url']
    
    delay_mgr.delay()
    response = session.get(url, headers=headers)
    
    # 如果页面有表单，可能需要模拟表单填写和提交
    if config.get('simulate_form', False) and '<form' in response.text:
        logger.info("检测到表单，模拟表单交互")
        # 解析表单，此处简化实现
        form_data = {}
        
        # 模拟填写表单的时间
        fill_time = random.uniform(3, 8)
        logger.debug(f"表单填写时间: {fill_time:.1f}秒")
        time.sleep(fill_time)
        
        # 提交表单
        delay_mgr.delay()
        post_url = config.get('form_url', url)
        response = session.post(post_url, data=form_data, headers=headers)
    
    return response

if __name__ == "__main__":
    # 测试代码
    print("生成随机用户代理...")
    ua_desktop = get_user_agent('desktop', 'chrome')
    ua_mobile = get_user_agent('mobile', 'safari')
    print(f"桌面Chrome UA: {ua_desktop}")
    print(f"移动Safari UA: {ua_mobile}")
    
    print("\n生成浏览器指纹...")
    fp = get_browser_fingerprint()
    print(f"指纹ID: {fp['fp_id']}")
    print(f"平台: {fp['platform']}")
    print(f"是否移动设备: {fp['is_mobile']}")
    
    print("\n获取Playwright选项...")
    pw_options = get_playwright_options(fp['fp_id'])
    print(f"视口尺寸: {pw_options['viewport']}")
    print(f"用户代理: {pw_options['user_agent']}")
    
    print("\n获取Selenium选项...")
    selenium_options = get_selenium_options(fp['fp_id'], 'chrome')
    print(f"参数数量: {len(selenium_options['arguments'])}")
    print(f"第一个参数: {selenium_options['arguments'][0]}") 