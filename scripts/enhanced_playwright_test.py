#!/usr/bin/env python3
"""
Universal Scraper 增强版 Playwright 测试脚本
支持多浏览器测试、代理设置、浏览器指纹伪装和验证码处理
"""

import asyncio
import os
import sys
import time
import json
import random
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import argparse
import psutil  # 用于性能监控

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("playwright-test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 测试场景列表
TEST_SCENARIOS = [
    {
        "name": "百度搜索测试",
        "url": "https://www.baidu.com/",
        "title_contains": "百度",
        "actions": [
            {"type": "fill", "selector": "#kw", "value": "Playwright 自动化测试"},
            {"type": "click", "selector": "#su"},
            {"type": "wait_for_selector", "selector": "#content_left"},
        ]
    },
    {
        "name": "GitHub访问测试",
        "url": "https://github.com/",
        "title_contains": "GitHub",
        "actions": []
    },
    {
        "name": "京东商品搜索测试",
        "url": "https://www.jd.com/",
        "title_contains": "京东",
        "actions": [
            {"type": "fill", "selector": "#key", "value": "手机"},
            {"type": "click", "selector": ".button"},
            {"type": "wait_for_selector", "selector": ".gl-warp"},
            {"type": "scroll", "distance": 500, "delay": 500, "count": 3},
            {"type": "wait", "time": 2000},
        ]
    },
    {
        "name": "淘宝商品页测试",
        "url": "https://www.taobao.com/",
        "title_contains": "淘宝",
        "actions": [
            {"type": "fill", "selector": "#q", "value": "笔记本电脑"},
            {"type": "click", "selector": ".btn-search"},
            {"type": "wait_for_selector", "selector": ".item"},
            {"type": "scroll", "distance": 500, "delay": 500, "count": 3},
        ],
        "requires_captcha_handling": True
    }
]

# 浏览器指纹配置
BROWSER_FINGERPRINTS = {
    "chrome_win10": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "viewport": {"width": 1280, "height": 800},
        "platform": "Windows",
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "color_scheme": "light"
    },
    "firefox_mac": {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:95.0) Gecko/20100101 Firefox/95.0",
        "viewport": {"width": 1440, "height": 900},
        "platform": "MacOS",
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "color_scheme": "light"
    },
    "chrome_android": {
        "user_agent": "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.104 Mobile Safari/537.36",
        "viewport": {"width": 393, "height": 851},
        "platform": "Android",
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "color_scheme": "light",
        "is_mobile": True
    }
}

# 代理配置
PROXY_LIST = [
    {
        "server": "http://127.0.0.1:7890",
        "username": "",
        "password": ""
    },
    # 可以添加更多代理
]

