#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器快速运行脚本
在项目根目录运行，提供简化的命令行接口
"""

import os
import sys
import subprocess
from pathlib import Path

# 确保在项目根目录
script_dir = Path(__file__).parent
os.chdir(script_dir)

def get_all_sites():
    """获取所有可用站点"""
    sites_dir = Path('config/sites')
    if not sites_dir.exists():
        return []
    
    sites = []
    for config_file in sites_dir.glob("*.yaml"):
        sites.append(config_file.stem)
    return sorted(sites)

def load_site_config(site_id):
    """加载站点配置"""
    config_file = Path('config/sites') / f"{site_id}.yaml"
    if not config_file.exists():
        return None
    
    try:
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except ImportError:
        print("警告: 需要安装pyyaml库: pip install pyyaml")
        return None
    except Exception as e:
        print(f"加载站点配置失败: {e}")
        return None

def show_help():
    """显示帮助信息"""
    print("""
🔧 Universal Scraper 工作流生成器
=====================================

快速命令:
  python3 run_workflow_generator.py <命令> [参数]

主要命令:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 查看帮助和状态:
  help                           显示此帮助信息
  list-sites                     列出所有可用站点
  validate [站点ID]              验证站点配置
  
🚀 增强版生成器 (推荐):
  enhanced-analyzer <站点ID>      生成增强版分析工作流
  enhanced-crawler <站点ID>       生成增强版爬虫工作流
  enhanced-all                   生成所有站点的增强版工作流
  
📜 传统YAML生成器:
  yaml-analyzer <站点ID>         生成YAML分析工作流
  yaml-crawler <站点ID>          生成YAML爬虫工作流
  yaml-all                       生成所有YAML工作流
  
🔍 标准Jsonnet生成器:
  jsonnet <模板名> <输出名> [站点ID]  生成Jsonnet工作流
  
🛠️ 工具命令:
  setup                          安装依赖项
  clean                          清理生成的工作流文件
  test <站点ID>                   测试站点配置

使用示例:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 生成heimao站点的增强版分析工作流
python3 run_workflow_generator.py enhanced-analyzer heimao

# 列出所有可用站点
python3 run_workflow_generator.py list-sites

# 生成所有站点的增强版工作流
python3 run_workflow_generator.py enhanced-all

# 验证特定站点配置
python3 run_workflow_generator.py validate heimao

添加参数:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
--verbose, -v                   启用详细日志
--dry-run                       试运行模式，不实际生成文件
--help                          显示详细帮助

