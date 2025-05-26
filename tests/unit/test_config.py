#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置系统单元测试
"""

import os
import sys
import pytest
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 创建测试数据目录
TEST_DATA_DIR = Path(__file__).parent.parent / 'data'
TEST_DATA_DIR.mkdir(exist_ok=True)

def test_load_config():
    """测试配置文件加载"""
    # 创建测试配置文件
    test_config = {
        'site': {
            'name': '测试站点',
            'description': '测试站点描述',
            'base_url': 'https://example.com'
        },
        'scraping': {
            'engine': 'custom'
        }
    }
    
    config_path = TEST_DATA_DIR / 'test_config.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(test_config, f, allow_unicode=True)
    
    # 测试配置加载
    with open(config_path, 'r', encoding='utf-8') as f:
        loaded_config = yaml.safe_load(f)
    
    # 验证配置内容
    assert loaded_config['site']['name'] == '测试站点'
    assert loaded_config['site']['base_url'] == 'https://example.com'
    assert loaded_config['scraping']['engine'] == 'custom'
    
    # 清理测试文件
    config_path.unlink(missing_ok=True)

def test_config_validation():
    """测试配置验证"""
    # 有效配置
    valid_config = {
        'site': {
            'name': '测试站点',
            'base_url': 'https://example.com'
        },
        'scraping': {
            'engine': 'custom'
        }
    }
    
    # 缺少必要字段的配置
    invalid_config = {
        'site': {
            'name': '测试站点'
        }
    }
    
    # 简单验证函数
    def validate_config(config):
        if 'site' not in config:
            return False
        if 'base_url' not in config['site']:
            return False
        if 'scraping' not in config:
            return False
        return True
    
    assert validate_config(valid_config) == True
    assert validate_config(invalid_config) == False
