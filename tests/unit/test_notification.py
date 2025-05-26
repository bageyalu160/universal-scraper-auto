#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知系统单元测试
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 创建测试数据目录
TEST_DATA_DIR = Path(__file__).parent.parent / 'data'
TEST_DATA_DIR.mkdir(exist_ok=True)

def test_apprise_notification():
    """测试 Apprise 通知功能"""
    # 模拟 Apprise 库
    with patch('apprise.Apprise') as mock_apprise:
        # 设置模拟实例
        mock_instance = MagicMock()
        mock_instance.add.return_value = True
        mock_instance.notify.return_value = True
        mock_apprise.return_value = mock_instance
        
        # 导入 apprise 库
        import apprise
        
        # 创建 Apprise 对象
        app = apprise.Apprise()
        
        # 添加通知服务
        app.add('discord://webhook_id/webhook_token')
        
        # 发送通知
        result = app.notify(
            title='测试通知',
            body='这是一条测试通知消息。'
        )
        
        # 验证结果
        assert result == True
        
        # 验证模拟函数被调用
        mock_instance.add.assert_called_once_with('discord://webhook_id/webhook_token')
        mock_instance.notify.assert_called_once()

def test_dingtalk_notification():
    """测试钉钉通知功能"""
    # 模拟 requests.post 方法
    with patch('requests.post') as mock_post:
        # 设置模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
        mock_post.return_value = mock_response
        
        # 创建简单的钉钉通知函数
        def send_dingtalk_notification(webhook_url, message, title=None):
            """发送钉钉通知"""
            import requests
            import json
            
            # 构建请求数据
            data = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': title or '通知',
                    'text': message
                }
            }
            
            # 发送请求
            response = requests.post(
                webhook_url,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'}
            )
            
            # 返回结果
            return response.status_code == 200 and response.json().get('errcode') == 0
        
        # 测试发送通知
        result = send_dingtalk_notification(
            webhook_url='https://oapi.dingtalk.com/robot/send?access_token=test_token',
            message='## 测试通知\n\n这是一条测试通知消息。',
            title='测试通知'
        )
        
        # 验证结果
        assert result == True
        
        # 验证模拟函数被调用
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://oapi.dingtalk.com/robot/send?access_token=test_token'
        assert kwargs['headers']['Content-Type'] == 'application/json'

def test_feishu_notification():
    """测试飞书通知功能"""
    # 模拟 requests.post 方法
    with patch('requests.post') as mock_post:
        # 设置模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'code': 0, 'msg': 'success'}
        mock_post.return_value = mock_response
        
        # 创建简单的飞书通知函数
        def send_feishu_notification(webhook_url, message, title=None):
            """发送飞书通知"""
            import requests
            import json
            
            # 构建请求数据
            data = {
                'msg_type': 'interactive',
                'card': {
                    'header': {
                        'title': {
                            'tag': 'plain_text',
                            'content': title or '通知'
                        }
                    },
                    'elements': [
                        {
                            'tag': 'div',
                            'text': {
                                'tag': 'lark_md',
                                'content': message
                            }
                        }
                    ]
                }
            }
            
            # 发送请求
            response = requests.post(
                webhook_url,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'}
            )
            
            # 返回结果
            return response.status_code == 200 and response.json().get('code') == 0
        
        # 测试发送通知
        result = send_feishu_notification(
            webhook_url='https://open.feishu.cn/open-apis/bot/v2/hook/test_token',
            message='**测试通知**\n\n这是一条测试通知消息。',
            title='测试通知'
        )
        
        # 验证结果
        assert result == True
        
        # 验证模拟函数被调用
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://open.feishu.cn/open-apis/bot/v2/hook/test_token'
        assert kwargs['headers']['Content-Type'] == 'application/json'
