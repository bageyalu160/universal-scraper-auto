#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真实站点配置
"""

import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from scripts.workflow_generator.jsonnet_generator import JsonnetWorkflowGenerator

def test_real_site():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test_real_site')
    
    generator = JsonnetWorkflowGenerator(logger=logger)
    
    # 测试heimao站点
    logger.info('开始测试heimao站点的增强版分析器生成...')
    site_config = generator._load_site_config('heimao')
    
    if site_config:
        logger.info(f"heimao站点配置加载成功: {site_config.get('site_info', {}).get('name', 'heimao')}")
        
        success = generator.generate_workflow('analyzer_test', 'analyzer_enhanced_heimao', {
            'site_id': 'heimao',
            'site_config': site_config,
            'global_config': generator.global_config
        })
        
        if success:
            logger.info('✅ heimao增强版分析器生成成功')
            
            # 检查生成的文件
            output_file = Path('.github/workflows/analyzer_enhanced_heimao.yml')
            if output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    logger.info(f"生成的工作流文件: {len(lines)} 行")
                    
                    # 检查关键特性
                    features = [
                        'workflow_dispatch',
                        'repository_dispatch', 
                        'workflow_call',
                        'concurrency',
                        'permissions',
                        'timeout-minutes'
                    ]
                    
                    found_features = [f for f in features if f in content]
                    logger.info(f"包含的增强特性: {found_features}")
                    
                    print(f"\n📄 生成的工作流文件预览 (前20行):")
                    for i, line in enumerate(lines[:20], 1):
                        print(f"{i:2d}: {line}")
                    
                    if len(lines) > 20:
                        print(f"... (省略 {len(lines)-20} 行)")
                        
            return True
        else:
            logger.error('❌ heimao增强版分析器生成失败')
            return False
    else:
        logger.error('❌ heimao站点配置加载失败')
        return False

if __name__ == "__main__":
    if test_real_site():
        print("\n🎉 真实站点测试成功！")
    else:
        print("\n❌ 真实站点测试失败") 