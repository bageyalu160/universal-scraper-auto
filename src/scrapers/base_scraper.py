#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬虫基类模块

提供通用爬虫功能的基类，包括配置加载、代理使用、反爬机制等功能。
所有具体爬虫实现应继承此基类。
"""

import os
import json
import time
import logging
import random
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# 导入工具类
from src.utils.proxy_pool import get_proxy, report_proxy_status
from src.utils.anti_detect import (
    get_user_agent, 
    get_browser_fingerprint, 
    solve_captcha,
    is_captcha_page
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/scraper.log')
    ]
)

class BaseScraper(ABC):
    """
    爬虫基类
    
    提供配置加载、代理使用、反爬策略、错误处理等通用功能
    """
    
    def __init__(self, site_id: str, config: Dict[str, Any] = None, output_dir: Optional[str] = None):
        """
        初始化爬虫基类
        
        Args:
            site_id: 站点ID
            config: 配置字典，为None则从默认路径加载
            output_dir: 输出目录
        """
        self.site_id = site_id
        self.config = config or self._load_config()
        self.output_dir = output_dir
        
        # 从配置中获取基本信息
        self.site_info = self.config.get('site', {}) or self.config.get('site_info', {})
        self.base_url = self.site_info.get('base_url', '')
        self.site_name = self.site_info.get('name', site_id)
        
        # 爬取设置
        self.scraping = self.config.get('scraping', {})
        
        # 错误处理配置
        self.error_handling = self.scraping.get('error_handling', {})
        self.max_retries = self.error_handling.get('max_retries', 3)
        self.retry_delay = self.error_handling.get('retry_delay', 5)
        
        # 代理设置
        self.proxy_config = self.scraping.get('proxy', {})
        self.use_proxy = self._get_env_bool('USE_PROXY', self.proxy_config.get('enable', False))
        self.rotate_proxy = self._get_env_bool('ROTATE_PROXY', self.proxy_config.get('rotate', False))
        self.rotate_interval = self.proxy_config.get('rotate_interval', 5)
        self.current_proxy = None
        self.request_count = 0
        
        # 反爬机制设置
        self.anti_detect_config = self.scraping.get('anti_detection', {})
        self.anti_detect_enabled = self._get_env_bool('ANTI_DETECT_ENABLED', True)
        
        # 浏览器指纹
        self.fp_config = self.anti_detect_config.get('browser_fingerprint', {})
        self.use_fingerprint = self._get_env_bool('BROWSER_FINGERPRINT', self.fp_config.get('enable', False))
        
        # 验证码处理
        self.captcha_config = self.anti_detect_config.get('captcha', {})
        self.solve_captchas = self._get_env_bool('SOLVE_CAPTCHAS', self.captcha_config.get('enable', False))
        
        # 行为模拟
        self.behavior_config = self.anti_detect_config.get('behavior', {})
        
        # 会话管理
        self.session = requests.Session()
        self.fingerprint_id = f"{site_id}_{random.randint(1000, 9999)}"
        
        # 输出设置
        self.output_config = self.config.get('output', {})
        self.output_filename = self.output_config.get('filename', f"{site_id}_data.json")
        
        # 初始化日志
        self.logger = logging.getLogger(f'scraper.{site_id}')
        self.logger.info(f"初始化 {self.site_name} 爬虫")
    
    def _get_env_bool(self, env_name: str, default: bool = False) -> bool:
        """从环境变量获取布尔值"""
        env_value = os.environ.get(env_name, str(default)).lower()
        return env_value in ['true', 'yes', 'y', '1', 'on']
    
    def _load_config(self) -> Dict[str, Any]:
        """
        从配置文件加载配置
        
        Returns:
            Dict: 配置字典
        """
        config_path = f"config/sites/{self.site_id}.yaml"
        
        if not os.path.exists(config_path):
            self.logger.error(f"配置文件不存在: {config_path}")
            return {}
        
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_output_path(self, filename: Optional[str] = None) -> str:
        """
        获取输出文件路径
        
        Args:
            filename: 可选的文件名，默认使用配置的文件名
            
        Returns:
            str: 输出文件路径
        """
        if not filename:
            filename = self.output_filename
        
        if self.output_dir:
            path = os.path.join(self.output_dir, filename)
        else:
            path = filename
            
        return path
    
    def _prepare_request(self, url: str, headers: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        准备请求参数，包括代理和浏览器指纹
        
        Args:
            url: 请求URL
            headers: 自定义请求头
            
        Returns:
            Dict: 请求参数字典
        """
        # 初始化请求参数
        request_args = {'timeout': 30}
        
        # 处理URL
        if not url.startswith(('http://', 'https://')):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        request_args['url'] = url
        
        # 添加浏览器指纹
        if self.anti_detect_enabled and self.use_fingerprint:
            fingerprint = get_browser_fingerprint(fp_id=self.fingerprint_id)
            fp_headers = fingerprint['headers']
            
            # 合并自定义头与指纹头
            if headers:
                fp_headers.update(headers)
                
            request_args['headers'] = fp_headers
        else:
            # 使用基本UA
            default_headers = {
                'User-Agent': get_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            if headers:
                default_headers.update(headers)
                
            request_args['headers'] = default_headers
        
        # 添加代理
        if self.use_proxy:
            # 检查是否需要轮换代理
            if self.rotate_proxy and self.request_count % self.rotate_interval == 0:
                self.current_proxy = get_proxy(rotate=True)
                self.logger.info(f"轮换代理: {self.current_proxy}")
            elif not self.current_proxy:
                self.current_proxy = get_proxy(rotate=False)
                self.logger.info(f"初始代理: {self.current_proxy}")
            
            if self.current_proxy:
                request_args['proxies'] = self.current_proxy
        
        # 增加请求计数
        self.request_count += 1
        
        # 添加其他参数
        for key, value in kwargs.items():
            request_args[key] = value
            
        return request_args
    
    def _handle_request_error(self, url: str, exception: Exception, attempt: int) -> None:
        """
        处理请求错误
        
        Args:
            url: 请求URL
            exception: 异常对象
            attempt: 当前尝试次数
        """
        self.logger.error(f"请求 {url} 失败 (尝试 {attempt}/{self.max_retries}): {str(exception)}")
        
        # 如果使用了代理，报告代理失败
        if self.use_proxy and self.current_proxy:
            report_proxy_status(self.current_proxy, success=False)
            
            # 如果不是最后一次尝试，获取新代理
            if attempt < self.max_retries:
                self.current_proxy = get_proxy(rotate=True)
                self.logger.info(f"更换代理: {self.current_proxy}")
    
    def _handle_captcha(self, response: requests.Response) -> Tuple[bool, Optional[Dict]]:
        """
        检测并处理验证码
        
        Args:
            response: 响应对象
            
        Returns:
            Tuple[bool, Optional[Dict]]: (是否包含验证码, 验证码解决结果)
        """
        if not self.solve_captchas:
            return False, None
            
        # 检查页面是否包含验证码
        if is_captcha_page(response.text):
            self.logger.warning(f"检测到验证码页面: {response.url}")
            
            # 设置验证码处理目录
            captcha_dir = Path("temp/captchas")
            captcha_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成验证码文件名
            captcha_file = captcha_dir / f"captcha_{int(time.time())}.png"
            
            # 提取验证码图片URL
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            captcha_img = soup.select_one('img[id*=captcha], img[class*=captcha], img[src*=captcha]')
            
            if captcha_img and captcha_img.get('src'):
                # 下载验证码图片
                captcha_url = captcha_img['src']
                if not captcha_url.startswith(('http://', 'https://')):
                    captcha_url = f"{self.base_url.rstrip('/')}/{captcha_url.lstrip('/')}"
                
                # 禁用代理下载验证码，以避免IP不一致
                img_response = requests.get(captcha_url, headers=response.request.headers)
                
                if img_response.status_code == 200:
                    with open(captcha_file, 'wb') as f:
                        f.write(img_response.content)
                    
                    # 解决验证码
                    provider = self.captcha_config.get('default_provider', '2captcha')
                    captcha_text = solve_captcha(str(captcha_file), provider=provider)
                    
                    if captcha_text:
                        self.logger.info(f"验证码解决成功: {captcha_text}")
                        # 提取表单数据
                        form_data = {}
                        forms = soup.select('form')
                        if forms:
                            for form in forms:
                                inputs = form.select('input')
                                for inp in inputs:
                                    name = inp.get('name')
                                    value = inp.get('value', '')
                                    if name:
                                        form_data[name] = value
                                
                                # 添加验证码字段
                                captcha_field = None
                                for field in ['captcha', 'validateCode', 'verification', 'code']:
                                    if field in form_data or any(field in k.lower() for k in form_data.keys()):
                                        captcha_field = next((k for k in form_data.keys() if field in k.lower()), field)
                                        break
                                
                                if captcha_field:
                                    form_data[captcha_field] = captcha_text
                                    return True, {
                                        'captcha_text': captcha_text,
                                        'form_data': form_data,
                                        'form_action': form.get('action', response.url)
                                    }
            
            self.logger.error("验证码处理失败")
            
        return False, None
    
    def _simulate_human_behavior(self) -> None:
        """
        模拟人类行为，添加随机延迟
        """
        if not self.anti_detect_enabled:
            return
            
        # 读取配置的随机延迟范围
        random_delays = self.behavior_config.get('random_delays', {})
        if random_delays.get('enable', False):
            min_delay = random_delays.get('min_seconds', 1.0)
            max_delay = random_delays.get('max_seconds', 5.0)
            
            # 添加随机延迟
            delay = random.uniform(min_delay, max_delay)
            self.logger.debug(f"添加随机延迟: {delay:.2f} 秒")
            time.sleep(delay)
    
    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        发送GET请求，包含重试、代理、反爬机制
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Optional[requests.Response]: 响应对象或None
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                # 模拟人类行为
                self._simulate_human_behavior()
                
                # 准备请求参数
                request_args = self._prepare_request(url, **kwargs)
                
                # 发送请求
                response = self.session.get(**request_args)
                
                # 检查是否成功
                if response.status_code == 200:
                    # 检查是否为验证码页面
                    has_captcha, captcha_result = self._handle_captcha(response)
                    
                    if has_captcha and captcha_result:
                        # 处理验证码
                        form_data = captcha_result.get('form_data', {})
                        form_action = captcha_result.get('form_action', response.url)
                        
                        # 提交验证码
                        self.logger.info(f"提交验证码: {captcha_result['captcha_text']}")
                        response = self.session.post(
                            form_action,
                            data=form_data,
                            headers=request_args.get('headers'),
                            proxies=request_args.get('proxies'),
                            timeout=request_args.get('timeout')
                        )
                    
                    # 如果使用了代理，报告成功
                    if self.use_proxy and self.current_proxy:
                        report_proxy_status(self.current_proxy, success=True)
                    
                    return response
                else:
                    self.logger.warning(f"请求 {url} 返回状态码 {response.status_code}")
                    
                    # 检查是否为重试状态码
                    retry_codes = self.error_handling.get('retry_codes', [429, 500, 502, 503, 504])
                    if response.status_code not in retry_codes or attempt == self.max_retries:
                        return response
                    
                    # 如果使用了代理，报告失败
                    if self.use_proxy and self.current_proxy:
                        report_proxy_status(self.current_proxy, success=False)
                    
                    # 获取新代理
                    if self.use_proxy:
                        self.current_proxy = get_proxy(rotate=True)
                        self.logger.info(f"更换代理: {self.current_proxy}")
            except Exception as e:
                self._handle_request_error(url, e, attempt)
                
                # 最后一次尝试失败
                if attempt == self.max_retries:
                    return None
            
            # 添加重试延迟
            if attempt < self.max_retries:
                retry_delay = self.retry_delay * (2 ** (attempt - 1))  # 指数退避
                self.logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
        
        return None
    
    def post(self, url: str, data=None, json=None, **kwargs) -> Optional[requests.Response]:
        """
        发送POST请求，包含重试、代理、反爬机制
        
        Args:
            url: 请求URL
            data: 表单数据
            json: JSON数据
            **kwargs: 其他请求参数
            
        Returns:
            Optional[requests.Response]: 响应对象或None
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                # 模拟人类行为
                self._simulate_human_behavior()
                
                # 准备请求参数
                request_args = self._prepare_request(url, **kwargs)
                
                # 添加数据
                if data is not None:
                    request_args['data'] = data
                if json is not None:
                    request_args['json'] = json
                
                # 发送请求
                response = self.session.post(**request_args)
                
                # 检查是否成功
                if response.status_code == 200:
                    # 如果使用了代理，报告成功
                    if self.use_proxy and self.current_proxy:
                        report_proxy_status(self.current_proxy, success=True)
                    
                    return response
                else:
                    self.logger.warning(f"POST请求 {url} 返回状态码 {response.status_code}")
                    
                    # 检查是否为重试状态码
                    retry_codes = self.error_handling.get('retry_codes', [429, 500, 502, 503, 504])
                    if response.status_code not in retry_codes or attempt == self.max_retries:
                        return response
                    
                    # 如果使用了代理，报告失败
                    if self.use_proxy and self.current_proxy:
                        report_proxy_status(self.current_proxy, success=False)
                    
                    # 获取新代理
                    if self.use_proxy:
                        self.current_proxy = get_proxy(rotate=True)
                        self.logger.info(f"更换代理: {self.current_proxy}")
            except Exception as e:
                self._handle_request_error(url, e, attempt)
                
                # 最后一次尝试失败
                if attempt == self.max_retries:
                    return None
            
            # 添加重试延迟
            if attempt < self.max_retries:
                retry_delay = self.retry_delay * (2 ** (attempt - 1))
                self.logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
        
        return None
    
    def save_data(self, data: Union[List, Dict], filename: Optional[str] = None) -> str:
        """
        保存数据到文件
        
        Args:
            data: 要保存的数据
            filename: 可选的文件名，默认使用配置的文件名
            
        Returns:
            str: 保存的文件路径
        """
        output_path = self._get_output_path(filename)
        
        # 创建输出目录
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # 添加时间戳
        if isinstance(data, list) and self.output_config.get('add_timestamp', False):
            timestamp_field = self.output_config.get('timestamp_field', 'crawled_at')
            timestamp_format = self.output_config.get('timestamp_format', '%Y-%m-%d %H:%M:%S')
            
            timestamp = time.strftime(timestamp_format)
            for item in data:
                if isinstance(item, dict):
                    item[timestamp_field] = timestamp
        
        # 保存数据
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"数据已保存到 {output_path}")
        return output_path
    
    @abstractmethod
    def scrape(self) -> Dict[str, Any]:
        """
        爬取数据的抽象方法，子类必须实现
        
        Returns:
            Dict: 包含状态和统计信息的字典
        """
        pass 