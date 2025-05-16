#!/usr/bin/env python3
"""
增强版Playwright测试脚本
支持多浏览器测试和多个测试场景
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from playwright.async_api import async_playwright
import argparse

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
    }
]

async def run_test_scenario(page, scenario):
    """运行单个测试场景"""
    print(f"\n执行测试: {scenario['name']}")
    
    # 访问URL
    print(f"正在访问 {scenario['url']}...")
    await page.goto(scenario['url'])
    
    # 验证标题
    title = await page.title()
    print(f"页面标题: {title}")
    assert scenario['title_contains'] in title, f"页面标题不包含'{scenario['title_contains']}': {title}"
    
    # 执行操作
    for action in scenario['actions']:
        action_type = action['type']
        if action_type == "fill":
            await page.fill(action['selector'], action['value'])
            print(f"填写文本: {action['selector']} -> {action['value']}")
        elif action_type == "click":
            await page.click(action['selector'])
            print(f"点击元素: {action['selector']}")
        elif action_type == "wait_for_selector":
            await page.wait_for_selector(action['selector'])
            print(f"等待元素: {action['selector']}")
    
    # 截图
    screenshot_path = f"playwright-report/{scenario['name'].replace(' ', '_')}.png"
    await page.screenshot(path=screenshot_path)
    print(f"截图已保存到 {screenshot_path}")
    
    return {
        "name": scenario['name'],
        "title": title,
        "screenshot": os.path.basename(screenshot_path),
        "success": True
    }

async def main():
    """运行所有Playwright测试"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行Playwright测试')
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit', 'all'], 
                        default='chromium', help='要使用的浏览器')
    args = parser.parse_args()
    
    # 创建报告目录
    os.makedirs("playwright-report", exist_ok=True)
    
    # 开始时间
    start_time = time.time()
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 确定要测试的浏览器
    browsers_to_test = []
    if args.browser == 'all':
        browsers_to_test = ['chromium', 'firefox', 'webkit']
    else:
        browsers_to_test = [args.browser]
    
    results = []
    
    # 启动浏览器并运行测试
    async with async_playwright() as p:
        for browser_name in browsers_to_test:
            print(f"\n=== 在 {browser_name} 浏览器上运行测试 ===")
            
            try:
                # 获取浏览器启动器
                browser_launcher = getattr(p, browser_name)
                browser = await browser_launcher.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # 运行所有测试场景
                browser_results = []
                for scenario in TEST_SCENARIOS:
                    try:
                        result = await run_test_scenario(page, scenario)
                        result["browser"] = browser_name
                        browser_results.append(result)
                    except Exception as e:
                        print(f"测试场景 '{scenario['name']}' 失败: {str(e)}")
                        browser_results.append({
                            "name": scenario['name'],
                            "browser": browser_name,
                            "error": str(e),
                            "success": False
                        })
                
                results.extend(browser_results)
                await browser.close()
                
            except Exception as e:
                print(f"在 {browser_name} 上运行测试失败: {str(e)}")
                results.append({
                    "name": f"初始化 {browser_name} 浏览器",
                    "browser": browser_name,
                    "error": str(e),
                    "success": False
                })
    
    # 计算测试时间
    duration = time.time() - start_time
    
    # 生成HTML报告
    success_count = sum(1 for r in results if r.get("success", False))
    total_count = len(results)
    
    report_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Playwright 测试报告</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; }}
            .summary {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .success {{ color: green; }}
            .error {{ color: red; }}
            .scenario {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
            .browser-icon {{ font-size: 20px; margin-right: 5px; }}
            img {{ max-width: 800px; border: 1px solid #ddd; margin-top: 10px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Playwright 测试报告</h1>
            <div>
                <p>运行时间: {report_date}</p>
                <p>耗时: {duration:.2f} 秒</p>
            </div>
        </div>
        
        <div class="summary">
            <h2>测试结果摘要</h2>
            <p class="{('success' if success_count == total_count else 'error')}">
                总共 {total_count} 项测试，通过 {success_count} 项，失败 {total_count - success_count} 项
            </p>
        </div>
        
        <h2>详细测试结果</h2>
        <table>
            <tr>
                <th>浏览器</th>
                <th>测试场景</th>
                <th>结果</th>
            </tr>
    """
    
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
        
        report_html += f"""
            <tr>
                <td>{browser_icon} {result["browser"]}</td>
                <td>{result["name"]}</td>
                <td class="{status_class}">{status}</td>
            </tr>
        """
    
    report_html += """
        </table>
        
        <h2>测试截图</h2>
    """
    
    for result in results:
        if result.get("success", False) and "screenshot" in result:
            report_html += f"""
            <div class="scenario">
                <h3>{result["browser"]} - {result["name"]}</h3>
                <p>页面标题: <strong>{result.get("title", "无标题")}</strong></p>
                <img src="{result['screenshot']}" alt="{result['name']} 截图">
            </div>
            """
    
    report_html += """
    </body>
    </html>
    """
    
    with open("playwright-report/index.html", "w", encoding="utf-8") as f:
        f.write(report_html)
    
    print("\n测试报告已生成到 playwright-report/index.html")
    print(f"总共 {total_count} 项测试，通过 {success_count} 项，失败 {total_count - success_count} 项")
    
    # 返回成功或失败的退出代码
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 