#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬虫模块单元测试
"""

import os
import sys
import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 创建测试数据目录
TEST_DATA_DIR = Path(__file__).parent.parent / 'data'
TEST_DATA_DIR.mkdir(exist_ok=True)

# 模拟 scraper.py 中的函数
def test_run_scraper():
    """测试爬虫运行函数"""
    
    # 模拟配置
    config = {
        'site': {
            'name': '测试站点',
            'base_url': 'https://example.com'
        },
        'scraping': {
            'engine': 'custom',
            'custom_module': 'test_module',
            'custom_function': 'test_function'
        }
    }
    
    # 模拟导入模块和函数
    with patch('importlib.import_module') as mock_import:
        # 设置模拟函数返回值
        mock_module = MagicMock()
        mock_function = MagicMock(return_value={'status': 'success', 'count': 10})
        mock_module.test_function = mock_function
        mock_import.return_value = mock_module
        
        # 导入实际的 run_scraper 函数
        # 注意：这里假设 scripts 目录下有 scraper.py 文件
        try:
            from scripts.scraper import run_scraper
            
            # 测试运行爬虫
            output_dir = str(TEST_DATA_DIR)
            result = run_scraper('test_site', config, output_dir)
            
            # 验证结果
            assert result['status'] == 'success'
            assert result['count'] == 10
            
            # 验证模拟函数被调用
            mock_import.assert_called_once_with('test_module')
            mock_function.assert_called_once()
        except ImportError:
            # 如果无法导入，则跳过测试
            pytest.skip("无法导入 scripts.scraper 模块")

# 测试 HTTP 请求功能
def test_http_request():
    """测试 HTTP 请求功能"""
    
    # 模拟 requests.get 响应
    with patch('requests.get') as mock_get:
        # 设置模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>测试页面</h1></body></html>'
        mock_get.return_value = mock_response
        
        # 执行请求
        import requests
        response = requests.get('https://example.com')
        
        # 验证响应
        assert response.status_code == 200
        assert '测试页面' in response.text
        
        # 验证模拟函数被调用
        mock_get.assert_called_once_with('https://example.com')

# 测试数据解析功能
def test_data_parsing():
    """测试数据解析功能"""
    
    # 测试 HTML 解析
    from bs4 import BeautifulSoup
    
    html = '<html><body><div class="item"><h2>标题1</h2><p>内容1</p></div><div class="item"><h2>标题2</h2><p>内容2</p></div></body></html>'
    soup = BeautifulSoup(html, 'html.parser')
    
    # 查找元素
    items = soup.find_all('div', class_='item')
    
    # 验证解析结果
    assert len(items) == 2
    assert items[0].h2.text == '标题1'
    assert items[1].p.text == '内容2'
