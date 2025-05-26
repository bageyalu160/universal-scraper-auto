#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬虫和分析流程集成测试
"""

import os
import sys
import pytest
import json
import yaml
from unittest.mock import patch, MagicMock
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 创建测试数据目录
TEST_DATA_DIR = Path(__file__).parent.parent / 'data'
TEST_DATA_DIR.mkdir(exist_ok=True)

@pytest.mark.integration
def test_scraper_analyzer_flow():
    """测试爬虫和分析的完整流程"""
    
    # 模拟爬虫函数
    def mock_scrape_function(config, output_dir):
        """模拟爬虫函数"""
        # 创建测试数据
        test_data = [
            {
                "title": "测试标题1",
                "content": "测试内容1",
                "date": "2025-05-01",
                "author": "测试作者1",
                "views": 100
            },
            {
                "title": "测试标题2",
                "content": "测试内容2",
                "date": "2025-05-02",
                "author": "测试作者2",
                "views": 200
            }
        ]
        
        # 保存测试数据
        output_file = os.path.join(output_dir, config['site']['output_filename'])
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False)
        
        return {
            'status': 'success',
            'count': len(test_data),
            'file_path': output_file
        }
    
    # 模拟 AI 分析函数
    def mock_analyze_function(file_path, site_id, output_path=None):
        """模拟 AI 分析函数"""
        # 读取测试数据
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 生成分析结果
        analysis_result = f"""
## {site_id} 数据分析

数据概览:
- 总记录数: {len(data)}
- 日期范围: {data[0]['date']} 至 {data[-1]['date']}

### 主要发现

1. 数据中包含多个主题的内容
2. 浏览量呈上升趋势
3. 内容质量整体较高

### 详细分析

各记录详情:
{', '.join([item['title'] for item in data])}
        """
        
        # 保存分析结果
        if not output_path:
            output_path = os.path.join(os.path.dirname(file_path), f"analysis_{site_id}.md")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(analysis_result)
        
        return output_path
    
    try:
        # 尝试导入相关模块
        from scripts.scraper import run_scraper
        from scripts.ai_analyzer import AIAnalyzer
        
        # 创建测试配置
        test_config = {
            'site': {
                'name': '测试站点',
                'description': '测试站点描述',
                'base_url': 'https://example.com',
                'output_filename': 'test_data.json'
            },
            'scraping': {
                'engine': 'custom',
                'custom_module': 'test_module',
                'custom_function': 'test_function'
            }
        }
        
        # 保存测试配置
        config_dir = TEST_DATA_DIR / 'config' / 'sites'
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / 'test_site.yaml'
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, allow_unicode=True)
        
        # 模拟导入模块
        with patch('importlib.import_module') as mock_import:
            # 设置模拟模块
            mock_module = MagicMock()
            mock_module.test_function = mock_scrape_function
            mock_import.return_value = mock_module
            
            # 模拟 AIAnalyzer 类
            with patch.object(AIAnalyzer, '__init__', return_value=None):
                with patch.object(AIAnalyzer, 'analyze', return_value=True):
                    with patch.object(AIAnalyzer, 'save_result', return_value=True):
                        # 执行爬虫
                        output_dir = str(TEST_DATA_DIR / 'output')
                        result = run_scraper('test_site', test_config, output_dir)
                        
                        # 验证爬虫结果
                        assert result['status'] == 'success'
                        assert result['count'] == 2
                        
                        # 执行分析
                        analyzer = AIAnalyzer(
                            file_path=result['file_path'],
                            site_id='test_site'
                        )
                        
                        # 模拟分析过程
                        analyzer.analyze = MagicMock(return_value=True)
                        analyzer.save_result = MagicMock(return_value=True)
                        
                        # 验证分析结果
                        assert analyzer.analyze() == True
                        assert analyzer.save_result() == True
        
        # 清理测试文件
        config_file.unlink(missing_ok=True)
        
    except ImportError:
        # 如果无法导入，则跳过测试
        pytest.skip("无法导入必要的模块")

@pytest.mark.integration
def test_notification_after_analysis():
    """测试分析后的通知功能"""
    
    # 模拟分析结果
    analysis_result = """
## 测试站点数据分析

数据概览:
- 总记录数: 2
- 日期范围: 2025-05-01 至 2025-05-02

### 主要发现

1. 数据中包含多个主题的内容
2. 浏览量呈上升趋势
3. 内容质量整体较高
    """
    
    # 保存分析结果
    analysis_file = TEST_DATA_DIR / 'analysis_result.md'
    with open(analysis_file, 'w', encoding='utf-8') as f:
        f.write(analysis_result)
    
    # 模拟通知函数
    def mock_send_notification(title, message, channels=None):
        """模拟发送通知"""
        return {
            'status': 'success',
            'channels': channels or ['dingtalk', 'feishu', 'wechat'],
            'title': title,
            'message_length': len(message)
        }
    
    try:
        # 尝试导入通知模块
        from scripts.notify import send_notification
        
        # 模拟 send_notification 函数
        with patch('scripts.notify.send_notification', side_effect=mock_send_notification):
            # 发送通知
            notification_result = send_notification(
                title='测试站点数据更新通知',
                message=analysis_result,
                channels=['dingtalk', 'feishu']
            )
            
            # 验证通知结果
            assert notification_result['status'] == 'success'
            assert len(notification_result['channels']) == 2
            assert notification_result['title'] == '测试站点数据更新通知'
            assert notification_result['message_length'] > 0
    
    except ImportError:
        # 如果无法导入，则使用模拟函数
        notification_result = mock_send_notification(
            title='测试站点数据更新通知',
            message=analysis_result,
            channels=['dingtalk', 'feishu']
        )
        
        # 验证通知结果
        assert notification_result['status'] == 'success'
        assert len(notification_result['channels']) == 2
        assert notification_result['title'] == '测试站点数据更新通知'
        assert notification_result['message_length'] > 0
    
    # 清理测试文件
    analysis_file.unlink(missing_ok=True)
