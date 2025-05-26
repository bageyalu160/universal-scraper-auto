#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知脚本 - 发送分析结果通知
支持多种通知渠道：使用Apprise库实现通用通知
"""

import os
import sys
import json
import yaml
import argparse
import logging
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

# 导入Apprise库
import apprise

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('notify')

class Notifier:
    """通知发送器类，使用Apprise支持多种通知渠道"""
    
    def __init__(self, file_path, site_id, settings_path=None):
        """
        初始化通知发送器
        
        Args:
            file_path (str): 分析结果文件路径
            site_id (str): 网站ID
            settings_path (str, optional): 设置文件路径
        """
        self.file_path = file_path
        self.site_id = site_id
        
        # 设置路径
        self.base_dir = Path(__file__).parent.parent
        self.settings_path = settings_path or self.base_dir / "config" / "settings.yaml"
        
        # 加载设置
        self.settings = self._load_settings()
        
        # 初始化Apprise对象
        self.apprise = apprise.Apprise()
        
        # 验证通知设置
        self._validate_notification_settings()
        
        # 加载分析结果
        self.result_data = None
        self.load_result()
    
    def _load_settings(self):
        """加载设置文件"""
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
            logger.info(f"成功加载设置文件: {self.settings_path}")
            return settings
        except Exception as e:
            logger.error(f"加载设置文件失败: {e}")
            raise
    
    def _get_webhook_url(self, settings_dict):
        """
        从设置字典中获取webhook_url
        优先使用直接配置的webhook_url，如果没有则尝试从环境变量获取
        
        Args:
            settings_dict (dict): 通知设置字典
            
        Returns:
            str: Webhook URL或None
        """
        # 直接配置的webhook_url
        webhook_url = settings_dict.get('webhook_url')
        if webhook_url:
            # 安全检查 - 确保URL是有效的
            if not webhook_url.startswith(('http://', 'https://')):
                if not webhook_url.startswith('http'):
                    logger.warning(f"Webhook URL格式可能不正确: {webhook_url}")
            return webhook_url
            
        # 从环境变量获取
        webhook_env = settings_dict.get('webhook_env')
        if webhook_env and webhook_env in os.environ:
            webhook_url = os.environ.get(webhook_env)
            # 安全检查 - 编写日志时隐藏大部分URL
            if webhook_url and len(webhook_url) > 10:
                visible_part = webhook_url[:6] + "..." + webhook_url[-4:]
                logger.info(f"已从环境变量 {webhook_env} 获取Webhook URL: {visible_part}")
            else:
                logger.info(f"已从环境变量 {webhook_env} 获取Webhook URL")
            return webhook_url
        elif webhook_env:
            logger.warning(f"环境变量 {webhook_env} 未设置")
            
        return None
    
    def _validate_notification_settings(self):
        """验证通知设置并添加到Apprise"""
        notification_settings = self.settings.get('notification', {})
        if not notification_settings.get('enabled', False):
            logger.warning("通知功能未启用")
            return False
        
        # 添加通知渠道到Apprise
        channels_added = 0
        
        # 钉钉通知
        dingtalk_settings = notification_settings.get('dingtalk', {})
        if dingtalk_settings.get('enabled', False):
            webhook_url = self._get_webhook_url(dingtalk_settings)
            if webhook_url:
                # 获取钉钉密钥
                secret = dingtalk_settings.get('secret', '')
                
                # 构建钉钉通知URL
                # 对于钉钉，使用带有secret的格式
                if secret:
                    apprise_url = f"dingtalk://{webhook_url}/{secret}"
                else:
                    # 如果URL中已包含完整路径，使用jsons格式
                    if webhook_url.startswith('http'):
                        apprise_url = f"jsons://{webhook_url}"
                    else:
                        apprise_url = f"dingtalk://{webhook_url}"
                
                self.apprise.add(apprise_url)
                channels_added += 1
                logger.info(f"已添加钉钉通知渠道: {apprise_url.split('://')[0]}")
            else:
                logger.warning("未找到钉钉Webhook URL，跳过配置")
        
        # 飞书通知
        feishu_settings = notification_settings.get('feishu', {})
        if feishu_settings.get('enabled', False):
            webhook_url = self._get_webhook_url(feishu_settings)
            if webhook_url:
                # 飞书使用json格式，但可以使用专用的插件
                # 检查URL格式
                if webhook_url.startswith('http'):
                    # 使用jsons格式，自定义JSON结构
                    apprise_url = f"jsons://{webhook_url}"
                else:
                    apprise_url = f"lark://{webhook_url}"  # lark是飞书的国际名称
                
                self.apprise.add(apprise_url)
                channels_added += 1
                logger.info(f"已添加飞书通知渠道: {apprise_url.split('://')[0]}")
            else:
                logger.warning("未找到飞书Webhook URL，跳过配置")
        
        # 企业微信通知
        wechat_settings = notification_settings.get('wechat', {})
        if wechat_settings.get('enabled', False):
            webhook_url = self._get_webhook_url(wechat_settings)
            if webhook_url:
                # 企业微信通知URL格式
                if webhook_url.startswith('http'):
                    # 使用jsons格式，自定义JSON结构
                    apprise_url = f"wxwork://{webhook_url}"
                else:
                    apprise_url = f"wxwork://{webhook_url}"
                
                self.apprise.add(apprise_url)
                channels_added += 1
                logger.info(f"已添加企业微信通知渠道: {apprise_url.split('://')[0]}")
            else:
                logger.warning("未找到企业微信Webhook URL，跳过配置")
        
        # 其他可能的通知渠道，可以根据settings文件中的配置添加
        other_channels = notification_settings.get('apprise_urls', [])
        for channel_url in other_channels:
            if channel_url:
                try:
                    self.apprise.add(channel_url)
                    channels_added += 1
                    scheme = channel_url.split('://')[0] if '://' in channel_url else 'unknown'
                    logger.info(f"已添加其他通知渠道: {scheme}")
                except Exception as e:
                    logger.error(f"添加通知渠道 '{channel_url}' 失败: {e}")
        
        if channels_added == 0:
            logger.warning("未添加任何通知渠道")
            return False
        
        logger.info(f"通知设置验证通过，已添加{channels_added}个通知渠道")
        return True
    
    def load_result(self):
        """加载分析结果"""
        try:
            # 获取文件扩展名
            file_ext = self.file_path.split('.')[-1].lower()
            
            if file_ext == 'json':
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.result_data = json.load(f)
            elif file_ext == 'csv':
                self.result_data = pd.read_csv(self.file_path)
            elif file_ext == 'tsv':
                self.result_data = pd.read_csv(self.file_path, sep='\t')
            elif file_ext == 'txt' or file_ext == 'md':
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 尝试解析为TSV
                try:
                    import io
                    self.result_data = pd.read_csv(io.StringIO(content), sep='\t')
                except:
                    # 如果解析失败，则作为纯文本保存
                    self.result_data = content
            else:
                logger.error(f"不支持的文件格式: {file_ext}")
                raise ValueError(f"不支持的文件格式: {file_ext}")
                
            logger.info(f"成功加载分析结果文件: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"加载分析结果文件失败: {e}")
            return False
    
    def prepare_message(self):
        """准备通知消息内容"""
        notification_settings = self.settings.get('notification', {})
        template = notification_settings.get('template', '分析完成，共有{total_records}条记录')
        
        # 检查是否是工作流状态文件
        if isinstance(self.result_data, dict) and 'workflow_status' in self.result_data:
            return self._prepare_workflow_status_message()
        
        # 检查是否是仪表盘状态文件
        if isinstance(self.result_data, dict) and 'dashboard_status' in self.result_data:
            return self._prepare_dashboard_status_message()
        
        # 检查是否是爬虫状态文件
        if isinstance(self.result_data, dict) and 'crawler_status' in self.result_data:
            return self._prepare_crawler_status_message()
        
        # 检查是否是分析器状态文件
        if isinstance(self.result_data, dict) and 'analyzer_status' in self.result_data:
            return self._prepare_analyzer_status_message()
        
        # 检查是否是代理池状态文件
        if isinstance(self.result_data, dict) and 'proxy_status' in self.result_data:
            return self._prepare_proxy_status_message()
        
        # 获取统计信息
        record_count = 0
        date_range_start = datetime.now().strftime('%Y-%m-%d')
        date_range_end = date_range_start
        ai_analysis_title = "数据分析"
        ai_analysis_content = ""
        
        # 获取仓库URL，可以从设置或环境变量中获取
        repo_url = self.settings.get('repo_url', os.environ.get('REPO_URL', ''))
        if not repo_url:
            # 尝试从git配置获取
            try:
                import subprocess
                remote_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], 
                                                    stderr=subprocess.PIPE, text=True).strip()
                if remote_url:
                    # 处理可能的SSH格式
                    if remote_url.startswith('git@'):
                        repo_url = remote_url.replace(':', '/').replace('git@', 'https://').rstrip('.git')
                    else:
                        repo_url = remote_url.rstrip('.git')
            except Exception as e:
                logger.debug(f"无法从git获取仓库URL: {e}")
                repo_url = "https://github.com/用户名/仓库名"
        
        # 根据数据类型处理
        if isinstance(self.result_data, pd.DataFrame):
            record_count = len(self.result_data)
            top_records = self.result_data.head(5)
            
            # 尝试获取日期范围
            date_field = notification_settings.get('date_field', 'date')
            if date_field in self.result_data.columns:
                try:
                    sorted_dates = sorted(self.result_data[date_field].dropna())
                    if sorted_dates:
                        date_range_start = str(sorted_dates[0])
                        date_range_end = str(sorted_dates[-1])
                except Exception as e:
                    logger.warning(f"提取日期范围失败: {e}")
            
            # 尝试获取分析结果
            ai_field = notification_settings.get('ai_field', 'analysis')
            if ai_field in self.result_data.columns and not self.result_data[ai_field].isna().all():
                ai_sample = self.result_data[ai_field].dropna().iloc[0] if not self.result_data[ai_field].dropna().empty else ""
                ai_analysis_content = ai_sample[:500] + "..." if len(ai_sample) > 500 else ai_sample
            
            # 格式化分析内容为列表
            category_field = notification_settings.get('category_field', '类别')
            if category_field in self.result_data.columns:
                category_stats = self.result_data[category_field].value_counts().to_dict()
                if category_stats:
                    stats_text = "\n".join([f"- {category}: {count}条" for category, count in category_stats.items()])
                    if not ai_analysis_content:
                        ai_analysis_content = stats_text
                    else:
                        ai_analysis_content += f"\n\n**分类统计**:\n{stats_text}"
            
        elif isinstance(self.result_data, list) and self.result_data:
            record_count = len(self.result_data)
            
            # 尝试提取日期信息
            date_keys = ['date', '日期', 'time', '时间', 'created_at', 'updated_at']
            for item in self.result_data:
                for key in date_keys:
                    if key in item and item[key]:
                        try:
                            dates = [str(item[key]) for item in self.result_data if key in item and item[key]]
                            if dates:
                                sorted_dates = sorted(dates)
                                date_range_start = sorted_dates[0]
                                date_range_end = sorted_dates[-1]
                                break
                        except:
                            pass
                if date_range_start != date_range_end:
                    break
                
        else:
            # 纯文本结果
            if isinstance(self.result_data, str):
                # 获取行数
                lines = self.result_data.strip().split('\n')
                record_count = len(lines) - 1 if len(lines) > 1 else 0  # 减去表头
                ai_analysis_content = "\n".join(lines[:5]) + "\n..." if len(lines) > 5 else self.result_data
        
        # 格式化消息
        try:
            message = template.format(
                site_name=self.site_id,
                total_records=record_count,
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                ai_analysis_title=ai_analysis_title,
                ai_analysis_content=ai_analysis_content,
                repo_url=repo_url
            )
        except KeyError as e:
            logger.warning(f"格式化模板时出现未知变量: {e}，使用默认格式")
            message = f"### {self.site_id}数据更新通知\n\n总记录数: {record_count}\n分析日期: {datetime.now().strftime('%Y-%m-%d')}"
        
        return message
    
    def _prepare_workflow_status_message(self):
        """准备工作流状态通知消息"""
        workflow_status = self.result_data['workflow_status']
        
        # 检查整体状态
        failed_jobs = []
        success_jobs = []
        skipped_jobs = []
        
        for job_name, result in workflow_status.items():
            if job_name in ['date', 'sites', 'action', 'run_id', 'run_url']:
                continue
            
            if result == 'success':
                success_jobs.append(job_name)
            elif result == 'failure':
                failed_jobs.append(job_name)
            elif result == 'skipped':
                skipped_jobs.append(job_name)
        
        # 确定整体状态
        if failed_jobs:
            status_emoji = "❌"
            status_text = "部分失败"
        elif success_jobs:
            status_emoji = "✅"
            status_text = "全部完成"
        else:
            status_emoji = "⚠️"
            status_text = "无结果"
        
        # 构建消息
        message = f"### {status_emoji} {self.site_id}{status_text}\n\n"
        
        # 基本信息
        if 'date' in workflow_status:
            message += f"- **日期**: {workflow_status['date']}\n"
        if 'action' in workflow_status:
            message += f"- **操作**: {workflow_status['action']}\n"
        if 'sites' in workflow_status:
            sites = workflow_status['sites']
            if isinstance(sites, list):
                message += f"- **站点**: {', '.join(sites) if len(sites) <= 3 else f'{len(sites)}个站点'}\n"
        
        # 执行结果
        message += "\n**执行结果**:\n"
        job_names = {
            'setup': '环境准备',
            'proxy_pool': '代理池更新', 
            'crawl': '数据爬取',
            'analyze': '数据分析',
            'dashboard': '仪表盘更新',
            'pre_check': '预检查',
            'analyze': '分析'
        }
        
        for job_name, result in workflow_status.items():
            if job_name in ['date', 'sites', 'action', 'run_id', 'run_url']:
                continue
                
            display_name = job_names.get(job_name, job_name)
            if result == 'success':
                message += f"- ✅ {display_name}: 成功\n"
            elif result == 'failure':
                message += f"- ❌ {display_name}: 失败\n"
            elif result == 'skipped':
                message += f"- ⏭️ {display_name}: 跳过\n"
            else:
                message += f"- ⚪ {display_name}: {result}\n"
        
        # 运行链接
        if 'run_url' in workflow_status:
            run_id = workflow_status.get('run_id', '未知')
            message += f"\n[查看详细日志]({workflow_status['run_url']})"
        
        return message
    
    def _prepare_dashboard_status_message(self):
        """准备仪表盘状态通知消息"""
        dashboard_status = self.result_data['dashboard_status']
        
        # 确定状态
        status = dashboard_status.get('status', 'unknown')
        if status == 'success':
            status_emoji = "✅"
            status_text = "更新成功"
        elif status == 'failure':
            status_emoji = "❌"
            status_text = "更新失败"
        else:
            status_emoji = "⚠️"
            status_text = f"状态: {status}"
        
        # 构建消息
        message = f"### {status_emoji} 监控仪表盘{status_text}\n\n"
        
        # 基本信息
        if status == 'success':
            if 'url' in dashboard_status:
                message += f"- **URL**: {dashboard_status['url']}\n"
            if 'update_time' in dashboard_status:
                message += f"- **更新时间**: {dashboard_status['update_time']}\n"
        else:
            if 'failed_stage' in dashboard_status:
                message += f"- **失败阶段**: {dashboard_status['failed_stage']}\n"
        
        # 运行链接
        if 'run_url' in dashboard_status:
            run_id = dashboard_status.get('run_id', '未知')
            message += f"- **运行ID**: [#{run_id}]({dashboard_status['run_url']})\n"
        
        return message
    
    def _prepare_crawler_status_message(self):
        """准备爬虫状态通知消息"""
        crawler_status = self.result_data['crawler_status']
        
        # 检查整体状态
        pre_check_result = crawler_status.get('pre_check', 'unknown')
        crawl_result = crawler_status.get('crawl', 'unknown')
        
        # 确定整体状态
        if pre_check_result == 'success' and crawl_result == 'success':
            status_emoji = "✅"
            status_text = "任务成功"
        elif pre_check_result == 'failure' or crawl_result == 'failure':
            status_emoji = "❌"
            status_text = "任务失败"
        else:
            status_emoji = "⚠️"
            status_text = "任务状态异常"
        
        # 构建消息
        site_name = self.site_id
        message = f"### {status_emoji} {site_name}爬虫{status_text}\n\n"
        
        # 基本信息
        if 'site_id' in crawler_status:
            message += f"- **站点**: {crawler_status['site_id']}\n"
        if 'date' in crawler_status:
            message += f"- **日期**: {crawler_status['date']}\n"
        
        # 执行结果
        message += "\n**执行结果**:\n"
        message += f"- {'✅' if pre_check_result == 'success' else '❌'} 预检查: {pre_check_result}\n"
        message += f"- {'✅' if crawl_result == 'success' else '❌'} 数据爬取: {crawl_result}\n"
        
        # 运行链接
        if 'run_url' in crawler_status:
            run_id = crawler_status.get('run_id', '未知')
            message += f"\n[查看详细日志]({crawler_status['run_url']})"
        
        return message
    
    def _prepare_analyzer_status_message(self):
        """准备分析器状态通知消息"""
        analyzer_status = self.result_data['analyzer_status']
        
        # 检查整体状态
        pre_check_result = analyzer_status.get('pre_check', 'unknown')
        analyze_result = analyzer_status.get('analyze', 'unknown')
        
        # 确定整体状态
        if pre_check_result == 'success' and analyze_result == 'success':
            status_emoji = "✅"
            status_text = "分析成功"
        elif pre_check_result == 'failure' or analyze_result == 'failure':
            status_emoji = "❌"
            status_text = "分析失败"
        else:
            status_emoji = "⚠️"
            status_text = "分析状态异常"
        
        # 构建消息
        site_name = self.site_id
        message = f"### {status_emoji} {site_name}数据{status_text}\n\n"
        
        # 基本信息
        if 'site_id' in analyzer_status:
            message += f"- **站点**: {analyzer_status['site_id']}\n"
        if 'date' in analyzer_status:
            message += f"- **日期**: {analyzer_status['date']}\n"
        
        # 执行结果
        message += "\n**执行结果**:\n"
        message += f"- {'✅' if pre_check_result == 'success' else '❌'} 预检查: {pre_check_result}\n"
        message += f"- {'✅' if analyze_result == 'success' else '❌'} 数据分析: {analyze_result}\n"
        
        # 运行链接
        if 'run_url' in analyzer_status:
            run_id = analyzer_status.get('run_id', '未知')
            message += f"\n[查看详细日志]({analyzer_status['run_url']})"
        
        return message
    
    def _prepare_proxy_status_message(self):
        """准备代理池状态通知消息"""
        proxy_status = self.result_data['proxy_status']
        
        # 检查整体状态
        main_success = proxy_status.get('main_success', 'false') == 'true'
        fallback_success = proxy_status.get('fallback_success', 'false') == 'true'
        
        # 确定整体状态
        if main_success:
            status_emoji = "✅"
            status_text = "管理成功"
        elif fallback_success:
            status_emoji = "⚠️"
            status_text = "备用操作成功"
        else:
            status_emoji = "❌"
            status_text = "管理失败"
        
        # 构建消息
        message = f"### {status_emoji} 代理池{status_text}\n\n"
        
        # 基本信息
        if 'main_action' in proxy_status:
            message += f"- **主操作**: {proxy_status['main_action']}\n"
        if 'fallback_action' in proxy_status and proxy_status['fallback_action']:
            message += f"- **备用操作**: {proxy_status['fallback_action']}\n"
        if 'proxy_source' in proxy_status:
            message += f"- **代理源**: {proxy_status['proxy_source']}\n"
        
        # 代理统计
        valid_count = proxy_status.get('valid_count', 0)
        failed_count = proxy_status.get('failed_count', 0)
        message += f"- **代理统计**: 有效 {valid_count} 个，失效 {failed_count} 个\n"
        
        # 执行结果
        message += "\n**执行结果**:\n"
        if main_success:
            message += f"- ✅ 主操作: {proxy_status.get('main_action', '未知')}\n"
        else:
            message += f"- ❌ 主操作: {proxy_status.get('main_action', '未知')}\n"
            if fallback_success:
                message += f"- ✅ 备用操作: {proxy_status.get('fallback_action', '未知')}\n"
            elif proxy_status.get('fallback_action'):
                message += f"- ❌ 备用操作: {proxy_status.get('fallback_action', '未知')}\n"
        
        # 运行链接
        if 'run_url' in proxy_status:
            run_id = proxy_status.get('run_id', '未知')
            message += f"\n[查看详细日志]({proxy_status['run_url']})"
        
        return message
    
    def send_notifications(self):
        """发送所有通知"""
        if not self.result_data:
            logger.error("没有分析结果可通知")
            return False
        
        if not self.apprise or len(self.apprise) == 0:
            logger.error("没有配置通知渠道")
            return False
        
        # 准备消息内容
        message = self.prepare_message()
        title = f"{self.site_id}分析结果"
        
        # 记录通知内容的摘要（仅供调试）
        if logger.isEnabledFor(logging.DEBUG):
            message_preview = message[:100] + "..." if len(message) > 100 else message
            logger.debug(f"通知内容预览: {message_preview}")
        
        try:
            # 使用Apprise发送通知
            results = self.apprise.notify(
                title=title,
                body=message,
                notify_type=apprise.NotifyType.INFO,
                body_format=apprise.NotifyFormat.MARKDOWN,
            )
            
            # 分析结果
            success_count = sum(1 for result in results if result)
            total_count = len(results)
            
            if success_count > 0:
                logger.info(f"通知发送完成，成功: {success_count}/{total_count} 个渠道")
                
                # 如果有部分失败，记录详细日志
                if success_count < total_count:
                    failed_indices = [i for i, result in enumerate(results) if not result]
                    try:
                        # 尝试获取服务器列表以识别失败的服务
                        servers = list(self.apprise.servers())
                        for idx in failed_indices:
                            if idx < len(servers):
                                logger.warning(f"通知发送失败: {servers[idx].url}")
                            else:
                                logger.warning(f"通知发送失败: 服务器索引 {idx}")
                    except Exception as e:
                        logger.warning(f"无法获取详细的失败信息: {e}")
                
                # 至少有一个渠道发送成功，算作整体成功
                return True
            else:
                logger.error("所有通知渠道均发送失败")
                return False
                
        except Exception as e:
            logger.exception(f"通知发送异常: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='通知脚本 - 发送分析结果通知')
    parser.add_argument('--file', '-f', required=True, help='分析结果文件路径')
    parser.add_argument('--site', '-s', required=True, help='网站ID')
    parser.add_argument('--settings', help='设置文件路径')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 创建通知发送器实例
        notifier = Notifier(
            file_path=args.file,
            site_id=args.site,
            settings_path=args.settings
        )
        
        # 发送通知
        if notifier.send_notifications():
            logger.info("通知任务完成")
            return 0
        else:
            logger.error("发送通知失败")
            return 1
    except Exception as e:
        logger.exception(f"通知过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 