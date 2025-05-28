#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Scraper (us) - 统一命令行工具
提供标准化的命令接口来管理工作流生成和执行

此文件整合了以下功能：
- 工作流生成 (原 generate_workflow.py, generate_workflows*.py)
- 爬虫执行 (原 scraper.py)
- 分析执行 (原 analyzer.py)
- 工作流执行 (原 run_workflow.py)
- 通知发送 (原 notifier.py)

使用方法：
  python scripts/us.py [命令] [选项]

主要命令：
  generate, gen   - 生成工作流配置
  execute, run     - 执行完整工作流
  scrape, crawl    - 仅执行爬虫
  analyze          - 仅执行分析
  notify           - 仅发送通知

示例：
  python scripts/us.py generate --site pm001 --type all
  python scripts/us.py run --site heimao
  python scripts/us.py scrape --site pm001
"""

import os
import sys
import argparse
import logging
import time
import yaml
import json
import importlib
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入工作流组件
from scripts.workflow_generator.engine_factory import WorkflowEngineFactory

# 导入增强版Jsonnet生成器（如果可用）
try:
    from scripts.workflow_generator.enhanced_jsonnet_generator import EnhancedJsonnetGenerator
    ENHANCED_JSONNET_AVAILABLE = True
except ImportError:
    ENHANCED_JSONNET_AVAILABLE = False

# 导入工作流验证器
try:
    from scripts.workflow_generator.validators import WorkflowValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


def setup_logger(verbose=False):
    """设置日志记录器"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logger = logging.getLogger('universal-scraper')
    logger.setLevel(level)
    
    # 清除已有的处理器
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    
    return logger


def handle_generate(args, logger):
    """生成工作流命令处理函数"""
    logger.info(f"开始生成工作流，站点: {args.site or '所有'}, 类型: {args.type}")
    
    # 记录详细参数
    if logger.level == logging.DEBUG:
        logger.debug(f"详细参数: config={args.config}, sites_dir={args.sites_dir}, output_dir={args.output_dir}, enhanced={args.enhanced}")
        if hasattr(args, 'cache') and args.cache:
            logger.debug(f"缓存设置: {args.cache}")
        if hasattr(args, 'timeout') and args.timeout:
            logger.debug(f"超时设置: {args.timeout} 分钟")
        if hasattr(args, 'error_strategy') and args.error_strategy:
            logger.debug(f"错误处理策略: {args.error_strategy}")
    
    # 创建工作流引擎工厂
    factory = WorkflowEngineFactory(
        settings_path=args.config,
        sites_dir=args.sites_dir,
        output_dir=args.output_dir,
        logger=logger
    )
    logger.debug("工作流引擎工厂创建成功")
    
    # 使用增强版引擎还是标准引擎
    if args.enhanced and ENHANCED_JSONNET_AVAILABLE:
        logger.debug("使用增强版 Jsonnet 引擎")
        generator = EnhancedJsonnetGenerator(
            settings_path=args.config,
            sites_dir=args.sites_dir,
            output_dir=args.output_dir,
            logger=logger
        )
    else:
        logger.debug("使用标准 Jsonnet 引擎")
        generator = factory.get_generator('jsonnet', validate_output=True)
    
    # 应用高级配置
    if hasattr(args, 'cache') and args.cache:
        cache_enabled = args.cache == 'enable'
        logger.info(f"缓存设置: {'启用' if cache_enabled else '禁用'}")
        generator.set_cache_enabled(cache_enabled)
    
    if hasattr(args, 'timeout') and args.timeout:
        logger.info(f"超时设置: {args.timeout} 分钟")
        generator.set_timeout(args.timeout)
    
    if hasattr(args, 'error_strategy') and args.error_strategy:
        logger.info(f"错误处理策略: {args.error_strategy}")
        generator.set_error_strategy(args.error_strategy)
    
    # 记录开始时间
    start_time = time.time()
    success = False
    
    # 根据类型和站点参数生成工作流
    if args.type == 'all':
        if args.site:
            logger.info(f"为站点 {args.site} 生成爬虫和分析工作流")
            crawler_success = generator.generate_crawler_workflow(args.site)
            
            if args.enhanced and ENHANCED_JSONNET_AVAILABLE:
                analyzer_success = generator.generate_enhanced_analyzer_workflow(args.site)
            else:
                analyzer_success = generator.generate_analyzer_workflow(args.site)
                
            success = crawler_success and analyzer_success
        else:
            logger.info("生成所有工作流")
            success = generator.generate_all_workflows()
    
    elif args.type == 'common':
        logger.info("生成通用工作流（主调度、仪表盘、代理池）")
        success = generator.generate_common_workflows()
    
    elif args.type == 'crawler':
        if not args.site:
            logger.error("生成爬虫工作流需要指定站点ID")
            return False
        logger.info(f"为站点 {args.site} 生成爬虫工作流")
        success = generator.generate_crawler_workflow(args.site)
    
    elif args.type == 'analyzer':
        if not args.site:
            logger.error("生成分析工作流需要指定站点ID")
            return False
        logger.info(f"为站点 {args.site} 生成分析工作流")
        
        if args.enhanced and ENHANCED_JSONNET_AVAILABLE:
            success = generator.generate_enhanced_analyzer_workflow(args.site)
        else:
            success = generator.generate_analyzer_workflow(args.site)
    
    # 计算耗时
    elapsed_time = time.time() - start_time
    
    if success:
        logger.info(f"✅ 工作流生成成功，耗时: {elapsed_time:.2f}秒")
    else:
        logger.error(f"❌ 工作流生成失败，耗时: {elapsed_time:.2f}秒")
    
    return success


