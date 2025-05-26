#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI 分析模块单元测试
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

def test_load_prompt():
    """测试提示词加载功能"""
    # 创建测试提示词文件
    prompt_dir = TEST_DATA_DIR / 'prompts'
    prompt_dir.mkdir(exist_ok=True)
    
    test_prompt = "这是一个测试提示词，用于分析{site_name}的数据。\n数据包含{record_count}条记录。"
    
    prompt_file = prompt_dir / 'test_prompt.txt'
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(test_prompt)
    
    # 测试提示词加载和格式化
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 格式化提示词
    formatted_prompt = prompt_template.format(
        site_name="测试站点",
        record_count=100
    )
    
    # 验证格式化结果
    assert "测试站点" in formatted_prompt
    assert "100条记录" in formatted_prompt
    
    # 清理测试文件
    prompt_file.unlink(missing_ok=True)

def test_analyze_with_gemini():
    """测试使用 Gemini 进行分析"""
    # 模拟 Gemini API
    with patch('google.generativeai.GenerativeModel') as mock_model:
        # 设置模拟响应
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "这是 Gemini 的分析结果。数据显示有明显的趋势变化。"
        mock_instance.generate_content.return_value = mock_response
        mock_model.return_value = mock_instance
        
        try:
            # 尝试导入 AIAnalyzer 类
            from scripts.ai_analyzer import AIAnalyzer
            
            # 创建测试数据文件
            test_data = [
                {"title": "测试标题1", "content": "测试内容1", "date": "2025-05-01"},
                {"title": "测试标题2", "content": "测试内容2", "date": "2025-05-02"}
            ]
            
            data_file = TEST_DATA_DIR / 'test_data.json'
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False)
            
            # 模拟 AIAnalyzer._load_settings 方法
            with patch.object(AIAnalyzer, '_load_settings', return_value={
                'analysis': {
                    'enabled': True,
                    'provider': 'gemini',
                    'api': {
                        'model': 'gemini-1.5-pro'
                    }
                }
            }):
                # 模拟 AIAnalyzer._setup_ai_provider 方法
                with patch.object(AIAnalyzer, '_setup_ai_provider'):
                    # 模拟 AIAnalyzer._load_prompt 方法
                    with patch.object(AIAnalyzer, '_load_prompt', return_value="测试提示词"):
                        # 创建 AIAnalyzer 实例
                        analyzer = AIAnalyzer(
                            file_path=str(data_file),
                            site_id='test_site'
                        )
                        
                        # 模拟 load_data 方法
                        analyzer.data = test_data
                        
                        # 测试 analyze_with_gemini 方法
                        result = analyzer.analyze_with_gemini("测试内容")
                        
                        # 验证结果
                        assert "Gemini 的分析结果" in result
                        
                        # 验证模拟函数被调用
                        mock_model.assert_called_once()
                        mock_instance.generate_content.assert_called_once()
            
            # 清理测试文件
            data_file.unlink(missing_ok=True)
            
        except ImportError:
            # 如果无法导入，则跳过测试
            pytest.skip("无法导入 scripts.ai_analyzer 模块")

def test_analyze_with_openai():
    """测试使用 OpenAI 进行分析"""
    # 模拟 OpenAI API
    with patch('openai.ChatCompletion.create') as mock_create:
        # 设置模拟响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "这是 OpenAI 的分析结果。数据表明存在季节性变化。"
        mock_create.return_value = mock_response
        
        try:
            # 尝试导入 AIAnalyzer 类
            from scripts.ai_analyzer import AIAnalyzer
            
            # 创建测试数据文件
            test_data = [
                {"title": "测试标题1", "content": "测试内容1", "date": "2025-05-01"},
                {"title": "测试标题2", "content": "测试内容2", "date": "2025-05-02"}
            ]
            
            data_file = TEST_DATA_DIR / 'test_data.json'
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False)
            
            # 模拟 AIAnalyzer._load_settings 方法
            with patch.object(AIAnalyzer, '_load_settings', return_value={
                'analysis': {
                    'enabled': True,
                    'provider': 'openai',
                    'api': {
                        'model': 'gpt-4'
                    }
                }
            }):
                # 模拟 AIAnalyzer._setup_ai_provider 方法
                with patch.object(AIAnalyzer, '_setup_ai_provider'):
                    # 模拟 AIAnalyzer._load_prompt 方法
                    with patch.object(AIAnalyzer, '_load_prompt', return_value="测试提示词"):
                        # 创建 AIAnalyzer 实例
                        analyzer = AIAnalyzer(
                            file_path=str(data_file),
                            site_id='test_site'
                        )
                        
                        # 模拟 load_data 方法
                        analyzer.data = test_data
                        analyzer.ai_provider = 'openai'
                        
                        # 测试 analyze_with_openai 方法
                        result = analyzer.analyze_with_openai("测试内容")
                        
                        # 验证结果
                        assert "OpenAI 的分析结果" in result
                        
                        # 验证模拟函数被调用
                        mock_create.assert_called_once()
            
            # 清理测试文件
            data_file.unlink(missing_ok=True)
            
        except ImportError:
            # 如果无法导入，则跳过测试
            pytest.skip("无法导入 scripts.ai_analyzer 模块")
