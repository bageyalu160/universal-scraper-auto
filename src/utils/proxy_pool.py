#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理池管理模块

该模块提供代理IP的获取、验证、轮换和管理功能，
支持从API和文件读取代理源，自动定期验证代理的可用性，
并提供轮换使用和失败汇报机制。
"""

import os
import time
import json
import random
import logging
import threading
import requests
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/proxy_pool.log')
    ]
)

logger = logging.getLogger('proxy_pool')


class ProxyPool:
    """
    代理池类，负责管理和提供代理IP
    
    特性：
    - 支持从API和文件中加载代理IP
    - 自动验证代理可用性
    - 支持代理轮换策略
    - 记录代理使用状态和成功率
    - 异常恢复机制
    """
    
    _instance = None  # 单例模式实例
    _lock = threading.Lock()  # 线程锁，用于保证并发安全
    
    def __new__(cls, *args, **kwargs):
        """
        单例模式实现，确保全局只有一个代理池实例
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ProxyPool, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化代理池
        
        Args:
            config_path (Optional[str]): 配置文件路径，如果为None则使用默认路径
        """
        # 避免重复初始化
        if self._initialized:
            return
        
        self._initialized = True
        self.proxies = []  # 可用代理列表
        self.used_proxies = {}  # 代理使用记录: {proxy: {'count': 使用次数, 'success': 成功次数, 'last_used': 最后使用时间}}
        self.failed_proxies = {}  # 失败代理记录: {proxy: 失败次数}
        self.last_update = 0  # 上次代理池更新时间
        self.config = self._load_config(config_path)  # 加载配置
        self.update_interval = self.config.get('update_interval', 3600)  # 默认1小时更新一次
        self.max_fails = self.config.get('max_fails', 3)  # 代理最大失败次数
        self.recovery_threshold = self.config.get('recovery_threshold', 5)  # 触发恢复的代理数量阈值
        self.auto_recovery = self.config.get('auto_recovery', True)  # 是否启用自动恢复
        
        # 创建代理状态存储目录
        self.status_dir = Path('status/proxies')
        self.status_dir.mkdir(parents=True, exist_ok=True)
        
        # 从状态文件恢复代理池状态
        self._load_status()
        
        # 初始更新代理池
        self.update_proxies()
        
        # 启动后台自动更新线程
        self._start_auto_update()
        
        logger.info("代理池初始化完成")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        加载代理池配置
        
        Args:
            config_path (Optional[str]): 配置文件路径
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        # 如果提供了配置路径，直接加载
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.endswith('.json'):
                    return json.load(f)
                else:
                    import yaml
                    return yaml.safe_load(f)
        
        # 否则尝试从默认配置文件加载
        config_paths = [
            'config/proxy_pool.json',
            'config/proxy_pool.yaml',
            'config/proxy_pool.yml',
            'config/settings.yaml'
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    if path.endswith('.json'):
                        settings = json.load(f)
                    else:
                        import yaml
                        settings = yaml.safe_load(f)
                    
                    # 从settings中提取proxy_pool配置
                    if 'proxy_pool' in settings:
                        return settings['proxy_pool']
                    return settings
        
        # 如果没有找到配置文件，返回默认配置
        logger.warning("未找到代理池配置文件，使用默认配置")
        return {
            'update_interval': 3600,
            'timeout': 5,
            'max_fails': 3,
            'sources': [
                {
                    'type': 'api',
                    'url': 'https://proxy.example.com/api/v1/proxies',
                    'headers': {'Authorization': 'Bearer demo_key'}
                }
            ]
        }
    
    def _save_status(self):
        """
        保存代理池状态到文件，便于程序重启后恢复
        """
        status = {
            'proxies': self.proxies,
            'used_proxies': self.used_proxies,
            'failed_proxies': self.failed_proxies,
            'last_update': self.last_update
        }
        
        status_file = self.status_dir / 'proxy_status.json'
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f)
        
        logger.debug("代理池状态已保存")
    
    def _load_status(self):
        """
        从文件加载代理池状态
        """
        status_file = self.status_dir / 'proxy_status.json'
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                
                self.proxies = status.get('proxies', [])
                self.used_proxies = status.get('used_proxies', {})
                self.failed_proxies = status.get('failed_proxies', {})
                self.last_update = status.get('last_update', 0)
                
                logger.info(f"从状态文件恢复了 {len(self.proxies)} 个代理")
            except Exception as e:
                logger.error(f"加载代理池状态失败: {e}")
    
    def _start_auto_update(self):
        """
        启动自动更新线程，定期更新代理池
        """
        def auto_update():
            while True:
                # 检查是否需要更新
                if time.time() - self.last_update > self.update_interval:
                    try:
                        self.update_proxies()
                    except Exception as e:
                        logger.error(f"自动更新代理池失败: {e}")
                
                # 休眠一段时间
                time.sleep(min(300, self.update_interval / 12))  # 最多每5分钟检查一次
        
        # 创建并启动线程
        update_thread = threading.Thread(target=auto_update, daemon=True)
        update_thread.start()
        logger.info("代理池自动更新线程已启动")
    
    def update_proxies(self, force: bool = False, source_type: str = "all"):
        """
        更新代理池，从各种代理源获取新代理
        
        Args:
            force (bool): 是否强制更新，即使未到更新时间
            source_type (str): 代理源类型，可选值为"all", "api", "file"
        """
        # 如果未到更新时间且非强制更新，则跳过
        if time.time() - self.last_update < self.update_interval and not force:
            return
        
        with self._lock:
            logger.info(f"开始更新代理池 (源类型: {source_type})")
            new_proxies = []
            
            # 获取配置中的代理源
            sources = self.config.get('sources', [])
            
            # 过滤指定类型的代理源
            if source_type != "all":
                sources = [s for s in sources if s.get('type', '') == source_type]
            
            # 从各个代理源获取代理
            for source in sources:
                source_type = source.get('type', '')
                
                try:
                    if source_type == 'api':
                        # 从API获取代理
                        proxies = self._get_proxies_from_api(source)
                        new_proxies.extend(proxies)
                    
                    elif source_type == 'file':
                        # 从文件获取代理
                        proxies = self._get_proxies_from_file(source)
                        new_proxies.extend(proxies)
                except Exception as e:
                    logger.error(f"从源 {source_type} 获取代理失败: {e}")
            
            # 更新代理池
            if new_proxies:
                # 保留之前的有效代理，并添加新代理
                old_valid_proxies = [p for p in self.proxies if p not in self.failed_proxies]
                combined_proxies = list(set(old_valid_proxies + new_proxies))
                
                # 验证代理有效性
                self.proxies = self._validate_proxies(combined_proxies)
                
                # 更新时间
                self.last_update = time.time()
                
                # 保存状态
                self._save_status()
                
                logger.info(f"代理池更新完成，当前有 {len(self.proxies)} 个有效代理")
            else:
                logger.warning("未获取到新的代理")
                
                # 检查是否需要触发恢复机制
                if len(self.proxies) < self.recovery_threshold and self.auto_recovery:
                    logger.warning(f"代理数量低于阈值 ({len(self.proxies)} < {self.recovery_threshold})，尝试恢复失败代理")
                    self._try_recover_failed_proxies()
    
    def _try_recover_failed_proxies(self):
        """尝试恢复部分失败的代理，用于在代理不足时临时应急"""
        # 如果没有失败代理，直接返回
        if not self.failed_proxies:
            return
        
        logger.info("开始尝试恢复失败代理")
        
        # 筛选失败次数较少的代理进行重试
        retry_candidates = {}
        for proxy, fails in self.failed_proxies.items():
            if fails <= self.max_fails:  # 只重试失败次数不超过阈值的代理
                retry_candidates[proxy] = fails
        
        # 按失败次数排序，优先尝试失败较少的代理
        sorted_candidates = sorted(retry_candidates.items(), key=lambda x: x[1])
        
        # 最多尝试20个代理
        candidates_to_try = [p[0] for p in sorted_candidates[:20]]
        
        if candidates_to_try:
            # 重新验证这些代理
            recovered_proxies = self._validate_proxies(candidates_to_try)
            
            # 将验证通过的代理添加回代理池，并从失败列表中移除
            for proxy in recovered_proxies:
                if proxy in self.failed_proxies:
                    del self.failed_proxies[proxy]
                    if proxy not in self.proxies:
                        self.proxies.append(proxy)
            
            # 保存状态
            self._save_status()
            
            logger.info(f"成功恢复 {len(recovered_proxies)} 个代理")
        else:
            logger.info("没有合适的失败代理可供恢复")
    
    def integrate_with_workflow(self, action: str = "update", source_type: str = "all") -> Dict[str, Any]:
        """
        与工作流集成的接口，提供统一的命令执行入口
        
        Args:
            action (str): 要执行的操作，可选值为 "update", "validate", "clear", "rebuild", "recover"
            source_type (str): 代理源类型，用于更新操作，可选值为 "all", "api", "file"
            
        Returns:
            Dict[str, Any]: 操作结果统计
        """
        start_time = time.time()
        result = {
            "action": action,
            "timestamp": time.time()
        }
        
        try:
            if action == "update":
                self.update_proxies(force=True, source_type=source_type)
                result.update({
                    "source": source_type,
                    "valid_count": len(self.proxies),
                    "failed_count": len(self.failed_proxies)
                })
            
            elif action == "validate":
                # 获取验证前的代理数
                before_count = len(self.proxies)
                
                # 验证所有代理
                self.proxies = self._validate_proxies(self.proxies)
                self.last_update = time.time()
                self._save_status()
                
                # 获取验证后的代理数
                after_count = len(self.proxies)
                
                # 计算失效率
                fail_rate = ((before_count - after_count) / before_count * 100) if before_count > 0 else 0
                
                result.update({
                    "before_count": before_count,
                    "after_count": after_count,
                    "fail_rate": fail_rate
                })
            
            elif action == "clear":
                # 获取清理前的计数
                failed_before = len(self.failed_proxies)
                
                # 清空失效代理列表
                self.failed_proxies = {}
                self._save_status()
                
                result.update({
                    "failed_cleared": failed_before
                })
            
            elif action == "rebuild":
                # 清空现有代理
                self.proxies = []
                self.failed_proxies = {}
                self.used_proxies = {}
                
                # 更新代理池
                self.update_proxies(force=True, source_type=source_type)
                
                result.update({
                    "source": source_type,
                    "valid_count": len(self.proxies)
                })
            
            elif action == "recover":
                # 尝试恢复失败代理
                before_count = len(self.proxies)
                self._try_recover_failed_proxies()
                after_count = len(self.proxies)
                
                result.update({
                    "before_count": before_count,
                    "after_count": after_count,
                    "recovered_count": after_count - before_count
                })
            
            else:
                raise ValueError(f"未知操作类型: {action}")
            
            # 计算操作耗时
            result["elapsed_time"] = time.time() - start_time
            result["status"] = "success"
            
        except Exception as e:
            logger.error(f"执行操作 {action} 时发生错误: {e}")
            
            # 添加错误信息到结果
            result["status"] = "error"
            result["error"] = str(e)
            result["elapsed_time"] = time.time() - start_time
        
        return result
    
    def _get_proxies_from_api(self, source: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        从API获取代理
        
        Args:
            source (Dict[str, Any]): 代理源配置
            
        Returns:
            List[Dict[str, str]]: 代理列表
        """
        url = source.get('url', '')
        if not url:
            logger.error("API代理源URL未指定")
            return []
        
        # 获取请求头和参数
        headers = source.get('headers', {})
        params = source.get('params', {})
        
        try:
            # 发送请求获取代理
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                # 尝试解析响应
                data = response.json()
                
                # 根据API响应格式进行解析
                # 这里需要根据实际API格式调整
                if isinstance(data, list):
                    # 如果返回的直接是代理列表
                    proxies = []
                    for item in data:
                        if isinstance(item, str):
                            # 格式: "ip:port"
                            ip, port = item.split(':')
                            proxies.append({
                                'http': f'http://{item}',
                                'https': f'http://{item}'
                            })
                        elif isinstance(item, dict):
                            # 格式: {"ip": "x.x.x.x", "port": xxxx}
                            ip = item.get('ip')
                            port = item.get('port')
                            if ip and port:
                                proxy_str = f"{ip}:{port}"
                                proxies.append({
                                    'http': f'http://{proxy_str}',
                                    'https': f'http://{proxy_str}'
                                })
                    
                    logger.info(f"从API获取了 {len(proxies)} 个代理")
                    return proxies
                
                elif isinstance(data, dict):
                    # 如果返回的是包含代理列表的字典
                    proxies = []
                    proxy_list = data.get('proxies', []) or data.get('data', []) or data.get('list', [])
                    
                    for item in proxy_list:
                        if isinstance(item, str):
                            # 格式: "ip:port"
                            proxies.append({
                                'http': f'http://{item}',
                                'https': f'http://{item}'
                            })
                        elif isinstance(item, dict):
                            # 格式: {"ip": "x.x.x.x", "port": xxxx}
                            ip = item.get('ip')
                            port = item.get('port')
                            if ip and port:
                                proxy_str = f"{ip}:{port}"
                                proxies.append({
                                    'http': f'http://{proxy_str}',
                                    'https': f'http://{proxy_str}'
                                })
                    
                    logger.info(f"从API获取了 {len(proxies)} 个代理")
                    return proxies
            
            logger.error(f"从API获取代理失败，状态码: {response.status_code}")
            return []
            
        except Exception as e:
            logger.error(f"从API获取代理时出错: {e}")
            return []
    
    def _get_proxies_from_file(self, source: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        从文件获取代理
        
        Args:
            source (Dict[str, Any]): 代理源配置
            
        Returns:
            List[Dict[str, str]]: 代理列表
        """
        file_path = source.get('path', '')
        if not file_path or not os.path.exists(file_path):
            logger.error(f"代理文件不存在: {file_path}")
            return []
        
        try:
            proxies = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 尝试解析行
                        try:
                            if line.startswith('{'):
                                # JSON格式
                                proxy_dict = json.loads(line)
                                if 'http' in proxy_dict:
                                    proxies.append(proxy_dict)
                                else:
                                    ip = proxy_dict.get('ip')
                                    port = proxy_dict.get('port')
                                    if ip and port:
                                        proxy_str = f"{ip}:{port}"
                                        proxies.append({
                                            'http': f'http://{proxy_str}',
                                            'https': f'http://{proxy_str}'
                                        })
                            else:
                                # 纯文本格式 "ip:port"
                                proxies.append({
                                    'http': f'http://{line}',
                                    'https': f'http://{line}'
                                })
                        except:
                            continue
            
            logger.info(f"从文件获取了 {len(proxies)} 个代理")
            return proxies
            
        except Exception as e:
            logger.error(f"从文件获取代理时出错: {e}")
            return []
    
    def _validate_proxies(self, proxies: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        验证代理的有效性
        
        Args:
            proxies (List[Dict[str, str]]): 待验证的代理列表
            
        Returns:
            List[Dict[str, str]]: 有效的代理列表
        """
        logger.info(f"开始验证 {len(proxies)} 个代理")
        valid_proxies = []
        
        # 测试URL，可以配置多个用于验证
        test_urls = self.config.get('test_urls', ['http://www.baidu.com', 'http://www.qq.com'])
        timeout = self.config.get('timeout', 5)
        
        for proxy in proxies:
            is_valid = False
            
            # 尝试不同的测试URL
            for test_url in test_urls:
                try:
                    # 发送测试请求
                    response = requests.get(
                        test_url,
                        proxies=proxy,
                        timeout=timeout,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )
                    
                    if response.status_code == 200:
                        is_valid = True
                        break
                        
                except:
                    continue
            
            if is_valid:
                valid_proxies.append(proxy)
        
        logger.info(f"验证完成，有 {len(valid_proxies)}/{len(proxies)} 个有效代理")
        return valid_proxies
    
    def get_proxy(self, rotate: bool = False) -> Dict[str, str]:
        """
        获取一个代理
        
        Args:
            rotate (bool): 是否轮换代理，即使当前代理仍然可用
            
        Returns:
            Dict[str, str]: 代理字典 {'http': 'http://ip:port', 'https': 'http://ip:port'}
        """
        with self._lock:
            # 检查是否需要更新代理池
            if time.time() - self.last_update > self.update_interval:
                self.update_proxies()
            
            # 如果代理池为空，强制更新
            if not self.proxies:
                self.update_proxies(force=True)
                if not self.proxies:
                    logger.error("无可用代理")
                    return {}
            
            # 选择代理
            chosen_proxy = None
            
            # 如果需要轮换代理，则选择使用次数最少或最近最少使用的代理
            if rotate:
                # 按使用次数排序代理
                sorted_proxies = sorted(
                    self.proxies,
                    key=lambda p: (
                        self.used_proxies.get(str(p), {}).get('count', 0),
                        self.used_proxies.get(str(p), {}).get('last_used', 0)
                    )
                )
                
                # 选择使用最少的代理
                if sorted_proxies:
                    chosen_proxy = sorted_proxies[0]
            else:
                # 随机选择代理
                chosen_proxy = random.choice(self.proxies)
            
            if chosen_proxy:
                # 更新代理使用记录
                proxy_str = str(chosen_proxy)
                if proxy_str not in self.used_proxies:
                    self.used_proxies[proxy_str] = {'count': 0, 'success': 0, 'last_used': 0}
                
                self.used_proxies[proxy_str]['count'] += 1
                self.used_proxies[proxy_str]['last_used'] = time.time()
                
                # 保存状态
                self._save_status()
                
                return chosen_proxy
            
            return {}
    
    def report_proxy_status(self, proxy: Dict[str, str], success: bool):
        """
        报告代理使用状态
        
        Args:
            proxy (Dict[str, str]): 代理字典
            success (bool): 使用是否成功
        """
        if not proxy:
            return
        
        with self._lock:
            proxy_str = str(proxy)
            
            # 更新使用记录
            if proxy_str in self.used_proxies:
                if success:
                    self.used_proxies[proxy_str]['success'] += 1
                    
                    # 如果代理在失败列表中，减少失败计数
                    if proxy_str in self.failed_proxies:
                        self.failed_proxies[proxy_str] -= 1
                        if self.failed_proxies[proxy_str] <= 0:
                            del self.failed_proxies[proxy_str]
                else:
                    # 记录失败
                    if proxy_str not in self.failed_proxies:
                        self.failed_proxies[proxy_str] = 0
                    
                    self.failed_proxies[proxy_str] += 1
                    
                    # 如果失败次数超过阈值，从代理池中移除
                    if self.failed_proxies[proxy_str] >= self.max_fails:
                        if proxy in self.proxies:
                            self.proxies.remove(proxy)
                            logger.warning(f"代理 {proxy_str} 失败次数过多，已从代理池移除")
            
            # 保存状态
            self._save_status()
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        """
        获取代理池统计信息
        
        Returns:
            Dict[str, Any]: 代理池统计信息
        """
        with self._lock:
            total = len(self.proxies)
            used = len(self.used_proxies)
            failed = len(self.failed_proxies)
            
            # 计算成功率
            success_rates = {}
            for proxy_str, stats in self.used_proxies.items():
                count = stats.get('count', 0)
                success = stats.get('success', 0)
                if count > 0:
                    success_rates[proxy_str] = round(success / count * 100, 2)
            
            # 计算平均成功率
            avg_success_rate = 0
            if used > 0:
                avg_success_rate = round(sum(success_rates.values()) / used, 2)
            
            return {
                'total': total,
                'used': used,
                'failed': failed,
                'avg_success_rate': avg_success_rate,
                'last_update': self.last_update,
                'update_interval': self.update_interval
            }


# 全局函数，便于外部调用
def get_proxy_pool() -> ProxyPool:
    """
    获取代理池实例
    
    Returns:
        ProxyPool: 代理池实例
    """
    return ProxyPool()


def get_proxy(rotate: bool = False) -> Dict[str, str]:
    """
    获取一个代理
    
    Args:
        rotate (bool): 是否轮换代理
        
    Returns:
        Dict[str, str]: 代理字典
    """
    return get_proxy_pool().get_proxy(rotate)


def report_proxy_status(proxy: Dict[str, str], success: bool):
    """
    报告代理使用状态
    
    Args:
        proxy (Dict[str, str]): 代理字典
        success (bool): 使用是否成功
    """
    get_proxy_pool().report_proxy_status(proxy, success)


def get_proxy_stats() -> Dict[str, Any]:
    """
    获取代理池统计信息
    
    Returns:
        Dict[str, Any]: 代理池统计信息
    """
    return get_proxy_pool().get_proxy_stats()


if __name__ == "__main__":
    # 命令行运行时，打印代理池状态
    pool = get_proxy_pool()
    pool.update_proxies(force=True)
    
    stats = pool.get_proxy_stats()
    print(f"代理池状态:")
    print(f"总代理数: {stats['total']}")
    print(f"已使用代理数: {stats['used']}")
    print(f"失败代理数: {stats['failed']}")
    print(f"平均成功率: {stats['avg_success_rate']}%")
    print(f"上次更新时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats['last_update']))}") 