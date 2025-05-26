#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pytest
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 测试数据目录
TEST_DATA_DIR = Path(__file__).parent / 'data'

@pytest.fixture
def test_data_dir():
    """返回测试数据目录"""
    return TEST_DATA_DIR

@pytest.fixture
def sample_config():
    """返回示例配置数据"""
    return {
        'site': {
            'name': '测试站点',
            'description': '测试站点描述',
            'base_url': 'https://example.com',
            'output_filename': 'test_data.json',
            'encoding': 'utf-8'
        },
        'scraping': {
            'engine': 'custom',
            'custom_module': 'src.scrapers.test_scraper',
            'custom_function': 'scrape_test'
        },
        'network': {
            'retry': {
                'max_retries': 3,
                'backoff_factor': 0.5,
                'status_forcelist': [408, 429, 500, 502, 503, 504]
            },
            'timeout': 30,
            'delay': {
                'page_delay': {
                    'min': 1,
                    'max': 2
                }
            },
            'user_agents': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]
        }
    }
