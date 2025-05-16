#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析器脚本 - 处理爬虫数据并使用AI模型进行分析
"""

import os
import sys
import json
import yaml
import argparse
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# 尝试导入不同的AI提供商模块
try:
    import google.generativeai as genai  # Gemini API
except ImportError:
    genai = None

try:
    import openai  # OpenAI API
except ImportError:
    openai = None

try:
    from langchain_openai import ChatOpenAI  # LangChain支持
    from langchain.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ai_analyzer')

class AIAnalyzer:
    """AI分析器类，处理爬虫数据并使用AI进行分析"""
    
    def __init__(self, file_path, site_id, output_path=None, settings_path=None):
        """
        初始化AI分析器
        
        Args:
            file_path (str): 爬虫数据文件路径
            site_id (str): 网站ID
            output_path (str, optional): 输出文件路径
            settings_path (str, optional): 设置文件路径
        """
        self.file_path = file_path
        self.site_id = site_id
        self.output_path = output_path
        
        # 设置路径
        self.base_dir = Path(__file__).parent.parent
        self.settings_path = settings_path or self.base_dir / "config" / "settings.yaml"
        self.prompt_dir = self.base_dir / "config" / "analysis" / "prompts"
        
        # 加载设置
        self.settings = self._load_settings()
        
        # 设置提供商的API凭证
        self._setup_ai_provider()
        
        # 加载提示词
        self.prompt = self._load_prompt()
        
        # 数据
        self.data = None
        self.analysis_result = None
    
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
    
    def _setup_ai_provider(self):
        """根据设置设置AI提供商"""
        provider = self.settings.get('ai_analysis', {}).get('provider', 'gemini')
        api_key = os.environ.get(self.settings.get('ai_analysis', {}).get('api_key_env', 'AI_API_KEY'))
        
        if not api_key:
            logger.error("未找到AI API密钥，请设置环境变量")
            raise ValueError("未找到AI API密钥")
        
        if provider == 'gemini':
            if genai is None:
                logger.error("未安装google-generativeai库，无法使用Gemini")
                raise ImportError("请安装google-generativeai: pip install google-generativeai")
            
            genai.configure(api_key=api_key)
            self.ai_client = genai
            self.ai_provider = 'gemini'
            logger.info("成功配置Gemini AI提供商")
            
        elif provider == 'openai':
            if openai is None:
                logger.error("未安装openai库，无法使用OpenAI")
                raise ImportError("请安装openai: pip install openai")
            
            openai.api_key = api_key
            self.ai_client = openai
            self.ai_provider = 'openai'
            logger.info("成功配置OpenAI提供商")
            
        else:
            logger.error(f"不支持的AI提供商: {provider}")
            raise ValueError(f"不支持的AI提供商: {provider}")
    
    def _load_prompt(self):
        """加载提示词模板"""
        # 首先尝试加载站点特定的提示词
        site_prompt_path = self.prompt_dir / f"{self.site_id}_prompt.txt"
        
        # 如果站点特定提示词不存在，则加载通用提示词
        if not site_prompt_path.exists():
            site_prompt_path = self.prompt_dir / "general_prompt.txt"
        
        # 如果还是不存在，则使用默认提示词
        if not site_prompt_path.exists():
            logger.warning("未找到提示词文件，使用默认提示词")
            return """你是一个专业的数据分析助手。
请分析以下数据并提取关键信息。
请以TSV格式输出，包含以下字段：类别、主题、时间信息、价格、数量、特征
"""
        
        try:
            with open(site_prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
            logger.info(f"成功加载提示词文件: {site_prompt_path}")
            return prompt
        except Exception as e:
            logger.error(f"加载提示词文件失败: {e}")
            return """你是一个专业的数据分析助手。
请分析以下数据并提取关键信息。
请以TSV格式输出，包含以下字段：类别、主题、时间信息、价格、数量、特征
"""
    
    def load_data(self):
        """加载爬虫数据"""
        try:
            # 获取文件扩展名
            file_ext = self.file_path.split('.')[-1].lower()
            
            if file_ext == 'json':
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            elif file_ext == 'csv':
                self.data = pd.read_csv(self.file_path).to_dict('records')
            elif file_ext == 'tsv':
                self.data = pd.read_csv(self.file_path, sep='\t').to_dict('records')
            else:
                logger.error(f"不支持的文件格式: {file_ext}")
                raise ValueError(f"不支持的文件格式: {file_ext}")
                
            logger.info(f"成功加载数据文件: {self.file_path}, 共{len(self.data)}条记录")
            return True
        except Exception as e:
            logger.error(f"加载数据文件失败: {e}")
            return False
    
    def prepare_analysis_content(self):
        """准备分析内容"""
        # 如果数据是列表且不为空
        if isinstance(self.data, list) and self.data:
            # 获取限制条数
            max_records = self.settings.get('ai_analysis', {}).get('max_records', 50)
            
            # 限制分析的记录数
            analysis_data = self.data[:max_records]
            
            # 获取数据字段，用于提示词
            data_fields = list(analysis_data[0].keys())
            
            # 将数据转换为字符串
            data_str = json.dumps(analysis_data, ensure_ascii=False, indent=2)
            
            # 组合内容
            content = f"""
