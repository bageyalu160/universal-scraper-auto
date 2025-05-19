#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 依赖项管理工具
"""

import os
import sys
import logging
import platform
import subprocess
import json
import tempfile
import shutil
from pathlib import Path
import requests


def ensure_schema_directory(schema_dir):
    """
    确保 Schema 目录存在
    
    Args:
        schema_dir: Schema 目录路径
        
    Returns:
        创建的目录路径
    """
    schema_dir = Path(schema_dir)
    schema_dir.mkdir(parents=True, exist_ok=True)
    return schema_dir


def download_schema(schema_url, output_path, logger=None):
    """
    下载 JSON Schema 文件
    
    Args:
        schema_url: Schema URL
        output_path: 输出文件路径
        logger: 可选的日志记录器
        
    Returns:
        是否成功下载
    """
    logger = logger or logging.getLogger('workflow_generator')
    
    try:
        logger.info(f"正在下载 Schema: {schema_url}")
        response = requests.get(schema_url, timeout=30)
        response.raise_for_status()
        
        # 验证是否为有效的 JSON Schema
        schema = response.json()
        if not isinstance(schema, dict) or '$schema' not in schema:
            logger.warning("下载的 Schema 可能不是有效的 JSON Schema")
        
        # 保存到文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2)
            
        logger.info(f"Schema 已下载到: {output_path}")
        return True
    except Exception as e:
        logger.error(f"下载 Schema 失败: {e}")
        return False


def check_actionlint_installed():
    """
    检查是否安装了 actionlint
    
    Returns:
        bool: 是否已安装
    """
    try:
        result = subprocess.run(['actionlint', '--version'], 
                                capture_output=True, text=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_actionlint(logger=None):
    """
    尝试安装 actionlint
    
    Args:
        logger: 可选的日志记录器
        
    Returns:
        bool: 是否成功安装
    """
    logger = logger or logging.getLogger('workflow_generator')
    
    # 检查当前系统
    system = platform.system().lower()
    
    if system == 'darwin':  # macOS
        try:
            logger.info("正在尝试通过 Homebrew 安装 actionlint...")
            result = subprocess.run(['brew', 'install', 'actionlint'], 
                                   capture_output=True, text=True, check=False)
            if result.returncode == 0:
                logger.info("成功安装 actionlint")
                return True
            else:
                logger.warning(f"通过 Homebrew 安装 actionlint 失败: {result.stderr}")
        except Exception as e:
            logger.warning(f"通过 Homebrew 安装 actionlint 失败: {e}")
    
    elif system == 'linux':  # Linux
        try:
            logger.info("正在尝试通过 go install 安装 actionlint...")
            result = subprocess.run(['go', 'install', 'github.com/rhysd/actionlint/cmd/actionlint@latest'], 
                                   capture_output=True, text=True, check=False)
            if result.returncode == 0:
                logger.info("成功安装 actionlint")
                return True
            else:
                logger.warning(f"通过 go install 安装 actionlint 失败: {result.stderr}")
        except Exception as e:
            logger.warning(f"通过 go install 安装 actionlint 失败: {e}")
    
    # 如果以上方法都失败，尝试从GitHub下载二进制文件
    try:
        logger.info("正在尝试从 GitHub 下载 actionlint 二进制文件...")
        
        # 获取最新版本
        releases_url = "https://api.github.com/repos/rhysd/actionlint/releases/latest"
        response = requests.get(releases_url, timeout=30)
        response.raise_for_status()
        latest_release = response.json()
        
        # 确定适合当前系统的资源
        arch = 'amd64' if platform.machine() in ('x86_64', 'AMD64') else 'arm64'
        asset_pattern = f"actionlint_{system}_{arch}.tar.gz"
        
        # 查找匹配的资源
        matching_assets = [a for a in latest_release['assets'] if asset_pattern in a['name']]
        if not matching_assets:
            logger.warning(f"未找到适合当前系统的 actionlint 二进制文件: {system}_{arch}")
            return False
            
        download_url = matching_assets[0]['browser_download_url']
        
        # 下载并解压
        with tempfile.TemporaryDirectory() as temp_dir:
            tar_path = os.path.join(temp_dir, "actionlint.tar.gz")
            
            # 下载
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            with open(tar_path, 'wb') as f:
                f.write(response.content)
            
            # 解压
            subprocess.run(['tar', '-xzf', tar_path, '-C', temp_dir], check=True)
            
            # 移动到 PATH 目录
            bin_dir = os.path.expanduser("~/.local/bin")
            os.makedirs(bin_dir, exist_ok=True)
            
            shutil.copy(os.path.join(temp_dir, "actionlint"), os.path.join(bin_dir, "actionlint"))
            os.chmod(os.path.join(bin_dir, "actionlint"), 0o755)
            
            logger.info(f"actionlint 已安装到: {bin_dir}/actionlint")
            
            # 确保 bin 目录在 PATH 中
            if bin_dir not in os.environ['PATH'].split(os.pathsep):
                logger.warning(f"请将 {bin_dir} 添加到 PATH 环境变量中")
            
            return True
    except Exception as e:
        logger.error(f"安装 actionlint 失败: {e}")
        return False
    
    logger.warning("无法自动安装 actionlint，请手动安装")
    return False


def setup_dependencies(logger=None):
    """
    设置工作流生成器所需的所有依赖项
    
    Args:
        logger: 可选的日志记录器
        
    Returns:
        bool: 是否成功设置所有依赖项
    """
    logger = logger or logging.getLogger('workflow_generator')
    
    success = True
    
    # 设置 Schema 目录
    schema_dir = ensure_schema_directory(Path(__file__).parent.parent / "validators" / "schemas")
    
    # 下载 GitHub Actions Schema
    schema_path = schema_dir / "github-workflow.json"
    if not schema_path.exists():
        success = download_schema(
            "https://json.schemastore.org/github-workflow.json", 
            schema_path,
            logger
        ) and success
    
    # 检查并安装 actionlint
    if not check_actionlint_installed():
        logger.info("系统中未安装 actionlint，尝试安装...")
        success = install_actionlint(logger) and success
    else:
        logger.info("系统中已安装 actionlint")
    
    return success


if __name__ == "__main__":
    # 设置日志记录
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('workflow_generator')
    
    # 设置依赖项
    setup_dependencies(logger) 