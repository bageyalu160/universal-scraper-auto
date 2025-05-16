import time
import random
import hashlib
import json
import urllib.parse
import os
import logging
import re
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('heimao_scraper')

def generate_signature(keyword="", page=1, page_size=10):
    """生成黑猫投诉API请求的签名参数"""
    c = str(int(time.time() * 1000))   # 13位时间戳
    a = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
    h = ''.join(random.choice(a) for i in range(16))   # 随机16个字符
    d = '$d6eb7ff91ee257475%'   # 默认值
    
    # 用于搜索投诉的参数
    page_size_str = str(page_size)  # 每页数量
    page_str = str(page)  # 页码
    
    ts = c
    rs = h
    
    # 构建签名参数 - 始终使用搜索接口格式
    # 即使没有关键词，也使用搜索接口，关键词为空字符串
    bb = [d, keyword or '', page_size_str, ts, page_str, rs]
    
    bb.sort()
    signature = hashlib.sha256((''.join(bb)).encode('utf-8')).hexdigest()
    
    return ts, rs, signature

def remove_html_tags(text):
    """移除HTML标签"""
    if not text:
        return text
    # 使用正则表达式移除HTML标签
    clean_text = re.sub(r'<[^>]+>', '', text)
    return clean_text

def get_complaints(keyword="", page=1, page_size=10, cookie=None, max_pages=5):
    """
    获取黑猫投诉数据，支持分页
    
    Args:
        keyword: 搜索关键词
        page: 页码，从1开始
        page_size: 每页数量
        cookie: 登录Cookie
        max_pages: 最大页数，防止过度请求
        
    Returns:
        dict: 结果字典，包含状态、数据等
    """
    import requests
    
    all_complaints = []
    total_pages = 1
    current_page = page
    
    while current_page <= total_pages and current_page <= max_pages:
        try:
            # 每次请求生成新的签名
            ts, rs, signature = generate_signature(keyword, current_page, page_size)
            logger.info(f"生成参数 - 页码: {current_page}, 时间戳: {ts}, 随机字符串: {rs}")
            
            # 设置请求头
            headers = {
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                "accept": "*/*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "sec-ch-ua": '"Chromium";v="136", "Not.A/Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-requested-with": "XMLHttpRequest"
            }
            
            # 如果传入了Cookie，添加到请求头
            if cookie:
                headers["cookie"] = cookie
            
            # 构建URL - 支持分页
            encoded_keyword = urllib.parse.quote(keyword) if keyword else ""
            base_url = f"https://tousu.sina.com.cn/api/index/s?ts={ts}&rs={rs}&signature={signature}&keywords={encoded_keyword}&page_size={page_size}&page={current_page}"
            
            # 添加referer头
            headers["referer"] = f"https://tousu.sina.com.cn/index/search/?keywords={encoded_keyword}&t=1"
            
            logger.info(f"请求URL(第{current_page}页): {base_url}")
            response = requests.request("GET", base_url, headers=headers)
            
            # 检查是否重定向到登录页面
            if "<!doctype html>" in response.text.lower() or "登录" in response.text or "微博" in response.text:
                if cookie:
                    logger.error("提供的Cookie无效或已过期")
                else:
                    logger.warning("未提供Cookie，搜索功能可能受限")
                
                # 由于现在始终使用搜索接口，如果没有Cookie或Cookie无效，API可能直接返回失败
                return {
                    'status': 'error',
                    'message': "需要登录Cookie才能使用搜索功能",
                    'data': all_complaints  # 返回已获取的数据
                }
            
            # 尝试解析JSON
            if response.text.strip():
                try:
                    result = json.loads(response.text)
                    logger.debug(f"API返回内容: {response.text[:200]}...")
                    
                    # 检查返回值结构
                    if 'result' not in result:
                        logger.error(f"API返回数据格式异常: {result}")
                        break
                    
                    # 处理结果
                    if result['result']['status']['code'] == 0:
                        # 获取分页信息
                        pager = result['result']['data'].get('pager', {})
                        total_pages = pager.get('page_amount', 1)
                        total_items = pager.get('item_count', 0)
                        
                        logger.info(f"当前第{current_page}页，总计{total_pages}页，共{total_items}条投诉")
                        
                        # 获取投诉列表
                        lists = result['result']['data'].get('lists', [])
                        all_complaints.extend(lists)
                        
                        logger.info(f"当前页获取 {len(lists)} 条投诉，累计 {len(all_complaints)} 条")
                        
                        # 检查是否有风控（频率限制）
                        if len(lists) == 0 and total_items > 0:
                            logger.warning("可能触发风控机制，暂停请求")
                            break
                        
                        # 翻页前休息一下，避免频率过高
                        if current_page < total_pages and current_page < max_pages:
                            sleep_time = random.uniform(1.5, 3.0)
                            logger.info(f"休息 {sleep_time:.2f} 秒后获取下一页")
                            time.sleep(sleep_time)
                    else:
                        logger.error(f"请求失败: {result}")
                        break
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {e}")
                    logger.debug(f"原始响应: {response.text[:200]}...")
                    break
            else:
                logger.error("响应内容为空")
                break
            
            # 更新页码
            current_page += 1
            
        except Exception as e:
            logger.exception(f"获取第{current_page}页时出错: {e}")
            break
    
    return {
        'status': 'success' if all_complaints else 'error',
        'count': len(all_complaints),
        'keyword': keyword if keyword else None,
        'pages_fetched': current_page - page,
        'total_pages': total_pages,
        'data': all_complaints
    }