数据文件: {os.path.basename(self.file_path)}
网站ID: {self.site_id}
数据时间: {datetime.now().strftime('%Y-%m-%d')}
数据字段: {', '.join(data_fields)}
记录数量: {len(analysis_data)}

数据内容:
{data_str}
"""
            return content
        else:
            logger.error("数据无效或为空")
            return None
    
    def analyze_with_gemini(self, content):
        """使用Gemini API进行分析"""
        try:
            model_name = self.settings.get('ai_analysis', {}).get('gemini_model', 'gemini-pro')
            temperature = self.settings.get('ai_analysis', {}).get('temperature', 0.2)
            
            # 配置模型
            model = self.ai_client.GenerativeModel(
                model_name=model_name,
                generation_config={
                    "temperature": temperature,
                    "top_p": 0.95,
                    "top_k": 0,
                    "max_output_tokens": 8192,
                }
            )
            
            # 发送请求
            response = model.generate_content(
                [self.prompt, content]
            )
            
            # 返回结果
            return response.text
        except Exception as e:
            logger.error(f"Gemini分析失败: {e}")
            return None
    
    def analyze_with_openai(self, content):
        """使用OpenAI API进行分析"""
        try:
            model_name = self.settings.get('ai_analysis', {}).get('openai_model', 'gpt-3.5-turbo')
            temperature = self.settings.get('ai_analysis', {}).get('temperature', 0.2)
            
            # 使用LangChain（如果可用）
            if LANGCHAIN_AVAILABLE:
                # 创建ChatOpenAI实例
                llm = ChatOpenAI(model_name=model_name, temperature=temperature)
                
                # 创建提示词模板
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", self.prompt),
                    ("user", content)
                ])
                
                # 创建链
                chain = prompt_template | llm
                
                # 运行链
                response = chain.invoke({})
                
                # 返回结果
                return response.content
            else:
                # 使用OpenAI API直接调用
                response = self.ai_client.ChatCompletion.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": self.prompt},
                        {"role": "user", "content": content}
                    ],
                    temperature=temperature,
                    max_tokens=4096
                )
                
                # 返回结果
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI分析失败: {e}")
            return None
    
    def analyze(self):
        """使用AI分析数据"""
        # 首先加载数据
        if not self.data and not self.load_data():
            logger.error("无法加载数据，分析终止")
            return False
        
        # 准备分析内容
        content = self.prepare_analysis_content()
        if not content:
            logger.error("准备分析内容失败，分析终止")
            return False
        
        # 根据提供商进行分析
        logger.info(f"开始使用{self.ai_provider.upper()}分析数据...")
        
        if self.ai_provider == 'gemini':
            self.analysis_result = self.analyze_with_gemini(content)
        elif self.ai_provider == 'openai':
            self.analysis_result = self.analyze_with_openai(content)
        else:
            logger.error(f"不支持的AI提供商: {self.ai_provider}")
            return False
        
        # 检查分析结果
        if not self.analysis_result:
            logger.error("分析失败，未获得结果")
            return False
        
        logger.info(f"分析完成，获得结果（长度：{len(self.analysis_result)}字符）")
        return True
    
    def save_result(self):
        """保存分析结果"""
        if not self.analysis_result:
            logger.error("没有分析结果可保存")
            return False
        
        # 如果未指定输出路径，则使用默认路径
        if not self.output_path:
            output_dir = self.settings.get('analysis_dir', 'analysis')
            output_file = f"analysis_result.{self.settings.get('ai_analysis', {}).get('output_format', 'tsv')}"
            self.output_path = os.path.join(output_dir, output_file)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
        
        try:
            # 保存结果
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(self.analysis_result)
            
            logger.info(f"成功保存分析结果到: {self.output_path}")
            return True
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI分析器 - 分析爬虫数据')
    parser.add_argument('--file', '-f', required=True, help='爬虫数据文件路径')
    parser.add_argument('--site', '-s', required=True, help='网站ID')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--settings', help='设置文件路径')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 创建分析器实例
        analyzer = AIAnalyzer(
            file_path=args.file,
            site_id=args.site,
            output_path=args.output,
            settings_path=args.settings
        )
        
        # 分析数据
        if analyzer.analyze():
            # 保存结果
            if analyzer.save_result():
                logger.info("分析任务完成")
                return 0
            else:
                logger.error("保存分析结果失败")
                return 1
        else:
            logger.error("分析数据失败")
            return 1
    except Exception as e:
        logger.exception(f"分析过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 