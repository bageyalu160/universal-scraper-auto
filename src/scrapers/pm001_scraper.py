#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
import random
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pm001_scraper')

def scrape_pm001(config, output_dir=None):
    """
    PM001网站爬虫实现
    
    Args:
        config: 配置字典
        output_dir: 输出目录
        
    Returns:
        dict: 包含状态和计数的结果字典
    """
    logger.info("开始爬取PM001网站数据")
    
    # 获取配置参数
    site_config = config.get('site', {})
    scrape_config = config.get('scraping', {})
    network_config = config.get('network', {})
    parsing_config = config.get('parsing', {})
    output_config = config.get('output', {})
    
    base_url = site_config.get('base_url', 'http://www.pm001.net/')
    encoding = site_config.get('encoding', 'gbk')
    output_filename = site_config.get('output_filename', 'pm001_recent_posts.tsv')
    
    # 板块ID列表
    board_ids = scrape_config.get('board_ids', [])
    
    # 时间范围
    time_range = scrape_config.get('time_range', {})
    days_limit = time_range.get('days_limit', 2)
    
    # 分页设置
    pagination = scrape_config.get('pagination', {})
    pages_per_board = pagination.get('pages_per_board', 2)
    
    # URL格式
    url_format = scrape_config.get('url_format', {})
    board_page_url = url_format.get('board_page', '{base_url}index.asp?boardid={board_id}&page={page_num}')
    
    # 延迟设置
    delay = network_config.get('delay', {})
    page_delay = delay.get('page_delay', {'min': 2, 'max': 4})
    board_delay = delay.get('board_delay', {'min': 3, 'max': 6})
    
    # 用户代理
    user_agents = network_config.get('user_agents', [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ])
    
    # 解析器配置
    post_selector = parsing_config.get('post_selector', 'div.list')
    field_selectors = parsing_config.get('field_selectors', {})
    
    # 设置输出字段
    output_fields = output_config.get('fields', [
        "board_id", "board_name", "page", "post_id", "title", "author", "date", "replies", "views"
    ])
    
    # 当前日期和时间范围限制
    now = datetime.now()
    date_limit = now - timedelta(days=days_limit)
    
    # 创建会话对象以复用连接
    session = requests.Session()
    
    # 结果列表
    all_posts = []
    
    # 爬取每个板块
    for board in board_ids:
        board_id = board.get('id')
        board_name = board.get('name')
        category = board.get('category', '')
        
        logger.info(f"爬取板块 [{board_id}] {board_name}")
        
        # 爬取多个页面
        for page in range(1, pages_per_board + 1):
            # 构建URL
            url = board_page_url.format(base_url=base_url, board_id=board_id, page_num=page)
            
            # 随机选择User-Agent
            headers = {
                'User-Agent': random.choice(user_agents),
                'Referer': base_url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            try:
                logger.info(f"  页面 {page}: {url}")
                
                # 发送请求
                response = session.get(url, headers=headers, timeout=30)
                response.encoding = encoding
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找所有帖子
                posts = soup.select(post_selector)
                
                for post in posts:
                    try:
                        # 提取数据
                        post_data = {
                            'board_id': board_id,
                            'board_name': board_name,
                            'page': page,
                            'category': category
                        }
                        
                        # 提取标题和帖子ID
                        title_selector = field_selectors.get('title', {}).get('selector')
                        if title_selector:
                            title_elem = post.select_one(title_selector)
                            if title_elem:
                                post_data['title'] = title_elem.get_text(strip=True)
                                
                                # 提取帖子ID
                                post_id_regex = field_selectors.get('post_id', {}).get('regex')
                                if post_id_regex and 'href' in title_elem.attrs:
                                    href = title_elem['href']
                                    match = re.search(post_id_regex, href)
                                    if match:
                                        post_data['post_id'] = match.group(1)
                        
                        # 提取作者
                        author_selector = field_selectors.get('author', {}).get('selector')
                        if author_selector:
                            author_elem = post.select_one(author_selector)
                            if author_elem:
                                post_data['author'] = author_elem.get_text(strip=True)
                        
                        # 提取日期
                        date_selector = field_selectors.get('date', {}).get('selector')
                        if date_selector:
                            date_elem = post.select_one(date_selector)
                            if date_elem:
                                post_data['date'] = date_elem.get_text(strip=True)
                        
                        # 提取回复数
                        replies_selector = field_selectors.get('replies', {}).get('selector')
                        if replies_selector:
                            replies_elem = post.select_one(replies_selector)
                            if replies_elem:
                                post_data['replies'] = replies_elem.get_text(strip=True)
                        
                        # 提取浏览数
                        views_selector = field_selectors.get('views', {}).get('selector')
                        if views_selector:
                            views_elem = post.select_one(views_selector)
                            if views_elem:
                                post_data['views'] = views_elem.get_text(strip=True)
                        
                        # 添加到结果列表
                        if 'title' in post_data and post_data['title']:
                            all_posts.append(post_data)
                    
                    except Exception as e:
                        logger.error(f"处理帖子时出错: {e}")
                        continue
                
                # 每个页面之间的随机延迟
                sleep_time = random.uniform(page_delay['min'], page_delay['max'])
                logger.debug(f"  页面间延迟 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)
            
            except Exception as e:
                logger.error(f"爬取页面时出错: {url}, 错误: {e}")
                continue
        
        # 每个板块之间的随机延迟
        sleep_time = random.uniform(board_delay['min'], board_delay['max'])
        logger.debug(f"板块间延迟 {sleep_time:.2f} 秒")
        time.sleep(sleep_time)
    
    # 过滤数据为请求的字段
    filtered_posts = []
    for post in all_posts:
        filtered_post = {}
        for field in output_fields:
            filtered_post[field] = post.get(field, '')
        filtered_posts.append(filtered_post)
    
    # 保存数据
    if filtered_posts:
        # 创建DataFrame
        df = pd.DataFrame(filtered_posts)
        
        # 设置保存路径
        today_str = now.strftime('%Y-%m-%d')
        if output_dir:
            output_path = os.path.join(output_dir, f"{os.path.splitext(output_filename)[0]}_{today_str}.tsv")
        else:
            output_path = f"{os.path.splitext(output_filename)[0]}_{today_str}.tsv"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存为TSV文件
        df.to_csv(output_path, sep='\t', index=False, encoding='utf-8')
        logger.info(f"成功保存数据到 {output_path}，共 {len(filtered_posts)} 条记录")
        
        return {
            'status': 'success',
            'count': len(filtered_posts),
            'output_path': output_path
        }
    else:
        logger.warning("未获取到任何数据")
        return {
            'status': 'warning',
            'count': 0
        }

if __name__ == "__main__":
    """直接运行此脚本时的测试代码"""
    # 添加项目根目录到路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
    import yaml
    
    # 加载配置
    config_path = os.path.join('config', 'sites', 'pm001.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 设置输出目录
    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = os.path.join('data', 'daily', today)
    os.makedirs(output_dir, exist_ok=True)
    
    # 运行爬虫
    result = scrape_pm001(config, output_dir)
    print(result) 