环境检查:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
确保已安装必要依赖: pip install -r requirements.txt
注意: 请使用 python3 而不是 python
""")

def handle_list_sites():
    """处理列出站点命令"""
    print("\n📋 可用站点列表:")
    print("=" * 50)
    
    sites = get_all_sites()
    if not sites:
        print("  没有找到站点配置文件")
        return True
    
    for site_id in sites:
        config = load_site_config(site_id)
        site_name = site_id
        if config and 'site_info' in config:
            site_name = config['site_info'].get('name', site_id)
        print(f"  • {site_id} - {site_name}")
    
    print(f"\n总共找到 {len(sites)} 个站点配置")
    return True

def handle_validate(site_id=None):
    """处理验证配置命令"""
    if site_id:
        # 验证特定站点
        print(f"\n🔍 验证站点配置: {site_id}")
        config = load_site_config(site_id)
        if config:
            print(f"✅ 站点 {site_id} 配置有效")
            return True
        else:
            print(f"❌ 站点 {site_id} 配置无效或不存在")
            return False
    else:
        # 验证所有站点
        print("\n🔍 验证所有站点配置:")
        print("=" * 50)
        
        sites = get_all_sites()
        if not sites:
            print("  没有找到站点配置文件")
            return True
        
        success = True
        for site_id in sites:
            config = load_site_config(site_id)
            if config:
                print(f"  ✅ {site_id}")
            else:
                print(f"  ❌ {site_id}")
                success = False
        
        print(f"\n验证完成: {len(sites)} 个站点")
        return success

def handle_clean(dry_run=False):
    """处理清理命令"""
    output_dir = Path('.github/workflows')
    if not output_dir.exists():
        print("📁 工作流目录不存在，无需清理")
        return True
    
    print(f"\n🗑️ 清理工作流文件 ({'试运行模式' if dry_run else '实际执行'}):")
    print("=" * 50)
    
    yml_files = list(output_dir.glob('*.yml'))
    if not yml_files:
        print("  没有找到工作流文件")
        return True
    
    for file in yml_files:
        if not dry_run:
            file.unlink()
        print(f"  🗑️ {'将删除' if dry_run else '已删除'}: {file}")
    
    print(f"\n清理完成: {len(yml_files)} 个文件")
    return True

def run_command(cmd_args):
    """运行命令"""
    cli_script = "scripts/workflow_generator/enhanced_cli.py"
    
    if not Path(cli_script).exists():
        print(f"❌ 错误: 找不到CLI脚本 {cli_script}")
        return 1
    
    # 构建完整命令
    full_cmd = [sys.executable, cli_script] + cmd_args
    
    try:
        # 运行命令
        result = subprocess.run(full_cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ 运行命令时出错: {e}")
        return 1

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return 0
    
    command = sys.argv[1].lower()
    
    # 处理帮助命令
    if command in ['help', '--help', '-h']:
        show_help()
        return 0
    
    # 检查是否需要dry-run模式
    dry_run = '--dry-run' in sys.argv
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    # 处理直接命令（不需要CLI脚本）
    if command == 'list-sites':
        return 0 if handle_list_sites() else 1
    
    elif command == 'validate':
        site_id = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
        return 0 if handle_validate(site_id) else 1
    
    elif command == 'clean':
        return 0 if handle_clean(dry_run) else 1
    
    elif command == 'setup':
        print("📦 依赖项设置:")
        print("请运行: pip install -r requirements.txt")
        print("可选: pip install jsonnet")
        return 0
    
    # 处理需要CLI脚本的命令
    command_mapping = {
        # 增强版命令
        'enhanced-analyzer': ['enhanced', 'analyzer'],
        'enhanced-crawler': ['enhanced', 'crawler'], 
        'enhanced-all': ['enhanced', 'all'],
        
        # YAML命令
        'yaml-analyzer': ['yaml', 'generate'],
        'yaml-crawler': ['yaml', 'generate'],
        'yaml-all': ['yaml', 'all'],
        
        # Jsonnet命令
        'jsonnet': ['jsonnet', 'generate'],
    }
    
    # 构建命令参数
    if command in command_mapping:
        cmd_args = command_mapping[command].copy()
        
        # 添加额外参数
        extra_args = [arg for arg in sys.argv[2:] if not arg.startswith('--')]
        
        # 特殊处理某些命令
        if command in ['yaml-analyzer', 'yaml-crawler']:
            if len(extra_args) >= 1:
                cmd_args.append(extra_args[0])  # 站点ID
                cmd_args.append('analyzer' if 'analyzer' in command else 'crawler')
                cmd_args.extend(extra_args[1:])  # 其他参数
            else:
                print(f"❌ 错误: {command} 需要站点ID参数")
                return 1
        else:
            cmd_args.extend(extra_args)
        
        # 添加全局选项
        global_options = []
        if dry_run:
            global_options.append('--dry-run')
        if verbose:
            global_options.append('--verbose')
        
        # 合并参数：全局选项 + 命令参数
        final_args = global_options + cmd_args
        
        return run_command(final_args)
    
    # 直接传递未映射的命令
    elif command.startswith('-'):
        # 处理全局选项
        return run_command(sys.argv[1:])
    
    else:
        print(f"❌ 未知命令: {command}")
        print("使用 'python3 run_workflow_generator.py help' 查看可用命令")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️ 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1) 