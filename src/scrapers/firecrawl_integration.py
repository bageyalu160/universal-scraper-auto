#!/usr/bin/env python3
"""
Firecrawl集成模块
集成Firecrawl爬虫和Extract功能到Universal Scraper框架
"""

import os
import sys
import json
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field

# 导入基础类和工具
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_site_config
from utils.path_helper import ensure_dir, get_data_dir, get_analysis_dir

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('firecrawl_integration')

try:
    from firecrawl import FirecrawlApp, ScrapeOptions
    FIRECRAWL_AVAILABLE = True
except ImportError:
    logger.warning("Firecrawl SDK未安装，将使用模拟模式")
    FIRECRAWL_AVAILABLE = False

class FirecrawlScraper:
    """Firecrawl爬虫集成实现"""
    
    def __init__(self, site_id: str, config_path: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化Firecrawl爬虫
        
        Args:
            site_id: 站点ID
            config_path: 配置文件路径，默认为None（使用默认路径）
            api_key: Firecrawl API密钥，默认为None（使用环境变量）
        """
        self.site_id = site_id
        self.config = load_site_config(site_id, config_path)
        self.site_name = self.config['site']['name']
        self.base_url = self.config['site']['base_url']
        self.output_dir = get_data_dir(site_id)
        self.api_key = api_key or os.environ.get('FIRECRAWL_API_KEY')
        
        # 初始化Firecrawl客户端
        if FIRECRAWL_AVAILABLE and self.api_key:
            self.app = FirecrawlApp(api_key=self.api_key)
            logger.info(f"初始化Firecrawl客户端成功")
        else:
            self.app = None
            logger.warning("Firecrawl客户端初始化失败，将使用模拟模式")
        
        logger.info(f"初始化Firecrawl爬虫: {self.site_name}")
    
    def prepare_crawl_config(self) -> Dict[str, Any]:
        """
        准备Firecrawl爬虫配置
        
        Returns:
            Dict: Firecrawl配置字典
        """
        # 转换Universal Scraper配置为Firecrawl配置格式
        targets = self.config['scraping']['targets']
        urls_to_crawl = []
        
        for target in targets:
            if 'url' in target:
                urls_to_crawl.append(target['url'])
            else:
                # 使用URL格式模板构建URL
                target_id = target['id']
                url_format = self.config['scraping']['url_format']['target_page']
                url = url_format.format(base_url=self.base_url, target_id=target_id, page_num=1)
                urls_to_crawl.append(url)
        
        # 获取Firecrawl特定选项
        firecrawl_options = self.config.get('scraping', {}).get('firecrawl_options', {})
        
        # 构造基础抓取选项
        scrape_options = {
            "formats": firecrawl_options.get('formats', ["markdown"]),
            "onlyMainContent": firecrawl_options.get('onlyMainContent', True)
        }
        
        # 构造抓取配置
        crawl_config = {
            "urls": urls_to_crawl,  # 要爬取的URL列表
            "maxDepth": self.config['scraping'].get('pagination', {}).get('pages_per_target', 3),
            "limit": self.config['scraping'].get('pagination', {}).get('max_items', 100),
            "allowExternalLinks": firecrawl_options.get('allowExternalLinks', False),
            "scrapeOptions": scrape_options
        }
        
        # 添加关键词过滤
        if 'filters' in self.config and 'keywords' in self.config['filters']:
            if self.config['filters']['keywords'].get('include'):
                crawl_config["includePaths"] = self.config['filters']['keywords']['include']
            if self.config['filters']['keywords'].get('exclude'):
                crawl_config["excludePaths"] = self.config['filters']['keywords']['exclude']
        
        return crawl_config
    
    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        抓取单个URL
        
        Args:
            url: 要抓取的URL
            
        Returns:
            Dict: 抓取结果
        """
        logger.info(f"抓取URL: {url}")
        
        if self.app:
            # 获取Firecrawl特定选项
            firecrawl_options = self.config.get('scraping', {}).get('firecrawl_options', {})
            
            # 构造抓取选项
            formats = firecrawl_options.get('formats', ["markdown"])
            only_main_content = firecrawl_options.get('onlyMainContent', True)
            
            # 获取页面交互操作（如果有）
            actions = firecrawl_options.get('actions', [])
            
            # 检查是否需要使用JsonConfig进行LLM提取
            use_llm_extraction = 'extract_prompt' in self.config.get('scraping', {}) and 'json' in formats
            json_options = None
            
            if use_llm_extraction:
                try:
                    from firecrawl import JsonConfig
                    # 构建提取架构
                    schema = self._build_extract_schema()
                    # 获取提示词
                    prompt = self.config.get('scraping', {}).get('extract_prompt')
                    
                    # 创建JsonConfig对象
                    json_options = JsonConfig(
                        extractionSchema=schema if 'properties' in schema else None,
                        prompt=prompt,
                        mode="llm-extraction",
                        pageOptions={"onlyMainContent": only_main_content}
                    )
                    logger.info("启用LLM提取功能")
                except (ImportError, Exception) as e:
                    logger.error(f"创建JsonConfig失败: {str(e)}")
                    json_options = None
            
            try:
                # 使用Firecrawl SDK抓取URL
                params = {
                    "url": url,
                    "formats": formats,
                    "only_main_content": only_main_content
                }
                
                # 添加操作参数（如果有）
                if actions:
                    params["actions"] = actions
                    logger.info(f"使用页面交互操作: {len(actions)}个操作")
                
                # 添加JSON选项（如果有）
                if json_options:
                    params["json_options"] = json_options
                
                # 调用SDK
                result = self.app.scrape_url(**params)
                
                return result.to_dict() if hasattr(result, 'to_dict') else result
            except Exception as e:
                logger.error(f"使用Firecrawl抓取URL失败: {str(e)}")
                return {"error": str(e), "url": url}
        else:
            # 模拟抓取结果
            logger.info("使用模拟模式抓取URL")
            result = {
                "success": True,
                "data": {
                    "url": url,
                    "markdown": f"# 模拟抓取结果\n\n来自 {url} 的内容...",
                    "metadata": {
                        "title": f"页面标题 - {url}",
                        "description": "这是一个模拟的页面描述",
                        "sourceURL": url
                    }
                }
            }
            
            # 如果配置了Actions，在模拟结果中添加actions字段
            firecrawl_options = self.config.get('scraping', {}).get('firecrawl_options', {})
            if 'actions' in firecrawl_options:
                result["data"]["actions"] = {
                    "screenshots": ["https://example.com/mock-screenshot.png"],
                    "scrapes": [{"url": url, "html": "<html><body>模拟内容</body></html>"}]
                }
            
            return result
    
    def start_crawl(self) -> Dict[str, Any]:
        """
        启动Firecrawl爬虫任务
        
        Returns:
            Dict: 爬取结果
        """
        logger.info(f"准备使用Firecrawl爬取: {self.site_name}")
        
        crawl_config = self.prepare_crawl_config()
        logger.info(f"Firecrawl配置: {json.dumps(crawl_config, indent=2)}")
        
        if self.app:
            try:
                # 使用Firecrawl SDK启动爬取任务
                urls = crawl_config.pop('urls')
                
                # 处理ScrapeOptions
                if 'scrapeOptions' in crawl_config:
                    try:
                        from firecrawl import ScrapeOptions
                        
                        # 获取原始选项
                        opts = crawl_config.pop('scrapeOptions')
                        
                        # 创建ScrapeOptions对象
                        scrape_options = ScrapeOptions(
                            formats=opts.get('formats', ["markdown"]),
                            only_main_content=opts.get('onlyMainContent', True)
                        )
                        
                        # 添加到配置中
                        crawl_config['scrape_options'] = scrape_options
                        logger.info(f"创建ScrapeOptions成功: {scrape_options}")
                    except (ImportError, Exception) as e:
                        logger.warning(f"创建ScrapeOptions失败，使用原始配置: {str(e)}")
                        # 保留原始配置，但使用蛇形命名法
                        if 'scrapeOptions' in crawl_config:
                            crawl_config['scrape_options'] = crawl_config.pop('scrapeOptions')
                
                # 转换其他选项为蛇形命名法
                if 'maxDepth' in crawl_config:
                    crawl_config['max_depth'] = crawl_config.pop('maxDepth')
                if 'allowExternalLinks' in crawl_config:
                    crawl_config['allow_external_links'] = crawl_config.pop('allowExternalLinks')
                if 'includePaths' in crawl_config:
                    crawl_config['include_paths'] = crawl_config.pop('includePaths')
                if 'excludePaths' in crawl_config:
                    crawl_config['exclude_paths'] = crawl_config.pop('excludePaths')
                
                # 调用SDK
                crawl_result = self.app.crawl_url(
                    url=urls[0] if len(urls) == 1 else self.base_url,
                    **crawl_config
                )
                
                # 处理结果
                if hasattr(crawl_result, 'to_dict'):
                    results = crawl_result.to_dict()
                else:
                    results = crawl_result
                
                # 保存爬取结果
                output_file = os.path.join(self.output_dir, f"{self.site_id}_crawl.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                logger.info(f"爬取完成，结果已保存到: {output_file}")
                return results
                
            except Exception as e:
                logger.error(f"使用Firecrawl爬取失败: {str(e)}")
                return {"error": str(e)}
        else:
            # 模拟爬取结果
            logger.info("使用模拟模式爬取")
            results = {
                "success": True,
                "status": "completed",
                "site": self.site_name,
                "timestamp": datetime.now().isoformat(),
                "total": 5,
                "completed": 5,
                "creditsUsed": 5,
                "data": [
                    {
                        "markdown": "# 示例标题1\n\n这是一个示例内容...",
                        "metadata": {
                            "title": "示例页面1",
                            "description": "这是一个示例页面的描述",
                            "sourceURL": f"{self.base_url}page1"
                        }
                    },
                    {
                        "markdown": "# 示例标题2\n\n这是另一个示例内容...",
                        "metadata": {
                            "title": "示例页面2",
                            "description": "这是另一个示例页面的描述",
                            "sourceURL": f"{self.base_url}page2"
                        }
                    }
                ]
            }
            
            # 保存结果
            output_file = os.path.join(self.output_dir, f"{self.site_id}_crawl.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模拟爬取完成，结果已保存到: {output_file}")
            return results
    
    def extract_structured_data(self, urls: Optional[List[str]] = None, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """
        使用Firecrawl的Extract功能提取结构化数据
        
        Args:
            urls: 要提取的URL列表，如果为None则使用配置中的目标URL
            schema: 提取架构，如果为None则根据配置生成
            
        Returns:
            Dict: 提取结果
        """
        logger.info("使用Firecrawl的Extract功能提取结构化数据...")
        
        # 如果未提供URLs，则使用配置中的目标
        if urls is None:
            targets = self.config['scraping']['targets']
            urls = []
            for target in targets:
                if 'url' in target:
                    urls.append(target['url'])
                else:
                    # 使用URL格式模板构建URL
                    target_id = target['id']
                    url_format = self.config['scraping']['url_format']['target_page']
                    url = url_format.format(base_url=self.base_url, target_id=target_id, page_num=1)
                    urls.append(url)
        
        # 从配置中获取提示词
        prompt = self.config.get('scraping', {}).get('extract_prompt', "从这些网页中提取关键信息")
        
        # 获取Firecrawl特定选项
        firecrawl_options = self.config.get('scraping', {}).get('firecrawl_options', {})
        
        # 确定是否启用Web搜索
        enable_web_search = firecrawl_options.get('enableWebSearch', False)
        
        # 判断是否使用架构
        use_schema = False
        if schema is None:
            # 检查配置中是否有解析字段定义
            if 'parsing' in self.config and 'field_selectors' in self.config['parsing']:
                schema = self._build_extract_schema()
                use_schema = True
            else:
                # 使用无架构提取模式
                logger.info("使用无架构提取模式，仅依赖提示词")
                schema = None
        else:
            use_schema = True
        
        if self.app:
            try:
                # 使用Firecrawl SDK的extract功能
                params = {
                    "urls": urls, 
                    "prompt": prompt,
                    "enable_web_search": enable_web_search
                }
                
                # 如果有架构，添加到参数中
                if use_schema and schema:
                    params["schema"] = schema
                    logger.info("使用架构提取")
                else:
                    logger.info("使用无架构提取")
                
                # 调用SDK
                extract_result = self.app.extract(**params)
                
                # 处理结果
                if hasattr(extract_result, 'to_dict'):
                    results = extract_result.to_dict()
                else:
                    results = extract_result
                
                # 保存提取结果
                output_file = os.path.join(self.output_dir, f"{self.site_id}_structured.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                logger.info(f"数据提取完成，结果已保存到: {output_file}")
                return results
                
            except Exception as e:
                logger.error(f"使用Firecrawl提取数据失败: {str(e)}")
                return {"error": str(e)}
        else:
            # 模拟提取结果
            logger.info("使用模拟模式提取结构化数据")
            
            # 构建模拟输出
            mock_data = {}
            
            if use_schema and schema and 'properties' in schema:
                # 使用架构构建模拟数据
                for field_name, field_info in schema['properties'].items():
                    field_type = field_info.get('type', 'string')
                    
                    if field_type == 'string':
                        mock_data[field_name] = f"模拟{field_name}数据"
                    elif field_type == 'number':
                        mock_data[field_name] = 42
                    elif field_type == 'boolean':
                        mock_data[field_name] = True
                    elif field_type == 'array':
                        mock_data[field_name] = ["项目1", "项目2"]
                    elif field_type == 'object':
                        mock_data[field_name] = {"key": "value"}
            else:
                # 无架构模式，根据提示词构建模拟数据
                if "API" in prompt or "api" in prompt:
                    mock_data = {
                        "api_name": "Extract API",
                        "api_description": "从网页中提取结构化数据",
                        "parameters": ["urls", "prompt", "schema", "enableWebSearch"],
                        "example_code": "app.extract(urls=['https://example.com'], prompt='提取信息')"
                    }
                elif "公司" in prompt or "company" in prompt:
                    mock_data = {
                        "company_mission": "提供高效的网页数据抽取服务",
                        "supports_sso": True,
                        "is_open_source": True
                    }
                else:
                    mock_data = {
                        "title": "示例标题",
                        "content_summary": "这是AI生成的内容摘要...",
                        "topics": ["主题1", "主题2"],
                        "sentiment": "positive"
                    }
            
            # 假设的提取结果
            structured_data = {
                "success": True,
                "data": mock_data
            }
            
            # 保存结构化数据
            output_file = os.path.join(self.output_dir, f"{self.site_id}_structured.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模拟结构化数据提取完成，已保存到: {output_file}")
            return structured_data
    
    def _build_extract_schema(self) -> Dict[str, Any]:
        """
        根据配置构建Extract的架构
        
        Returns:
            Dict: Extract架构
        """
        # 默认的基础架构
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # 如果配置中有解析字段定义，用它构建架构
        if 'parsing' in self.config and 'field_selectors' in self.config['parsing']:
            fields = self.config['parsing']['field_selectors']
            properties = {}
            
            for field_name, field_config in fields.items():
                # 根据字段配置确定类型
                field_type = "string"  # 默认类型
                
                # 如果字段名称暗示类型，可以做相应调整
                if 'date' in field_name.lower():
                    field_type = "string"  # 日期类型仍然用字符串表示
                elif 'count' in field_name.lower() or 'number' in field_name.lower():
                    field_type = "number"
                elif field_name.lower() in ['is_active', 'published', 'featured']:
                    field_type = "boolean"
                
                # 添加字段定义
                properties[field_name] = {"type": field_type}
                
                # 添加字段描述（如果有）
                if isinstance(field_config, dict) and 'description' in field_config:
                    properties[field_name]["description"] = field_config['description']
                
                # 添加到required列表
                schema["required"].append(field_name)
            
            schema["properties"] = properties
        else:
            # 如果没有字段定义，使用默认通用架构
            schema["properties"] = {
                "title": {"type": "string", "description": "内容标题"},
                "content_summary": {"type": "string", "description": "内容摘要"},
                "topics": {"type": "array", "items": {"type": "string"}, "description": "相关主题"},
                "publish_date": {"type": "string", "description": "发布日期"},
                "sentiment": {"type": "string", "description": "内容情感倾向"}
            }
            schema["required"] = ["title", "content_summary"]
        
        return schema
    
    def map_website(self) -> Dict[str, Any]:
        """
        使用Firecrawl的map功能映射网站结构
        
        Returns:
            Dict: 网站地图结果
        """
        logger.info(f"使用Firecrawl映射网站: {self.site_name}")
        
        if self.app:
            try:
                # 使用Firecrawl SDK映射网站
                map_result = self.app.map_url(
                    url=self.base_url,
                    limit=self.config['scraping'].get('pagination', {}).get('max_items', 100),
                    include_subdomains=self.config.get('scraping', {}).get('firecrawl_options', {}).get('includeSubdomains', False)
                )
                
                # 处理结果
                if hasattr(map_result, 'to_dict'):
                    results = map_result.to_dict()
                else:
                    results = map_result
                
                # 保存映射结果
                output_file = os.path.join(self.output_dir, f"{self.site_id}_sitemap.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                logger.info(f"网站映射完成，结果已保存到: {output_file}")
                return results
                
            except Exception as e:
                logger.error(f"使用Firecrawl映射网站失败: {str(e)}")
                return {"error": str(e)}
        else:
            # 模拟映射结果
            logger.info("使用模拟模式映射网站")
            results = {
                "urls": [
                    {"url": f"{self.base_url}page1", "title": "页面1"},
                    {"url": f"{self.base_url}page2", "title": "页面2"},
                    {"url": f"{self.base_url}page3", "title": "页面3"},
                ]
            }
            
            # 保存结果
            output_file = os.path.join(self.output_dir, f"{self.site_id}_sitemap.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模拟网站映射完成，结果已保存到: {output_file}")
            return results

def main():
    """命令行入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Firecrawl集成爬虫')
    parser.add_argument('--site', required=True, help='站点ID')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--api-key', help='Firecrawl API密钥')
    
    # 功能选择参数
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--crawl', action='store_true', help='爬取网站')
    group.add_argument('--extract', action='store_true', help='提取结构化数据')
    group.add_argument('--map', action='store_true', help='映射网站结构')
    group.add_argument('--scrape', help='抓取单个URL', metavar='URL')
    group.add_argument('--all', action='store_true', help='执行所有功能：爬取、提取和映射')
    
    args = parser.parse_args()
    
    try:
        # 初始化Firecrawl爬虫
        scraper = FirecrawlScraper(args.site, args.config, args.api_key)
        
        # 根据参数执行相应功能
        if args.crawl or args.all:
            logger.info("执行网站爬取...")
            results = scraper.start_crawl()
            logger.info(f"爬取结果: {len(results.get('data', [])) if isinstance(results, dict) and 'data' in results else '未知'} 条数据")
        
        if args.extract or args.all:
            logger.info("执行结构化数据提取...")
            extract_results = scraper.extract_structured_data()
            logger.info(f"提取成功: {'success' in extract_results and extract_results['success']}")
        
        if args.map or args.all:
            logger.info("执行网站结构映射...")
            map_results = scraper.map_website()
            logger.info(f"映射结果: {len(map_results.get('urls', [])) if isinstance(map_results, dict) and 'urls' in map_results else '未知'} 个URL")
        
        if args.scrape:
            logger.info(f"抓取URL: {args.scrape}")
            scrape_results = scraper.scrape_url(args.scrape)
            logger.info(f"抓取成功: {'success' in scrape_results and scrape_results['success']}")
            
        logger.info("任务完成")
        return 0
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 