class PerformanceMonitor:
    """性能监控类"""
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            "memory_usage": [],
            "cpu_usage": [],
            "network_requests": 0,
            "page_load_times": []
        }
    
    def update_system_metrics(self):
        """更新系统指标"""
        process = psutil.Process(os.getpid())
        self.metrics["memory_usage"].append(process.memory_info().rss / 1024 / 1024)  # MB
        self.metrics["cpu_usage"].append(psutil.cpu_percent(interval=0.1))
    
    def record_page_load(self, load_time: float):
        """记录页面加载时间"""
        self.metrics["page_load_times"].append(load_time)
    
    def increment_network_requests(self):
        """增加网络请求计数"""
        self.metrics["network_requests"] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        duration = time.time() - self.start_time
        return {
            "duration": duration,
            "avg_memory_usage": sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
            "max_memory_usage": max(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0,
            "avg_cpu_usage": sum(self.metrics["cpu_usage"]) / len(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
            "network_requests": self.metrics["network_requests"],
            "avg_page_load_time": sum(self.metrics["page_load_times"]) / len(self.metrics["page_load_times"]) if self.metrics["page_load_times"] else 0
        }

class CaptchaHandler:
    """验证码处理类"""
    async def detect_captcha(self, page: Page) -> bool:
        """检测页面是否存在验证码"""
        # 这里实现验证码检测逻辑，例如查找特定元素或图像
        captcha_selectors = [
            "img[src*='captcha']", 
            "img[src*='verify']", 
            ".captcha",
            "#captcha",
            ".verify-code",
            ".slidecode-container"
        ]
        
        for selector in captcha_selectors:
            try:
                captcha_element = await page.query_selector(selector)
                if captcha_element:
                    logger.info(f"检测到验证码元素: {selector}")
                    return True
            except Exception as e:
                logger.debug(f"检查验证码选择器 {selector} 时出错: {str(e)}")
        
        return False
    
    async def solve_captcha(self, page: Page) -> bool:
        """尝试解决验证码"""
        # 检测验证码类型
        if await self._is_slider_captcha(page):
            return await self._solve_slider_captcha(page)
        elif await self._is_image_captcha(page):
            return await self._solve_image_captcha(page)
        else:
            logger.warning("未知验证码类型，无法自动解决")
            return False
    
    async def _is_slider_captcha(self, page: Page) -> bool:
        """检测是否为滑块验证码"""
        slider_selectors = [".slidecode-container", ".slide-verify", ".slider-captcha"]
        for selector in slider_selectors:
            if await page.query_selector(selector):
                return True
        return False
    
    async def _is_image_captcha(self, page: Page) -> bool:
        """检测是否为图片验证码"""
        image_selectors = ["input[name='captcha']", ".image-captcha", "#captcha-input"]
        for selector in image_selectors:
            if await page.query_selector(selector):
                return True
        return False
    
    async def _solve_slider_captcha(self, page: Page) -> bool:
        """解决滑块验证码"""
        try:
            # 查找滑块元素
            slider = await page.query_selector(".slidecode-slider")
            if not slider:
                logger.warning("未找到滑块元素")
                return False
            
            # 获取滑块位置
            slider_box = await slider.bounding_box()
            if not slider_box:
                return False
            
            # 模拟人类拖动行为
            await page.mouse.move(slider_box["x"] + slider_box["width"] / 2, slider_box["y"] + slider_box["height"] / 2)
            await page.mouse.down()
            
            # 分段移动，模拟人类行为
            steps = random.randint(5, 10)
            distance = random.randint(150, 250)  # 滑动距离
            
            for i in range(steps):
                step_distance = distance * (i + 1) / steps
                await page.mouse.move(slider_box["x"] + step_distance, slider_box["y"] + slider_box["height"] / 2 + random.randint(-3, 3))
                await asyncio.sleep(random.uniform(0.01, 0.05))
            
            await page.mouse.up()
            await asyncio.sleep(1)
            
            # 检查是否成功
            success_element = await page.query_selector(".slidecode-success")
            return bool(success_element)
        
        except Exception as e:
            logger.error(f"解决滑块验证码时出错: {str(e)}")
            return False
    
    async def _solve_image_captcha(self, page: Page) -> bool:
        """解决图片验证码"""
        # 注意：实际项目中可能需要接入第三方验证码识别服务
        logger.warning("图片验证码需要接入第三方识别服务，当前为模拟实现")
        
        try:
            # 查找验证码输入框
            input_field = await page.query_selector("input[name='captcha']")
            if not input_field:
                logger.warning("未找到验证码输入框")
                return False
            
            # 模拟输入随机验证码（实际项目中应该使用真实识别结果）
            mock_captcha = "".join(random.choices("0123456789", k=4))
            await input_field.fill(mock_captcha)
            
            # 查找提交按钮并点击
            submit_button = await page.query_selector("button[type='submit']")
            if submit_button:
                await submit_button.click()
            
            await asyncio.sleep(1)
            return True
        
        except Exception as e:
            logger.error(f"解决图片验证码时出错: {str(e)}")
            return False

async def setup_browser_context(
    playwright, 
    browser_name: str, 
    fingerprint_name: Optional[str] = None,
    use_proxy: bool = False
) -> tuple:
    """设置浏览器上下文，应用指纹和代理"""
    # 获取浏览器启动器
    browser_launcher = getattr(playwright, browser_name)
    
    # 基本浏览器选项
    browser_options = {
        "headless": False,  # 设置为 False 以便观察浏览器行为
    }
    
    # 启动浏览器
    browser = await browser_launcher.launch(**browser_options)
    
    # 上下文选项
    context_options = {}
    
    # 应用指纹设置
    if fingerprint_name and fingerprint_name in BROWSER_FINGERPRINTS:
        fingerprint = BROWSER_FINGERPRINTS[fingerprint_name]
        context_options.update({
            "user_agent": fingerprint["user_agent"],
            "viewport": fingerprint["viewport"],
            "locale": fingerprint["locale"],
            "timezone_id": fingerprint["timezone_id"],
            "color_scheme": fingerprint["color_scheme"],
        })
        
        if fingerprint.get("is_mobile", False):
            context_options["is_mobile"] = True
    
    # 应用代理设置
    if use_proxy and PROXY_LIST:
        proxy = random.choice(PROXY_LIST)
        context_options["proxy"] = {
            "server": proxy["server"],
        }
        if proxy["username"] and proxy["password"]:
            context_options["proxy"]["username"] = proxy["username"]
            context_options["proxy"]["password"] = proxy["password"]
    
    # 创建上下文和页面
    context = await browser.new_context(**context_options)
    page = await context.new_page()
    
    # 设置页面事件监听
    page.on("request", lambda request: logger.debug(f"请求: {request.method} {request.url}"))
    page.on("response", lambda response: logger.debug(f"响应: {response.status} {response.url}"))
    
    return browser, context, page

async def run_test_scenario(page: Page, scenario: Dict[str, Any], performance_monitor: PerformanceMonitor) -> Dict[str, Any]:
    """运行单个测试场景"""
    logger.info(f"\n执行测试: {scenario['name']}")
    
    # 访问URL
    logger.info(f"正在访问 {scenario['url']}...")
    start_time = time.time()
    await page.goto(scenario['url'])
    load_time = time.time() - start_time
    performance_monitor.record_page_load(load_time)
    logger.info(f"页面加载时间: {load_time:.2f} 秒")
    
    # 验证标题
    title = await page.title()
    logger.info(f"页面标题: {title}")
    assert scenario['title_contains'] in title, f"页面标题不包含'{scenario['title_contains']}': {title}"
    
    # 处理验证码
    if scenario.get("requires_captcha_handling", False):
        captcha_handler = CaptchaHandler()
        if await captcha_handler.detect_captcha(page):
            logger.info("检测到验证码，尝试解决...")
            captcha_solved = await captcha_handler.solve_captcha(page)
            if captcha_solved:
                logger.info("验证码解决成功")
            else:
                logger.warning("验证码解决失败")
    
    # 执行操作
    for action in scenario['actions']:
        action_type = action['type']
        performance_monitor.update_system_metrics()
        
        if action_type == "fill":
            await page.fill(action['selector'], action['value'])
            logger.info(f"填写文本: {action['selector']} -> {action['value']}")
        
        elif action_type == "click":
            await page.click(action['selector'])
            logger.info(f"点击元素: {action['selector']}")
            performance_monitor.increment_network_requests()
        
        elif action_type == "wait_for_selector":
            await page.wait_for_selector(action['selector'])
            logger.info(f"等待元素: {action['selector']}")
        
        elif action_type == "wait":
            await asyncio.sleep(action['time'] / 1000)
            logger.info(f"等待: {action['time']} 毫秒")
        
        elif action_type == "scroll":
            for i in range(action['count']):
                await page.evaluate(f"window.scrollBy(0, {action['distance']});")
                logger.info(f"滚动: {action['distance']} 像素 ({i+1}/{action['count']})")
                await asyncio.sleep(action['delay'] / 1000)
    
    # 截图
    os.makedirs("playwright-report", exist_ok=True)
    screenshot_path = f"playwright-report/{scenario['name'].replace(' ', '_')}.png"
    await page.screenshot(path=screenshot_path)
    logger.info(f"截图已保存到 {screenshot_path}")
    
    # 提取数据示例
    data_extracted = {}
    if "data_extraction" in scenario:
        for field_name, selector in scenario["data_extraction"].items():
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    data_extracted[field_name] = text.strip()
            except Exception as e:
                logger.error(f"提取数据 '{field_name}' 时出错: {str(e)}")
    
    return {
        "name": scenario['name'],
        "title": title,
        "screenshot": os.path.basename(screenshot_path),
        "success": True,
        "load_time": load_time,
        "data_extracted": data_extracted
    }

async def main():
    """运行所有Playwright测试"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行增强版Playwright测试')
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit', 'all'], 
                        default='chromium', help='要使用的浏览器')
    parser.add_argument('--fingerprint', choices=list(BROWSER_FINGERPRINTS.keys()) + ['random', 'none'],
                        default='none', help='使用的浏览器指纹配置')
    parser.add_argument('--proxy', action='store_true', help='使用代理')
    parser.add_argument('--scenarios', nargs='+', help='要运行的测试场景名称')
    args = parser.parse_args()
    
    # 创建报告目录
    os.makedirs("playwright-report", exist_ok=True)
    
    # 初始化性能监控
    performance_monitor = PerformanceMonitor()
    
    # 开始时间
    start_time = time.time()
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 确定要测试的浏览器
    browsers_to_test = []
    if args.browser == 'all':
        browsers_to_test = ['chromium', 'firefox', 'webkit']
    else:
        browsers_to_test = [args.browser]
    
    # 确定要使用的指纹
    fingerprint_name = None
    if args.fingerprint == 'random':
        fingerprint_name = random.choice(list(BROWSER_FINGERPRINTS.keys()))
    elif args.fingerprint != 'none':
        fingerprint_name = args.fingerprint
    
    # 筛选测试场景
    scenarios_to_run = TEST_SCENARIOS
    if args.scenarios:
        scenarios_to_run = [s for s in TEST_SCENARIOS if s['name'] in args.scenarios]
    
    results = []
    
    # 启动浏览器并运行测试
    async with async_playwright() as p:
        for browser_name in browsers_to_test:
            logger.info(f"\n=== 在 {browser_name} 浏览器上运行测试 ===")
            
            try:
                # 设置浏览器上下文
                browser, context, page = await setup_browser_context(
                    p, browser_name, fingerprint_name, args.proxy
                )
                
                # 运行所有测试场景
                browser_results = []
                for scenario in scenarios_to_run:
                    try:
                        result = await run_test_scenario(page, scenario, performance_monitor)
                        result["browser"] = browser_name
                        browser_results.append(result)
                    except Exception as e:
                        logger.error(f"测试场景 '{scenario['name']}' 失败: {str(e)}")
                        browser_results.append({
                            "name": scenario['name'],
                            "browser": browser_name,
                            "error": str(e),
                            "success": False
                        })
                
                results.extend(browser_results)
                await browser.close()
                
            except Exception as e:
                logger.error(f"在 {browser_name} 上运行测试失败: {str(e)}")
                results.append({
                    "name": f"初始化 {browser_name} 浏览器",
                    "browser": browser_name,
                    "error": str(e),
                    "success": False
                })
    
    # 获取性能摘要
    performance_summary = performance_monitor.get_summary()
    
    # 生成HTML报告
    success_count = sum(1 for r in results if r.get("success", False))
    total_count = len(results)
    
    report_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>增强版 Playwright 测试报告</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; }}
            .summary {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .performance {{ background: #e9f7ef; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .success {{ color: green; }}
            .error {{ color: red; }}
            .scenario {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
            .browser-icon {{ font-size: 20px; margin-right: 5px; }}
            img {{ max-width: 800px; border: 1px solid #ddd; margin-top: 10px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .chart-container {{ height: 200px; margin: 20px 0; }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="header">
            <h1>增强版 Playwright 测试报告</h1>
            <div>
                <p>运行时间: {report_date}</p>
                <p>耗时: {performance_summary['duration']:.2f} 秒</p>
            </div>
        </div>
        
        <div class="summary">
            <h2>测试结果摘要</h2>
            <p class="{('success' if success_count == total_count else 'error')}">
                总共 {total_count} 项测试，通过 {success_count} 项，失败 {total_count - success_count} 项
            </p>
        </div>
        
        <div class="performance">
            <h2>性能指标</h2>
            <table>
                <tr>
                    <td>平均内存使用</td>
                    <td>{performance_summary['avg_memory_usage']:.2f} MB</td>
                </tr>
                <tr>
                    <td>最大内存使用</td>
                    <td>{performance_summary['max_memory_usage']:.2f} MB</td>
                </tr>
                <tr>
                    <td>平均CPU使用率</td>
                    <td>{performance_summary['avg_cpu_usage']:.2f}%</td>
                </tr>
                <tr>
                    <td>网络请求数</td>
                    <td>{performance_summary['network_requests']}</td>
                </tr>
                <tr>
                    <td>平均页面加载时间</td>
                    <td>{performance_summary['avg_page_load_time']:.2f} 秒</td>
                </tr>
            </table>
            
            <div class="chart-container">
                <canvas id="loadTimeChart"></canvas>
            </div>
        </div>
        
        <h2>详细测试结果</h2>
        <table>
            <tr>
                <th>浏览器</th>
                <th>测试场景</th>
                <th>结果</th>
                <th>加载时间</th>
            </tr>
    """
    
    load_times = []
    scenario_names = []
    
    for result in results:
        browser_icon = "🌐"
        if result["browser"] == "chromium":
            browser_icon = "🌐"
        elif result["browser"] == "firefox":
            browser_icon = "🦊"
        elif result["browser"] == "webkit":
            browser_icon = "🧭"
        
        status = "✅ 通过" if result.get("success", False) else f"❌ 失败: {result.get('error', '未知错误')}"
        status_class = "success" if result.get("success", False) else "error"
        
        load_time = result.get("load_time", 0)
        if result.get("success", False):
            load_times.append(load_time)
            scenario_names.append(f"{result['browser']} - {result['name']}")
        
        report_html += f"""
            <tr>
                <td>{browser_icon} {result["browser"]}</td>
                <td>{result["name"]}</td>
                <td class="{status_class}">{status}</td>
                <td>{load_time:.2f} 秒</td>
            </tr>
        """
    
    report_html += """
        </table>
        
        <h2>测试截图</h2>
    """
    
    for result in results:
        if result.get("success", False) and "screenshot" in result:
            data_section = ""
            if result.get("data_extracted"):
                data_section = "<h4>提取的数据</h4><ul>"
                for key, value in result["data_extracted"].items():
                    data_section += f"<li><strong>{key}:</strong> {value}</li>"
                data_section += "</ul>"
            
            report_html += f"""
            <div class="scenario">
                <h3>{result["browser"]} - {result["name"]}</h3>
                <p>页面标题: <strong>{result.get("title", "无标题")}</strong></p>
                <p>加载时间: <strong>{result.get("load_time", 0):.2f} 秒</strong></p>
                {data_section}
                <img src="{result['screenshot']}" alt="{result['name']} 截图">
            </div>
            """
    
    # 添加图表脚本
    report_html += f"""
        <script>
            // 页面加载时间图表
            const loadTimeCtx = document.getElementById('loadTimeChart').getContext('2d');
            const loadTimeChart = new Chart(loadTimeCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(scenario_names)},
                    datasets: [{{
                        label: '页面加载时间 (秒)',
                        data: {json.dumps(load_times)},
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: '时间 (秒)'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open("playwright-report/index.html", "w", encoding="utf-8") as f:
        f.write(report_html)
    
    # 保存结果和性能数据为JSON
    with open("playwright-report/results.json", "w", encoding="utf-8") as f:
        json.dump({
            "results": results,
            "performance": performance_summary
        }, f, indent=2)
    
    logger.info("\n测试报告已生成到 playwright-report/index.html")
    logger.info(f"总共 {total_count} 项测试，通过 {success_count} 项，失败 {total_count - success_count} 项")
    logger.info(f"性能摘要: 平均内存使用 {performance_summary['avg_memory_usage']:.2f} MB, " +
             f"平均页面加载时间 {performance_summary['avg_page_load_time']:.2f} 秒")
    
    # 返回成功或失败的退出代码
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
