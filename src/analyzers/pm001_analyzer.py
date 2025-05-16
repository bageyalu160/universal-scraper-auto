#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd
import logging
from datetime import datetime
import json
import re
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pm001_analyzer')

def load_prompt(prompt_file):
    """加载分析提示词模板"""
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"加载提示词模板时出错: {e}")
        return None

def analyze_pm001_data(data_file, config, output_dir=None, api_key=None):
    """
    分析PM001数据
    
    Args:
        data_file: 数据文件路径
        config: 配置字典
        output_dir: 输出目录
        api_key: API密钥（可选）
        
    Returns:
        dict: 包含分析结果的字典
    """
    logger.info(f"开始分析PM001数据: {data_file}")
    
    # 检查文件存在
    if not os.path.exists(data_file):
        logger.error(f"数据文件不存在: {data_file}")
        return {"status": "error", "message": "数据文件不存在"}
    
    # 获取配置
    analysis_config = config.get('analysis', {})
    
    # 加载提示词模板
    prompt_file = os.path.join('config', 'analysis', 'prompts', 'pm001_prompt.txt')
    prompt_template = load_prompt(prompt_file)
    if not prompt_template:
        logger.error("无法加载提示词模板")
        return {"status": "error", "message": "无法加载提示词模板"}
    
    try:
        # 读取数据
        df = pd.read_csv(data_file, sep='\t')
        logger.info(f"成功读取数据文件，包含 {len(df)} 条记录")
        
        # 如果数据为空，返回警告
        if len(df) == 0:
            logger.warning("数据文件为空")
            return {"status": "warning", "message": "数据文件为空"}
        
        # 准备分析结果
        results = []
        
        # 简化版：对每条记录进行简单分类
        for _, row in df.iterrows():
            title = row.get('title', '')
            
            # 简单规则分类
            record = {
                'board_id': row.get('board_id', ''),
                'board_name': row.get('board_name', ''),
                'post_id': row.get('post_id', ''),
                'title': title,
                'author': row.get('author', ''),
                'date': row.get('date', ''),
                'replies': row.get('replies', ''),
                'views': row.get('views', '')
            }
            
            # 简单分类规则（完整版应该使用AI分析）
            if re.search(r'收|收购|求购|求|寻', title):
                record['意图分类'] = '收购'
            elif re.search(r'出|售|卖|转让', title):
                record['意图分类'] = '出售'
            else:
                record['意图分类'] = '其他'
            
            # 简单价格提取（正则匹配数字+元/块/价等）
            price_match = re.search(r'(\d+)[元块价]|(\d+)出', title)
            if price_match:
                price = price_match.group(1) or price_match.group(2)
                record['价格描述'] = f"{price}元"
                record['数值价格'] = price
            else:
                record['价格描述'] = ''
                record['数值价格'] = ''
            
            # 物品名称抽取（简化版，实际应用中应当使用NLP或AI）
            # 这里简单提取第一个名词短语
            name_match = re.search(r'[^\d\W]+[币券张版]|[^\d\W]+钱|[^\d\W]+邮票', title)
            if name_match:
                record['物品名称'] = name_match.group(0)
            else:
                record['物品名称'] = '未识别物品'
            
            # 设置价格类型
            if record['意图分类'] == '收购':
                record['价格类型'] = '收购价'
            elif record['意图分类'] == '出售':
                record['价格类型'] = '出售价'
            else:
                record['价格类型'] = 'N/A'
            
            # 添加到结果
            results.append(record)
        
        # 创建结果DataFrame
        results_df = pd.DataFrame(results)
        
        # 设置输出路径
        filename = os.path.basename(data_file)
        output_filename = f"analysis_{filename}"
        
        if output_dir:
            output_path = os.path.join(output_dir, output_filename)
        else:
            output_path = output_filename
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存分析结果
        results_df.to_csv(output_path, sep='\t', index=False, encoding='utf-8')
        logger.info(f"成功保存分析结果到 {output_path}")
        
        # 创建汇总信息
        summary = {
            "total_records": len(results_df),
            "buy_count": len(results_df[results_df['意图分类'] == '收购']),
            "sell_count": len(results_df[results_df['意图分类'] == '出售']),
            "other_count": len(results_df[results_df['意图分类'] == '其他'])
        }
        
        # 保存汇总信息
        summary_path = os.path.join(os.path.dirname(output_path), f"summary_{os.path.splitext(output_filename)[0]}.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"成功保存汇总信息到 {summary_path}")
        
        return {
            "status": "success",
            "message": "分析完成",
            "output_path": output_path,
            "summary_path": summary_path,
            "summary": summary
        }
    
    except Exception as e:
        logger.exception(f"分析数据时出错: {e}")
        return {"status": "error", "message": f"分析数据时出错: {e}"}

if __name__ == "__main__":
    """直接运行此脚本的测试代码"""
    import yaml
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='分析PM001数据')
    parser.add_argument('--file', required=True, help='数据文件路径')
    parser.add_argument('--output-dir', help='输出目录')
    args = parser.parse_args()
    
    # 加载全局配置
    config_path = os.path.join('config', 'settings.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        global_config = yaml.safe_load(f)
    
    # 运行分析
    result = analyze_pm001_data(args.file, global_config, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2)) 