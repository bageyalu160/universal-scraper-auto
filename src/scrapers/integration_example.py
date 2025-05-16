#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
集成示例：展示如何在爬虫中集成代理池和反爬机制

本示例演示了如何创建一个集成了代理池和反爬机制的爬虫类，
包括浏览器指纹伪装、IP代理轮换、验证码处理和错误重试机制。
"""

import os
import json
import time
import logging
import random
import requests
from typing import Dict, Any, Optional, Tuple, List, Union
from pathlib import Path

# 导入自定义工具包
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

logger = logging.getLogger('IntegratedScraper')


class IntegratedScraper:
    """
    集成爬虫类：结合代理池和反爬机制的网页爬虫
    
    该类提供了一个完整的爬虫框架，包含以下功能：
    - 自动轮换IP代理
    - 浏览器指纹伪装
    - 验证码检测和解决
    - 请求失败重试
    - 详细的日志记录
    """
    
    def __init__(self, site_name: str):
        """
        初始化爬虫实例
        
        Args:
            site_name (str): 站点名称，用于加载对应的配置文件
        """
        self.site_name = site_name
        self.config = self._load_config()
        
        # 从配置中获取基本信息
        self.base_url = self.config['site_info']['base_url']
        self.max_retries = self.config['scraping'].get('max_retries', 3)
        self.retry_delay = self.config['scraping'].get('retry_delay', 2)
        
        # 代理设置
        self.use_proxy = self.config['scraping'].get('use_proxy', False)
        self.rotate_proxy = self.config['scraping'].get('rotate_proxy', False)
        self.current_proxy = None
        
        # 反爬设置
        self.anti_settings = self.config['scraping'].get('anti_detection', {})
        self.use_fingerprint = self.anti_settings.get('browser_fingerprint', False)
        self.solve_captchas = self.anti_settings.get('captcha_solver', False)
        
        # 指纹ID，用于保持同一会话使用相同指纹
        self.fingerprint_id = f"{site_name}_{random.randint(1000, 9999)}"
        
        # 会话保持
        self.session = requests.Session()
        
        logger.info(f"初始化 {site_name} 爬虫实例完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载站点配置文件
        
        Returns:
            Dict[str, Any]: 站点配置字典
        """
        # 确定配置文件路径
        config_path = Path(f"config/sites/{self.site_name}.yaml")
        
        # 如果YAML文件不存在，尝试JSON文件
        if not config_path.exists():
            config_path = Path(f"config/sites/{self.site_name}.json")
        
        if not config_path.exists():
            raise FileNotFoundError(f"找不到站点 {self.site_name} 的配置文件")
        
        # 根据文件类型加载配置
        if str(config_path).endswith('.yaml') or str(config_path).endswith('.yml'):
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def _prepare_request_args(self, url: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """
        准备请求参数，包括代理和浏览器指纹
        
        Args:
            url (str): 请求URL
            headers (Optional[Dict]): 自定义请求头
            
        Returns:
            Dict[str, Any]: 请求参数字典
        """
        # 初始化请求参数
        request_args = {'timeout': 30}
        
        # 处理URL，支持相对和绝对URL
        if not url.startswith(('http://', 'https://')):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        request_args['url'] = url
        
        # 添加浏览器指纹
        if self.use_fingerprint:
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
            self.current_proxy = get_proxy(rotate=self.rotate_proxy)
            request_args['proxies'] = self.current_proxy
            logger.info(f"使用代理: {self.current_proxy}")
        
        return request_args
    
    def _handle_captcha(self, response: requests.Response) -> Optional[Dict[str, Any]]:
        """
        检测和处理验证码
        
        Args:
            response (requests.Response): 请求响应对象
            
        Returns:
            Optional[Dict[str, Any]]: 验证码处理结果，如果非验证码页面则返回None
        """
        if not self.solve_captchas:
            return None
        
        # 检测是否是验证码页面
        if is_captcha_page(response.text):
            logger.warning("检测到验证码页面")
            
            # 保存验证码图片
            captcha_dir = Path("temp/captchas")
            captcha_dir.mkdir(parents=True, exist_ok=True)
            
            captcha_file = captcha_dir / f"captcha_{int(time.time())}.png"
            
            # 从响应中提取验证码图片URL
            # 注意：此处提取方法需要根据目标网站实际情况调整
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            captcha_img = soup.select_one('img[id*="captcha"], img[class*="captcha"], img[src*="captcha"]')
            
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
                    provider = self.anti_settings.get('captcha', {}).get('default_provider', 'local')
                    captcha_text = solve_captcha(str(captcha_file), provider=provider)
                    
                    if captcha_text:
                        logger.info(f"验证码解决成功: {captcha_text}")
                        return {
                            'captcha_text': captcha_text,
                            'captcha_file': str(captcha_file),
                            'form_data': self._extract_form_data(response.text, captcha_text)
                        }
            
            logger.error("验证码处理失败")
        
        return None
    
    def _extract_form_data(self, html_content: str, captcha_text: str) -> Dict[str, str]:
        """
        从验证码页面提取表单数据
        
        Args:
            html_content (str): 网页内容
            captcha_text (str): 解析出的验证码文本
            
        Returns:
            Dict[str, str]: 包含验证码的表单数据
        """
        # 使用BeautifulSoup提取表单数据
        # 注意：此处提取方法需要根据目标网站实际情况调整
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        form = soup.find('form')
        form_data = {}
        
        if form:
            # 提取所有隐藏字段
            for input_field in form.find_all('input'):
                if 'name' in input_field.attrs:
                    field_name = input_field['name']
                    field_value = input_field.get('value', '')
                    
                    # 跳过提交按钮
                    if input_field.get('type') in ['submit', 'button']:
                        continue
                    
                    # 如果是验证码字段，使用解析出的验证码
                    if 'captcha' in field_name.lower():
                        form_data[field_name] = captcha_text
                    else:
                        form_data[field_name] = field_value
        
        return form_data
    
    def get(self, url: str, headers: Optional[Dict] = None, params: Optional[Dict] = None, 
            allow_redirects: bool = True) -> Tuple[Optional[requests.Response], bool]:
        """
        执行GET请求，包含重试和代理切换逻辑
        
        Args:
            url (str): 请求URL
            headers (Optional[Dict]): 自定义请求头
            params (Optional[Dict]): URL参数
            allow_redirects (bool): 是否允许重定向
            
        Returns:
            Tuple[Optional[requests.Response], bool]: (响应对象, 是否成功)
        """
        for attempt in range(1, self.max_retries + 1):
            # 准备请求参数
            request_args = self._prepare_request_args(url, headers)
            
            if params:
                request_args['params'] = params
            
            request_args['allow_redirects'] = allow_redirects
            
            try:
                logger.info(f"GET请求 {url} (尝试 {attempt}/{self.max_retries})")
                response = self.session.get(**request_args)
                
                # 检查响应状态
                if response.status_code >= 200 and response.status_code < 300:
                    # 检查是否是验证码页面
                    captcha_result = self._handle_captcha(response)
                    
                    if captcha_result:
                        # 如果是验证码页面，提交验证码
                        form_url = response.url
                        form_data = captcha_result['form_data']
                        
                        logger.info(f"提交验证码到 {form_url}")
                        
                        # 提交验证码表单
                        post_response = self.session.post(
                            form_url,
                            data=form_data,
                            headers=request_args['headers'],
                            proxies=request_args.get('proxies'),
                            allow_redirects=allow_redirects
                        )
                        
                        if post_response.status_code >= 200 and post_response.status_code < 300:
                            # 报告代理成功
                            if self.use_proxy:
                                report_proxy_status(self.current_proxy, success=True)
                            return post_response, True
                    else:
                        # 非验证码页面，直接返回成功
                        if self.use_proxy:
                            report_proxy_status(self.current_proxy, success=True)
                        return response, True
                
                # 可能的IP被封或其他错误
                elif response.status_code in [403, 429, 503]:
                    logger.warning(f"请求被拒绝，状态码: {response.status_code}")
                    
                    # 报告代理失败并切换代理
                    if self.use_proxy:
                        report_proxy_status(self.current_proxy, success=False)
                        self.rotate_proxy = True  # 强制轮换下一个代理
                else:
                    logger.error(f"请求失败，状态码: {response.status_code}")
            
            except (requests.RequestException, IOError) as e:
                logger.error(f"请求异常: {str(e)}")
                
                # 报告代理失败
                if self.use_proxy:
                    report_proxy_status(self.current_proxy, success=False)
                    self.rotate_proxy = True  # 强制轮换下一个代理
            
            # 重试前等待
            if attempt < self.max_retries:
                sleep_time = self.retry_delay * attempt
                logger.info(f"等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
        
        logger.error(f"所有重试失败，无法获取 {url}")
        return None, False
    
    def post(self, url: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None,
             headers: Optional[Dict] = None, allow_redirects: bool = True) -> Tuple[Optional[requests.Response], bool]:
        """
        执行POST请求，包含重试和代理切换逻辑
        
        Args:
            url (str): 请求URL
            data (Optional[Dict]): 表单数据
            json_data (Optional[Dict]): JSON数据
            headers (Optional[Dict]): 自定义请求头
            allow_redirects (bool): 是否允许重定向
            
        Returns:
            Tuple[Optional[requests.Response], bool]: (响应对象, 是否成功)
        """
        for attempt in range(1, self.max_retries + 1):
            # 准备请求参数
            request_args = self._prepare_request_args(url, headers)
            
            if data:
                request_args['data'] = data
            
            if json_data:
                request_args['json'] = json_data
                
                # 如果是JSON请求，确保头信息正确
                if 'headers' in request_args:
                    request_args['headers']['Content-Type'] = 'application/json'
            
            request_args['allow_redirects'] = allow_redirects
            
            try:
                logger.info(f"POST请求 {url} (尝试 {attempt}/{self.max_retries})")
                response = self.session.post(**request_args)
                
                # 检查响应状态
                if response.status_code >= 200 and response.status_code < 300:
                    # 检查是否是验证码页面
                    captcha_result = self._handle_captcha(response)
                    
                    if captcha_result:
                        # 如果是验证码页面，提交验证码
                        form_url = response.url
                        form_data = captcha_result['form_data']
                        
                        # 合并原始表单数据
                        if data:
                            form_data.update(data)
                        
                        logger.info(f"提交验证码到 {form_url}")
                        
                        # 提交验证码表单
                        post_response = self.session.post(
                            form_url,
                            data=form_data,
                            headers=request_args['headers'],
                            proxies=request_args.get('proxies'),
                            allow_redirects=allow_redirects
                        )
                        
                        if post_response.status_code >= 200 and post_response.status_code < 300:
                            # 报告代理成功
                            if self.use_proxy:
                                report_proxy_status(self.current_proxy, success=True)
                            return post_response, True
                    else:
                        # 非验证码页面，直接返回成功
                        if self.use_proxy:
                            report_proxy_status(self.current_proxy, success=True)
                        return response, True
                
                # 可能的IP被封或其他错误
                elif response.status_code in [403, 429, 503]:
                    logger.warning(f"请求被拒绝，状态码: {response.status_code}")
                    
                    # 报告代理失败并切换代理
                    if self.use_proxy:
                        report_proxy_status(self.current_proxy, success=False)
                        self.rotate_proxy = True  # 强制轮换下一个代理
                else:
                    logger.error(f"请求失败，状态码: {response.status_code}")
            
            except (requests.RequestException, IOError) as e:
                logger.error(f"请求异常: {str(e)}")
                
                # 报告代理失败
                if self.use_proxy:
                    report_proxy_status(self.current_proxy, success=False)
                    self.rotate_proxy = True  # 强制轮换下一个代理
            
            # 重试前等待
            if attempt < self.max_retries:
                sleep_time = self.retry_delay * attempt
                logger.info(f"等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
        
        logger.error(f"所有重试失败，无法提交到 {url}")
        return None, False
    
    def scrape(self, targets: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        执行爬取任务
        
        Args:
            targets (Optional[List[Dict[str, Any]]]): 爬取目标列表，如果不提供则使用配置中的targets
            
        Returns:
            Dict[str, Any]: 爬取结果
        """
        results = {
            'success': 0,
            'failed': 0,
            'data': [],
            'errors': []
        }
        
        # 如果没有提供targets，使用配置中的targets
        if not targets:
            targets = self.config['scraping'].get('targets', [])
        
        # 如果仍然没有targets，记录错误并返回
        if not targets:
            logger.error("未找到爬取目标配置")
            results['errors'].append("未找到爬取目标配置")
            return results
        
        # 处理每个目标
        for target in targets:
            target_url = target.get('url')
            method = target.get('method', 'GET').upper()
            
            if not target_url:
                logger.error("目标URL未定义，跳过")
                results['failed'] += 1
                results['errors'].append("目标URL未定义")
                continue
            
            logger.info(f"开始爬取 {method} {target_url}")
            
            try:
                response = None
                success = False
                
                # 根据请求方法执行请求
                if method == 'GET':
                    params = target.get('params')
                    response, success = self.get(target_url, params=params)
                elif method == 'POST':
                    data = target.get('data')
                    json_data = target.get('json')
                    response, success = self.post(target_url, data=data, json_data=json_data)
                else:
                    logger.error(f"不支持的请求方法: {method}")
                    results['failed'] += 1
                    results['errors'].append(f"不支持的请求方法: {method}")
                    continue
                
                # 处理响应
                if success and response:
                    # 解析结果
                    parsed_data = self._parse_response(response, target)
                    
                    if parsed_data:
                        logger.info(f"成功爬取 {target_url}")
                        results['success'] += 1
                        results['data'].append(parsed_data)
                    else:
                        logger.warning(f"响应解析失败: {target_url}")
                        results['failed'] += 1
                        results['errors'].append(f"响应解析失败: {target_url}")
                else:
                    logger.error(f"爬取失败: {target_url}")
                    results['failed'] += 1
                    results['errors'].append(f"爬取失败: {target_url}")
            
            except Exception as e:
                logger.exception(f"爬取过程中发生异常: {str(e)}")
                results['failed'] += 1
                results['errors'].append(f"爬取异常 {target_url}: {str(e)}")
        
        logger.info(f"爬取任务完成: 成功 {results['success']}, 失败 {results['failed']}")
        return results
    
    def _parse_response(self, response: requests.Response, target: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析响应数据
        
        Args:
            response (requests.Response): 响应对象
            target (Dict[str, Any]): 目标配置
            
        Returns:
            Optional[Dict[str, Any]]: 解析结果
        """
        try:
            # 获取选择器类型
            selector_type = self.config['parsing'].get('selector_type', 'css')
            
            # 获取字段选择器
            field_selectors = self.config['parsing'].get('field_selectors', {})
            
            # 如果目标定义了特定的选择器，则使用目标的选择器
            target_selectors = target.get('field_selectors')
            if target_selectors:
                field_selectors = target_selectors
            
            # 初始化结果
            parsed_data = {
                'url': response.url,
                'timestamp': int(time.time())
            }
            
            # 使用BeautifulSoup解析HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 对每个字段应用选择器提取数据
            for field_name, selector in field_selectors.items():
                # 根据选择器类型选择方法
                if selector_type.lower() == 'css':
                    elements = soup.select(selector)
                elif selector_type.lower() == 'xpath':
                    # 对于XPath，需要额外的库
                    from lxml import etree
                    html = etree.HTML(response.text)
                    elements = html.xpath(selector)
                else:
                    logger.error(f"不支持的选择器类型: {selector_type}")
                    continue
                
                # 提取文本或值
                if elements:
                    if isinstance(elements, list) and len(elements) > 1:
                        # 多个元素，保存为列表
                        values = []
                        for el in elements:
                            if hasattr(el, 'get_text'):
                                values.append(el.get_text(strip=True))
                            elif hasattr(el, 'text'):
                                values.append(el.text.strip())
                            else:
                                values.append(str(el))
                        parsed_data[field_name] = values
                    else:
                        # 单个元素
                        el = elements[0] if isinstance(elements, list) else elements
                        if hasattr(el, 'get_text'):
                            parsed_data[field_name] = el.get_text(strip=True)
                        elif hasattr(el, 'text'):
                            parsed_data[field_name] = el.text.strip()
                        else:
                            parsed_data[field_name] = str(el)
                else:
                    # 未找到元素
                    parsed_data[field_name] = None
            
            return parsed_data
            
        except Exception as e:
            logger.exception(f"解析响应时发生异常: {str(e)}")
            return None
    
    def close(self):
        """关闭会话和资源"""
        if self.session:
            self.session.close()
        logger.info(f"爬虫会话已关闭")


def main():
    """主函数：演示如何使用集成爬虫"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='集成爬虫示例')
    parser.add_argument('--site', type=str, required=True, help='站点名称')
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path("data/daily")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 初始化并运行爬虫
        scraper = IntegratedScraper(args.site)
        result = scraper.scrape()
        
        # 保存结果
        if result['data']:
            # 获取输出格式
            output_format = scraper.config['output'].get('format', 'json').lower()
            filename = scraper.config['output'].get('filename', f"{args.site}_data.json")
            
            output_path = output_dir / filename
            
            # 根据格式保存数据
            if output_format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result['data'], f, ensure_ascii=False, indent=2)
            elif output_format == 'csv':
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    if result['data']:
                        # 使用第一条数据的keys作为表头
                        fieldnames = result['data'][0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(result['data'])
            elif output_format == 'tsv':
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    if result['data']:
                        fieldnames = result['data'][0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
                        writer.writeheader()
                        writer.writerows(result['data'])
            
            logger.info(f"结果已保存到 {output_path}")
            
            # 打印摘要
            print(f"爬取完成 - 成功: {result['success']}, 失败: {result['failed']}")
            print(f"数据已保存到 {output_path}")
        else:
            logger.warning("未收集到数据")
            print("爬取完成但未收集到数据")
        
        # 确保资源被释放
        scraper.close()
        
    except Exception as e:
        logger.exception(f"运行爬虫时发生异常: {str(e)}")
        print(f"错误: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())