def scrape_heimao(config, output_dir=None):
    """
    主爬虫函数，由框架调用
    
    Args:
        config: 配置信息字典
        output_dir: 输出目录
        
    Returns:
        dict: 包含爬取结果的字典
    """
    # 获取配置
    site_info = config.get('site_info', {})
    scraping = config.get('scraping', {})
    output_config = config.get('output', {})
    auth = config.get('auth', {})
    
    # 获取API配置
    api_config = scraping.get('api', {})
    page_size = api_config.get('page_size', 10)
    max_pages = api_config.get('max_pages', 5)
    
    # 获取Cookie
    cookie_env = auth.get('cookie_env')
    cookie = os.environ.get(cookie_env) if cookie_env else None
    
    # 创建输出目录（如果不存在）
    if not output_dir:
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.join('data', 'daily', today)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取目标配置
    targets = scraping.get('targets', [])
    
    # 存储所有结果
    all_results = []
    
    # 处理每个目标
    keywords = []
    default_search = True  # 是否执行默认搜索（不带关键词）
    
    # 收集所有关键词
    for target in targets:
        target_type = target.get('type')
        if target_type == 'latest':
            # 使用最新接口，实际上就是搜索接口不带关键词
            default_search = True
        elif target_type == 'keyword':
            # 处理关键词搜索
            keywords_env = target.get('keywords', [])[0]
            if keywords_env.startswith('${') and keywords_env.endswith('}'):
                # 从环境变量获取关键词
                env_name = keywords_env[2:-1]
                keywords_str = os.environ.get(env_name, '')
                keywords.extend([k.strip() for k in keywords_str.split(',') if k.strip()])
            else:
                keywords.extend([k for k in target.get('keywords', []) if k])
    
    # 如果没有指定关键词，但需要获取最新投诉，使用空关键词搜索
    if default_search and not keywords:
        result = get_complaints(page_size=page_size, max_pages=max_pages, cookie=cookie)
        if result and result.get('status') == 'success':
            logger.info(f"默认搜索获取到 {result.get('count')} 条投诉，共获取 {result.get('pages_fetched')} 页")
            all_results.extend(result.get('data', []))
    
    # 处理每个关键词搜索
    for keyword in keywords:
        if not keyword:
            continue
        logger.info(f"搜索关键词: {keyword}")
        result = get_complaints(keyword=keyword, page_size=page_size, max_pages=max_pages, cookie=cookie)
        if result and result.get('status') == 'success':
            logger.info(f"关键词'{keyword}'搜索结果: {result.get('count')} 条投诉，共获取 {result.get('pages_fetched')} 页")
            all_results.extend(result.get('data', []))
    
    # 添加调试日志
    logger.info(f"总共获取到 {len(all_results)} 条原始投诉数据")
    
    # 去重前打印所有结果的长度和第一项内容
    if all_results:
        logger.debug(f"第一条数据示例: {json.dumps(all_results[0], ensure_ascii=False)[:200]}")
    
    # 修改去重逻辑，确保适应当前数据结构
    unique_results = []
    seen_sns = set()  # 使用sn(投诉编号)作为去重依据
    
    for item in all_results:
        # 获取sn作为唯一标识
        sn = item.get('main', {}).get('sn')
        if sn and sn not in seen_sns:
            seen_sns.add(sn)
            unique_results.append(item)
    
    logger.info(f"去重后剩余 {len(unique_results)} 条投诉数据")
    
    # 格式化结果
    formatted_results = []
    for item in unique_results:
        try:
            main = item.get('main', {})
            
            # 获取ID - 使用sn作为ID
            item_id = main.get('sn')
            url = main.get('url', '')
            
            # 如果没有ID但有URL，尝试从URL提取
            if not item_id and url:
                match = re.search(r'/view/(\d+)/', url)
                if match:
                    item_id = match.group(1)
            
            # 移除HTML标签
            title = remove_html_tags(main.get('title', ''))
            company = remove_html_tags(main.get('cotitle', ''))
            content = remove_html_tags(main.get('summary', ''))
            
            # 转换时间戳
            timestamp = main.get('timestamp')
            if timestamp:
                try:
                    # 尝试将字符串时间戳转换为日期时间
                    formatted_timestamp = datetime.fromtimestamp(int(timestamp)).isoformat()
                except (ValueError, TypeError):
                    formatted_timestamp = timestamp
            else:
                formatted_timestamp = None
            
            formatted_results.append({
                'id': item_id,
                'title': title,
                'company': company,
                'content': content,
                'url': "https:" + url if url.startswith("//") else url,
                'timestamp': formatted_timestamp,
                'status': main.get('status'),
                'crawled_at': datetime.now().isoformat(),
                'issue': main.get('issue'),  # 问题类型
                'appeal': main.get('appeal'),  # 诉求
                'cost': main.get('cost')  # 消费金额
            })
        except Exception as e:
            logger.exception(f"处理数据项时出错: {e}")
            logger.error(f"问题数据: {item}")
    
    logger.info(f"格式化后得到 {len(formatted_results)} 条投诉数据")
    
    # 输出结果
    output_filename = output_config.get('filename', 'heimao_data.json')
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        if output_config.get('pretty_print', False):
            json.dump({'complaints': formatted_results}, f, ensure_ascii=False, indent=2)
        else:
            json.dump({'complaints': formatted_results}, f, ensure_ascii=False)
    
    logger.info(f"已保存 {len(formatted_results)} 条投诉数据到 {output_path}")
    
    return {
        'status': 'success',
        'count': len(formatted_results),
        'output_path': output_path
    }

if __name__ == "__main__":
    # 用于直接运行模块进行测试
    from pathlib import Path
    import yaml
    
    # 获取配置文件路径
    config_path = Path(__file__).parents[2] / 'config' / 'sites' / 'heimao.yaml'
    
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 运行爬虫
    result = scrape_heimao(config)
    print(json.dumps(result, ensure_ascii=False, indent=2)) 