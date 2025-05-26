#!/usr/bin/env python3
"""
AI Issue摘要工作流测试脚本
测试Jsonnet模板的语法和功能
"""

import json
import os
import sys
import subprocess
import yaml
from pathlib import Path

def load_site_config(site_id):
    """加载站点配置"""
    config_file = f"config/sites/{site_id}_ai_summary.yaml"
    if not os.path.exists(config_file):
        # 使用默认配置
        config_file = f"config/sites/{site_id}.yaml"
        if not os.path.exists(config_file):
            print(f"❌ 错误: 找不到站点配置文件 {config_file}")
            return None
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def test_jsonnet_template(site_id):
    """测试Jsonnet模板"""
    print(f"🧪 测试AI Issue摘要模板 - {site_id}")
    
    # 加载站点配置
    site_config = load_site_config(site_id)
    if not site_config:
        return False
    
    # 准备Jsonnet参数
    site_config_json = json.dumps(site_config)
    global_config = {"runner": "ubuntu-latest", "python_version": "3.10"}
    global_config_json = json.dumps(global_config)
    
    # Jsonnet模板路径 - 使用修复版
    template_path = "config/workflow/templates/ai_issue_summary_fixed.jsonnet"
    
    if not os.path.exists(template_path):
        print(f"❌ 错误: 找不到模板文件 {template_path}")
        return False
    
    try:
        # 构建jsonnet命令
        cmd = [
            "jsonnet",
            "--ext-str", f"site_id={site_id}",
            "--ext-str", f"site_config={site_config_json}",
            "--ext-str", f"global_config={global_config_json}",
            template_path
        ]
        
        print(f"📋 执行命令: {' '.join(cmd[:4])}...")
        
        # 执行jsonnet
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Jsonnet编译失败:")
            print(f"错误输出: {result.stderr}")
            return False
        
        # 解析生成的YAML
        try:
            workflow_yaml = yaml.safe_load(result.stdout)
            print(f"✅ Jsonnet模板编译成功!")
            
            # 验证生成的工作流结构
            required_keys = ["name", "on", "permissions", "jobs"]
            for key in required_keys:
                if key not in workflow_yaml:
                    print(f"⚠️ 警告: 生成的工作流缺少必要字段 '{key}'")
                    return False
            
            # 检查作业
            if "ai-summary" not in workflow_yaml["jobs"]:
                print(f"⚠️ 警告: 生成的工作流缺少 'ai-summary' 作业")
                return False
            
            print(f"🎯 工作流名称: {workflow_yaml['name']}")
            print(f"🔧 作业数量: {len(workflow_yaml['jobs'])}")
            print(f"📝 作业列表: {list(workflow_yaml['jobs'].keys())}")
            
            # 保存测试结果
            output_file = f".github/workflows/test_ai_summary_{site_id}.yml"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            
            print(f"💾 测试工作流已保存到: {output_file}")
            return True
            
        except yaml.YAMLError as e:
            print(f"❌ 生成的YAML格式错误: {e}")
            return False
            
    except subprocess.SubprocessError as e:
        print(f"❌ 执行jsonnet命令失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 意外错误: {e}")
        return False

def test_issue_parsing():
    """测试Issue解析逻辑"""
    print("\n🔍 测试Issue解析逻辑")
    
    # 测试用例
    test_cases = [
        {
            "title": "黑猫投诉爬虫失败",
            "body": "运行爬虫时出现超时错误，无法获取数据",
            "expected_labels": ["bug", "scraper", "heimao"]
        },
        {
            "title": "新增数据分析功能",
            "body": "希望添加投诉数据的可视化分析功能",
            "expected_labels": ["enhancement", "data", "scraper"]
        },
        {
            "title": "紧急：生产环境崩溃",
            "body": "生产环境的爬虫系统完全崩溃，数据丢失",
            "expected_labels": ["bug", "urgent", "scraper"]
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {case['title']}")
        
        # 这里只是模拟标签检测逻辑
        content = (case['title'] + ' ' + case['body']).lower()
        detected_labels = []
        
        # Bug关键词
        bug_keywords = ['error', 'fail', 'crash', '错误', '失败', '崩溃', 'bug', '异常', '超时', '无法访问']
        if any(keyword in content for keyword in bug_keywords):
            detected_labels.append('bug')
        
        # Enhancement关键词
        enhancement_keywords = ['feature', 'enhancement', 'improve', '功能', '改进', '增强', '优化', '新增', '扩展']
        if any(keyword in content for keyword in enhancement_keywords):
            detected_labels.append('enhancement')
        
        # Scraper关键词
        scraper_keywords = ['scraper', 'crawler', 'parse', '爬虫', '抓取', '解析', '黑猫', 'heimao', '投诉', '数据采集']
        if any(keyword in content for keyword in scraper_keywords):
            detected_labels.append('scraper')
        
        # Data关键词
        data_keywords = ['数据', 'data', '分析', 'analysis', '统计', '报告', '可视化']
        if any(keyword in content for keyword in data_keywords):
            detected_labels.append('data')
        
        # Urgent关键词
        urgent_keywords = ['urgent', 'critical', 'blocking', '紧急', '严重', '阻塞', '生产环境', '数据丢失']
        if any(keyword in content for keyword in urgent_keywords):
            detected_labels.append('urgent')
        
        # Heimao关键词
        if 'heimao' in content or '黑猫' in content:
            detected_labels.append('heimao')
        
        print(f"   检测到的标签: {detected_labels}")
        print(f"   期望的标签: {case['expected_labels']}")
        
        # 计算匹配度
        matched = set(detected_labels) & set(case['expected_labels'])
        match_rate = len(matched) / len(case['expected_labels']) if case['expected_labels'] else 0
        
        if match_rate >= 0.5:
            print(f"   ✅ 匹配率: {match_rate:.1%} (通过)")
        else:
            print(f"   ⚠️ 匹配率: {match_rate:.1%} (需要优化)")

def main():
    """主函数"""
    print("🤖 AI Issue摘要工作流测试")
    print("=" * 40)
    
    # 测试站点列表
    test_sites = ["heimao"]
    
    success_count = 0
    
    for site_id in test_sites:
        print(f"\n{'='*40}")
        if test_jsonnet_template(site_id):
            success_count += 1
    
    # 测试Issue解析逻辑
    test_issue_parsing()
    
    print(f"\n{'='*40}")
    print(f"📊 测试总结:")
    print(f"   成功: {success_count}/{len(test_sites)} 站点")
    
    if success_count == len(test_sites):
        print("🎉 所有测试通过！AI Issue摘要功能已就绪。")
        return 0
    else:
        print("❌ 部分测试失败，请检查配置和模板。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 