def handle_execute(args, logger):
    """执行工作流命令处理函数"""
    if not args.site:
        logger.error("执行工作流需要指定站点ID")
        return False
    
    logger.info(f"开始执行完整工作流，站点: {args.site}")
    
    # 设置输出目录
    output_dir = args.output_dir
    if not output_dir:
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.join('data', 'daily', today)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 加载配置
        site_config = load_config(args.site, args.config)
        global_config = load_global_config(args.settings)
        
        # 获取站点名称
        site_name = site_config.get('site', {}).get('name', args.site)
        
        # 1. 运行爬虫阶段
        logger.info(f"=== 开始爬虫阶段: {args.site} ===")
        scrape_args = argparse.Namespace(
            site=args.site,
            output_dir=output_dir,
            config=args.config,
            verbose=args.verbose
        )
        success, crawler_result = handle_scrape(scrape_args, logger)
        
        if not success:
            logger.error("爬虫阶段失败，终止工作流")
            return False
        
        # 2. 运行分析阶段
        data_file = crawler_result.get('output_path')
        logger.info(f"爬虫成功，获取了 {crawler_result.get('count', 0)} 条数据")
        logger.info(f"数据已保存到: {data_file}")
        
        # 设置分析输出目录
        analysis_dir = os.path.join('analysis', 'daily', datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(analysis_dir, exist_ok=True)
        
        # 创建分析参数
        analyze_args = argparse.Namespace(
            site=args.site,
            data=data_file,
            output_dir=analysis_dir,
            config=args.config,
            settings=args.settings,
            verbose=args.verbose
        )
        
        logger.info(f"=== 开始分析阶段: {args.site} ===")
        analysis_success, analysis_result = handle_analyze(analyze_args, logger)
        
        # 3. 运行通知阶段（如果分析成功）
        if analysis_success:
            # 获取分析结果文件路径
            analysis_file = os.path.join(analysis_dir, f"{args.site}_analysis.json")
            summary_file = os.path.join(analysis_dir, f"{args.site}_summary.md")
            
            logger.info(f"=== 开始通知阶段: {args.site} ===")
            try:
                notification_result = run_notifier(
                    args.site, 
                    site_name, 
                    data_file, 
                    analysis_file, 
                    summary_file, 
                    global_config
                )
                
                if notification_result and notification_result.get('status') == 'success':
                    logger.info("通知发送成功")
                else:
                    logger.warning(f"通知发送失败: {notification_result.get('message', '未知错误')}")
            except Exception as e:
                logger.warning(f"通知阶段发生错误: {e}")
        
        # 计算总耗时
        elapsed_time = time.time() - start_time
        logger.info(f"=== 工作流完成: {args.site}, 总耗时: {elapsed_time:.2f} 秒 ===")
        
        return analysis_success
    except Exception as e:
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.exception(f"❌ 工作流过程中发生错误: {e}, 耗时: {elapsed_time:.2f}秒")
        return False


def handle_scrape(args, logger):
    """爬虫命令处理函数"""
    if not args.site:
        logger.error("执行爬虫需要指定站点ID")
        return False
    
    logger.info(f"开始执行爬虫，站点: {args.site}")
    
    # 设置输出目录
    output_dir = args.output_dir
    if not output_dir:
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.join('data', 'daily', today)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载配置
    config = load_config(args.site, args.config)
    
    # 记录开始时间
    start_time = time.time()
    
    # 运行爬虫
    result = run_scraper(args.site, config, output_dir)
    
    # 计算耗时
    elapsed_time = time.time() - start_time
    
    if result and result.get('status') == 'success':
        logger.info(f"✅ 爬虫执行成功，获取了 {result.get('count')} 条数据，耗时: {elapsed_time:.2f}秒")
        logger.info(f"📄 数据已保存到: {result.get('output_path')}")
        return True, result
    else:
        logger.error(f"❌ 爬虫执行失败，耗时: {elapsed_time:.2f}秒")
        return False, result


def handle_analyze(args, logger):
    """分析命令处理函数"""
    if not args.site:
        logger.error("执行分析需要指定站点ID")
        return False, {"status": "error", "message": "缺少站点ID"}
    
    if not args.data:
        logger.error("执行分析需要指定数据文件")
        return False, {"status": "error", "message": "缺少数据文件"}
    
    logger.info(f"开始执行分析，站点: {args.site}，数据文件: {args.data}")
    
    # 设置输出目录
    output_dir = args.output_dir
    if not output_dir:
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.join('analysis', 'daily', today)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 加载站点配置
        site_config = load_config(args.site, args.config)
        
        # 记录开始时间
        start_time = time.time()
        
        # 运行分析器
        result = run_analyzer(args.site, args.data, site_config, output_dir)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        if result and result.get('status') == 'success':
            logger.info(f"✅ 分析执行成功，耗时: {elapsed_time:.2f}秒")
            logger.info(f"📄 分析结果已保存到: {result.get('output_path')}")
            return True, result
        else:
            logger.error(f"❌ 分析执行失败，耗时: {elapsed_time:.2f}秒")
            return False, result
    except Exception as e:
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.exception(f"❌ 分析过程中发生错误: {e}, 耗时: {elapsed_time:.2f}秒")
        return False, {"status": "error", "message": str(e)}


def load_config(site_id, config_file=None):
    """加载站点配置文件"""
    if config_file:
        config_path = Path(config_file)
    else:
        config_path = Path('config') / 'sites' / f'{site_id}.yaml'
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def load_global_config(settings_file=None):
    """加载全局配置文件"""
    if settings_file:
        config_path = Path(settings_file)
    else:
        config_path = Path('config') / 'settings.yaml'
    
    if not config_path.exists():
        raise FileNotFoundError(f"全局配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def run_scraper(site_id, config, output_dir=None, **kwargs):
    """根据配置运行爬虫，支持自动透传额外参数"""
    scraping = config.get('scraping', {})
    engine = scraping.get('engine', 'custom')
    
    if engine == 'custom':
        # 获取自定义模块和函数
        module_path = scraping.get('custom_module')
        function_name = scraping.get('custom_function')
        
        if not module_path or not function_name:
            raise ValueError("配置缺少custom_module或custom_function")
        
        try:
            # 导入模块
            module = importlib.import_module(module_path)
            scrape_function = getattr(module, function_name)
            
            # 运行爬虫，自动透传kwargs
            result = scrape_function(config, output_dir, **kwargs)
            
            # 复制结果文件到当前目录（如果需要）
            output_config = config.get('output', {})
            output_filename = output_config.get('filename', f'{site_id}_data.json')
            if output_dir:
                source_path = Path(output_dir) / output_filename
                if source_path.exists():
                    import shutil
                    shutil.copy(source_path, output_filename)
            
            return result
        except ImportError as e:
            raise ImportError(f"无法导入模块: {module_path}") from e
        except AttributeError as e:
            raise AttributeError(f"模块 {module_path} 中没有函数 {function_name}") from e
    else:
        raise ValueError(f"不支持的爬虫引擎: {engine}")


def run_analyzer(site_id, data_file, config, output_dir):
    """运行分析器"""
    # 为PM001站点使用专门的分析器
    if site_id == 'pm001':
        from src.analyzers.pm001_analyzer import analyze_pm001_data
        return analyze_pm001_data(data_file, config, output_dir)
    elif site_id == 'heimao':
        from src.analyzers.heimao_analyzer import analyze_heimao_data
        return analyze_heimao_data(data_file, config, output_dir)
    else:
        # 对于其他站点，尝试使用通用分析器
        try:
            from src.analyzers.generic_analyzer import analyze_data
            return analyze_data(site_id, data_file, config, output_dir)
        except ImportError:
            raise NotImplementedError(f"没有为站点 {site_id} 找到专门的分析器，且通用分析器不可用")


def run_notifier(site_id, site_name, data_file, analysis_file, summary_file, config):
    """运行通知模块"""
    # 使用简单通知器
    try:
        from src.notifiers.simple_notifier import send_notification
        return send_notification(site_name, data_file, analysis_file, summary_file, config)
    except ImportError:
        raise ImportError("通知模块不可用")


def handle_notify(args, logger):
    """通知命令处理函数"""
    if not args.site:
        logger.error("发送通知需要指定站点ID")
        return False
    
    if not args.data or not args.analysis or not args.summary:
        logger.error("发送通知需要指定数据文件、分析结果文件和摘要文件")
        return False
    
    logger.info(f"开始发送通知，站点: {args.site}")
    
    try:
        # 加载站点配置和全局配置
        site_config = load_config(args.site, args.config)
        global_config = load_global_config(args.settings)
        
        # 获取站点名称
        site_name = site_config.get('site', {}).get('name', args.site)
        
        # 记录开始时间
        start_time = time.time()
        
        # 运行通知器
        result = run_notifier(
            args.site,
            site_name,
            args.data,
            args.analysis,
            args.summary,
            global_config
        )
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        if result and result.get('status') == 'success':
            logger.info(f"✅ 通知发送成功，耗时: {elapsed_time:.2f}秒")
            return True
        else:
            logger.error(f"❌ 通知发送失败，耗时: {elapsed_time:.2f}秒")
            return False
    except Exception as e:
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.exception(f"❌ 通知发送过程中发生错误: {e}, 耗时: {elapsed_time:.2f}秒")
        return False


def main():
    """主函数"""
    # 创建主解析器
    parser = argparse.ArgumentParser(
        description='Universal Scraper (us) - 统一命令行工具',
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # 添加全局选项
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志')
    parser.add_argument('-c', '--config', help='指定设置文件路径')
    parser.add_argument('-d', '--sites-dir', help='指定站点配置目录')
    parser.add_argument('-o', '--output-dir', help='指定输出目录')
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # generate命令 - 生成工作流
    generate_parser = subparsers.add_parser('generate', help='生成工作流', aliases=['gen'])
    generate_parser.add_argument('-s', '--site', help='站点ID')
    generate_parser.add_argument('-t', '--type', default='all', 
                               choices=['all', 'common', 'crawler', 'analyzer'], 
                               help='工作流类型 (默认: all)')
    generate_parser.add_argument('-e', '--enhanced', action='store_true', 
                               help='使用增强版Jsonnet引擎')
    # 缓存控制
    generate_parser.add_argument('--cache', choices=['enable', 'disable'], 
                               help='启用或禁用依赖项缓存')
    # 超时设置
    generate_parser.add_argument('--timeout', type=int, 
                               help='设置工作流超时时间(分钟)')
    # 错误处理策略
    generate_parser.add_argument('--error-strategy', choices=['strict', 'tolerant'], 
                               help='错误处理策略: strict(严格) 或 tolerant(宽松)')
    
    # execute命令 - 运行完整工作流
    execute_parser = subparsers.add_parser('execute', help='运行完整工作流', aliases=['run'])
    execute_parser.add_argument('-s', '--site', required=True, help='站点ID')
    
    # scrape命令 - 只运行爬虫
    scrape_parser = subparsers.add_parser('scrape', help='只运行爬虫', aliases=['crawl'])
    scrape_parser.add_argument('-s', '--site', required=True, help='站点ID')
    
    # analyze命令 - 只运行分析
    analyze_parser = subparsers.add_parser('analyze', help='只运行分析')
    analyze_parser.add_argument('-s', '--site', required=True, help='站点ID')
    analyze_parser.add_argument('-d', '--data', required=True, help='数据文件路径')
    
    # notify命令 - 只发送通知
    notify_parser = subparsers.add_parser('notify', help='只发送通知')
    notify_parser.add_argument('-s', '--site', required=True, help='站点ID')
    notify_parser.add_argument('-d', '--data', required=True, help='数据文件路径')
    notify_parser.add_argument('-a', '--analysis', required=True, help='分析结果文件路径')
    notify_parser.add_argument('-m', '--summary', required=True, help='摘要文件路径')
    
    # 解析参数
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logger(args.verbose)
    
    # 如果没有提供命令，显示帮助
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        # 执行相应的命令
        if args.command in ['generate', 'gen']:
            success = handle_generate(args, logger)
        elif args.command in ['execute', 'run']:
            success = handle_execute(args, logger)
        elif args.command in ['scrape', 'crawl']:
            success, _ = handle_scrape(args, logger)
        elif args.command == 'analyze':
            success, _ = handle_analyze(args, logger)
        elif args.command == 'notify':
            success = handle_notify(args, logger)
        else:
            parser.print_help()
            return 0
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        logger.info("\n操作已取消")
        return 1
    except Exception as e:
        logger.exception(f"执行过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
