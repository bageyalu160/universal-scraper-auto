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
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
import hashlib

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