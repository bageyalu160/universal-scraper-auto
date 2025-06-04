#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置模型定义
使用 Pydantic 进行配置验证和类型转换
"""

import os
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml


class ViewportConfig(BaseModel):
    """浏览器视口配置"""
    width: int = 1280
    height: int = 720


class SiteConfig(BaseModel):
    """站点配置"""
    id: str
    name: str
    base_url: str


class BrowserConfig(BaseModel):
    """浏览器配置"""
    type: str = "chromium"  # chromium, firefox, webkit
    headless: bool = False
    viewport: ViewportConfig = Field(default_factory=ViewportConfig)
    user_agent: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    color_scheme: Optional[str] = None  # light, dark, no-preference
    stealth: bool = True
    launch_args: List[str] = Field(default_factory=list)


class ProxyRotationConfig(BaseModel):
    """代理轮换配置"""
    enable: bool = False
    interval: int = 10  # 分钟


class ProxyConfig(BaseModel):
    """代理配置"""
    enable: bool = False
    type: str = "http"  # http, socks5
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    rotation: ProxyRotationConfig = Field(default_factory=ProxyRotationConfig)

    @field_validator('host')
    def validate_host_if_enabled(cls, v, info):
        if info.data.get('enable', False) and not v:
            raise ValueError('代理启用时必须提供主机地址')
        return v

    @field_validator('port')
    def validate_port_if_enabled(cls, v, info):
        if info.data.get('enable', False) and not v:
            raise ValueError('代理启用时必须提供端口')
        return v


class CaptchaConfig(BaseModel):
    """验证码配置"""
    enable: bool = False
    provider: str = "2captcha"  # 2captcha, anticaptcha
    api_key: Optional[str] = None
    timeout: int = 120  # 秒
    manual_fallback: bool = True

    @field_validator('api_key')
    def validate_api_key_if_enabled(cls, v, info):
        if info.data.get('enable', False) and not v:
            raise ValueError('验证码处理启用时必须提供API密钥')
        return v


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    file: Optional[str] = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class DelayConfig(BaseModel):
    """延迟配置"""
    min: float = 1.0
    max: float = 3.0


class RetryConfig(BaseModel):
    """重试配置"""
    max_retries: int = 3
    backoff_factor: float = 2.0


class NetworkDelayConfig(BaseModel):
    """网络延迟配置"""
    page_delay: DelayConfig = Field(default_factory=DelayConfig)
    category_delay: DelayConfig = Field(default_factory=DelayConfig)


class NetworkConfig(BaseModel):
    """网络配置"""
    timeout: int = 30
    retry: RetryConfig = Field(default_factory=RetryConfig)
    delay: NetworkDelayConfig = Field(default_factory=NetworkDelayConfig)


class SubcategoryConfig(BaseModel):
    """子分类配置"""
    id: str
    name: str
    depth: int = 1


class CategoryConfig(BaseModel):
    """分类配置"""
    id: str
    name: str
    subcategories: List[SubcategoryConfig] = Field(default_factory=list)


class ProductListConfig(BaseModel):
    """商品列表配置"""
    url_format: str
    items_per_page: int = 30
    max_pages: int = 3


class ProductDetailConfig(BaseModel):
    """商品详情配置"""
    max_products: int = 0


class InteractionConfig(BaseModel):
    """交互操作配置"""
    type: str  # wait, click, scroll, fill, etc.
    selector: Optional[str] = None
    duration: Optional[int] = None  # 毫秒
    wait_after: Optional[int] = None  # 毫秒
    value: Optional[str] = None  # 填充值


class FieldSelectorConfig(BaseModel):
    """字段选择器配置"""
    selector: str
    attribute: str = "text"  # text, html, href, etc.
    regex: Optional[str] = None
    transform: Optional[str] = None  # strip, numeric, etc.


class CleaningRuleConfig(BaseModel):
    """数据清洗规则配置"""
    remove: Optional[str] = None
    type: Optional[str] = None  # numeric, integer, boolean, percentage
    multiplier: Optional[float] = None


class ValidationRangeConfig(BaseModel):
    """验证范围配置"""
    min: Optional[float] = None
    max: Optional[float] = None


class ValidationConfig(BaseModel):
    """数据验证配置"""
    required_fields: List[str] = Field(default_factory=list)
    # 允许动态字段，如 price_range
    model_config = {
        "extra": "allow"
    }


class ParsingConfig(BaseModel):
    """解析配置"""
    product_list_selector: str
    list_field_selectors: Dict[str, FieldSelectorConfig]
    cleaning: Dict[str, CleaningRuleConfig] = Field(default_factory=dict)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)


class OutputConfig(BaseModel):
    """输出配置"""
    format: str = "json"  # json, csv, tsv
    directory: str = "data"
    filename_pattern: str = "{site_id}_{timestamp}.{ext}"


class ScrapingConfig(BaseModel):
    """爬取配置"""
    categories: List[CategoryConfig] = Field(default_factory=list)
    product_list: ProductListConfig
    product_detail: ProductDetailConfig = Field(default_factory=ProductDetailConfig)
    interactions: List[InteractionConfig] = Field(default_factory=list)


class SiteConfigRoot(BaseModel):
    """站点配置根"""
    site: SiteConfig
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    captcha: CaptchaConfig = Field(default_factory=CaptchaConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    scraping: ScrapingConfig
    parsing: ParsingConfig
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(config_path: str) -> SiteConfigRoot:
    """
    加载并验证配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        SiteConfigRoot: 验证后的配置对象
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    try:
        config = SiteConfigRoot(**config_data)
        return config
    except Exception as e:
        raise ValueError(f"配置验证失败: {str(e)}")


if __name__ == "__main__":
    # 测试配置加载
    import sys
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        try:
            config = load_config(config_file)
            print(f"配置验证成功: {config_file}")
            print(f"站点: {config.site.name} ({config.site.id})")
            print(f"基础URL: {config.site.base_url}")
        except Exception as e:
            print(f"配置验证失败: {str(e)}")
            sys.exit(1)
    else:
        print("用法: python config_models.py <配置文件路径>")
        sys.exit(1)
