#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版工作流生成器 - 命令行接口
支持原有CLI的所有功能，并添加增强版Jsonnet生成器支持
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# 将当前目录添加到导入路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 安全导入模块
try:
    from enhanced_jsonnet_generator import EnhancedJsonnetGenerator
except ImportError as e:
    print(f"警告: 无法导入EnhancedJsonnetGenerator: {e}")
    EnhancedJsonnetGenerator = None

try:
    from jsonnet_generator import JsonnetWorkflowGenerator
except ImportError as e:
    print(f"警告: 无法导入JsonnetWorkflowGenerator: {e}")
    JsonnetWorkflowGenerator = None

try:
    from generator import WorkflowGenerator
except ImportError as e:
    print(f"警告: 无法导入WorkflowGenerator: {e}")
    WorkflowGenerator = None


def setup_logging(verbose=False):
    """设置日志记录"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return logging.getLogger('enhanced_workflow_generator')


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="增强版工作流生成器 - 支持YAML和Jsonnet模板"
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # === 增强版Jsonnet生成器命令 ===
    enhanced_parser = subparsers.add_parser('enhanced', help='使用增强版Jsonnet生成器')
    enhanced_subparsers = enhanced_parser.add_subparsers(dest='enhanced_command', help='增强版命令')
    
    # 生成增强版分析工作流
    enhanced_analyzer_parser = enhanced_subparsers.add_parser('analyzer', help='生成增强版分析工作流')
    enhanced_analyzer_parser.add_argument('site_id', help='站点ID')
    
    # 生成增强版爬虫工作流
    enhanced_crawler_parser = enhanced_subparsers.add_parser('crawler', help='生成增强版爬虫工作流')
    enhanced_crawler_parser.add_argument('site_id', help='站点ID')
    
    # 生成所有增强版工作流
    enhanced_all_parser = enhanced_subparsers.add_parser('all', help='生成所有站点的增强版工作流')
    enhanced_all_parser.add_argument('--types', default='analyzer,crawler', help='工作流类型，逗号分隔')
    
    # === 标准Jsonnet生成器命令 ===
    jsonnet_parser = subparsers.add_parser('jsonnet', help='使用标准Jsonnet生成器')
    jsonnet_subparsers = jsonnet_parser.add_subparsers(dest='jsonnet_command', help='Jsonnet命令')
    
    # 生成Jsonnet工作流
    jsonnet_gen_parser = jsonnet_subparsers.add_parser('generate', help='生成Jsonnet工作流')
    jsonnet_gen_parser.add_argument('template_name', help='模板名称')
    jsonnet_gen_parser.add_argument('output_name', help='输出文件名')
    jsonnet_gen_parser.add_argument('--site-id', help='站点ID')
    
    # === 传统YAML生成器命令 ===
    yaml_parser = subparsers.add_parser('yaml', help='使用传统YAML生成器')
    yaml_subparsers = yaml_parser.add_subparsers(dest='yaml_command', help='YAML命令')
    
    # 生成YAML工作流
    yaml_gen_parser = yaml_subparsers.add_parser('generate', help='生成YAML工作流')
    yaml_gen_parser.add_argument('site_id', help='站点ID')
    yaml_gen_parser.add_argument('workflow_type', choices=['crawler', 'analyzer'], help='工作流类型')
    
    # 生成所有YAML工作流
    yaml_all_parser = yaml_subparsers.add_parser('all', help='生成所有YAML工作流')
    
    # === 工具命令 ===
    tools_parser = subparsers.add_parser('tools', help='工具命令')
    tools_subparsers = tools_parser.add_subparsers(dest='tools_command', help='工具子命令')
    
    # 列出可用站点
    tools_subparsers.add_parser('list-sites', help='列出所有可用站点')
    
    # 验证配置
    validate_parser = tools_subparsers.add_parser('validate', help='验证站点配置')
    validate_parser.add_argument('site_id', nargs='?', help='站点ID（可选，不指定则验证所有）')
    
    # 清理输出
    tools_subparsers.add_parser('clean', help='清理生成的工作流文件')
    
    # === 全局选项 ===
    parser.add_argument('--settings', help='设置文件路径')
    parser.add_argument('--sites-dir', help='站点配置目录')
    parser.add_argument('--output-dir', help='输出目录')
    parser.add_argument('-v', '--verbose', action='store_true', help='启用详细日志')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式，不实际生成文件')
    
    return parser.parse_args()


def get_all_sites_direct(sites_dir=None):
    """直接获取所有站点，避免继承问题"""
    from pathlib import Path
    
    sites_dir = Path(sites_dir) if sites_dir else Path('config/sites')
    if not sites_dir.exists():
        return []
    
    sites = []
    for config_file in sites_dir.glob("*.yaml"):
        sites.append(config_file.stem)
    return sorted(sites)


def run_enhanced_commands(args, logger):
    """运行增强版生成器命令"""
    if EnhancedJsonnetGenerator is None:
        logger.error("❌ 增强版生成器不可用，请检查依赖项")
        return False
        
    generator = EnhancedJsonnetGenerator(
        settings_path=args.settings,
        sites_dir=args.sites_dir,
        output_dir=args.output_dir,
        logger=logger
    )
    
    if args.enhanced_command == 'analyzer':
        logger.info(f"🚀 生成增强版分析工作流: {args.site_id}")
        if args.dry_run:
            logger.info("🔍 试运行模式 - 不会实际创建文件")
            return True
        return generator.generate_enhanced_analyzer_workflow(args.site_id)
    
    elif args.enhanced_command == 'crawler':
        logger.info(f"🚀 生成增强版爬虫工作流: {args.site_id}")
        if args.dry_run:
            logger.info("🔍 试运行模式 - 不会实际创建文件")
            return True
        return generator.generate_crawler_workflow(args.site_id)
    
    elif args.enhanced_command == 'all':
        logger.info("🚀 生成所有站点的增强版工作流")
        workflow_types = args.types.split(',')
        success = True
        
        # 直接获取所有站点，避免继承问题
        sites = get_all_sites_direct(args.sites_dir)
        for site_id in sites:
            for workflow_type in workflow_types:
                if workflow_type.strip() == 'analyzer':
                    if not args.dry_run:
                        success &= generator.generate_enhanced_analyzer_workflow(site_id)
                    logger.info(f"✅ 处理站点 {site_id} 的分析工作流")
                elif workflow_type.strip() == 'crawler':
                    if not args.dry_run:
                        success &= generator.generate_crawler_workflow(site_id)
                    logger.info(f"✅ 处理站点 {site_id} 的爬虫工作流")
        
        return success
    
    return False


def run_jsonnet_commands(args, logger):
    """运行标准Jsonnet生成器命令"""
    if JsonnetWorkflowGenerator is None:
        logger.error("❌ Jsonnet生成器不可用，请检查依赖项")
        return False
        
    generator = JsonnetWorkflowGenerator(
        settings_path=args.settings,
        sites_dir=args.sites_dir,
        output_dir=args.output_dir,
        logger=logger
    )
    
    if args.jsonnet_command == 'generate':
        logger.info(f"🚀 生成Jsonnet工作流: {args.template_name} -> {args.output_name}")
        if args.dry_run:
            logger.info("🔍 试运行模式 - 不会实际创建文件")
            return True
        
        ext_vars = {}
        if args.site_id:
            site_config = generator._load_site_config(args.site_id)
            ext_vars = {
                "site_id": args.site_id,
                "site_config": site_config,
                "global_config": generator.global_config
            }
        
        return generator.generate_workflow(args.template_name, args.output_name, ext_vars)
    
    return False


def run_yaml_commands(args, logger):
    """运行传统YAML生成器命令"""
    if WorkflowGenerator is None:
        logger.error("❌ YAML生成器不可用，请检查依赖项")
        return False
        
    generator = WorkflowGenerator(
        settings_path=args.settings,
        sites_dir=args.sites_dir,
        output_dir=args.output_dir,
        logger=logger
    )
    
    if args.yaml_command == 'generate':
        logger.info(f"🚀 生成YAML工作流: {args.site_id} - {args.workflow_type}")
        if args.dry_run:
            logger.info("🔍 试运行模式 - 不会实际创建文件")
            return True
        return generator.generate_workflow(args.site_id, args.workflow_type)
    
    elif args.yaml_command == 'all':
        logger.info("🚀 生成所有YAML工作流")
        if args.dry_run:
            logger.info("🔍 试运行模式 - 不会实际创建文件")
            return True
        return generator.generate_all_workflows()
    
    return False


def run_tools_commands(args, logger):
    """运行工具命令"""
    if EnhancedJsonnetGenerator is None:
        logger.error("❌ 增强版生成器不可用，请检查依赖项")
        return False
        
    generator = EnhancedJsonnetGenerator(
        settings_path=args.settings,
        sites_dir=args.sites_dir,
        output_dir=args.output_dir,
        logger=logger
    )
    
    if args.tools_command == 'list-sites':
        sites = get_all_sites_direct(args.sites_dir)
        logger.info("📋 可用站点列表:")
        for site_id in sites:
            site_config = generator._load_site_config(site_id)
            site_name = site_config.get('site_info', {}).get('name', site_id) if site_config else site_id
            print(f"  • {site_id} - {site_name}")
        return True
    
    elif args.tools_command == 'validate':
        if args.site_id:
            # 验证特定站点
            site_config = generator._load_site_config(args.site_id)
            if site_config:
                logger.info(f"✅ 站点 {args.site_id} 配置有效")
                return True
            else:
                logger.error(f"❌ 站点 {args.site_id} 配置无效")
                return False
        else:
            # 验证所有站点
            sites = get_all_sites_direct(args.sites_dir)
            success = True
            for site_id in sites:
                site_config = generator._load_site_config(site_id)
                if site_config:
                    logger.info(f"✅ 站点 {site_id} 配置有效")
                else:
                    logger.error(f"❌ 站点 {site_id} 配置无效")
                    success = False
            return success
    
    elif args.tools_command == 'clean':
        # 清理生成的工作流文件
        output_dir = Path(args.output_dir) if args.output_dir else Path('.github/workflows')
        if output_dir.exists():
            for file in output_dir.glob('*.yml'):
                if not args.dry_run:
                    file.unlink()
                logger.info(f"🗑️ 删除文件: {file}")
            logger.info("✅ 清理完成")
        return True
    
    return False


def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志记录
    logger = setup_logging(args.verbose)
    
    # 显示启动信息
    logger.info("🔧 增强版工作流生成器启动")
    if args.dry_run:
        logger.info("🔍 运行在试运行模式")
    
    # 执行命令
    success = False
    
    if args.command == 'enhanced':
        success = run_enhanced_commands(args, logger)
    elif args.command == 'jsonnet':
        success = run_jsonnet_commands(args, logger)
    elif args.command == 'yaml':
        success = run_yaml_commands(args, logger)
    elif args.command == 'tools':
        success = run_tools_commands(args, logger)
    else:
        print("❌ 错误: 未指定命令\n")
        parse_args(['--help'])
        return 1
    
    if success:
        logger.info("✅ 命令执行成功")
        return 0
    else:
        logger.error("❌ 命令执行失败")
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