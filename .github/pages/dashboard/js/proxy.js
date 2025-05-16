/**
 * 通用爬虫监控系统 - 代理管理JavaScript
 * 使用真实数据展示
 */

// 全局代理数据对象
let proxyData = {
    all: [],
    working: [],
    failed: {},
    last_update: ""
};

/**
 * 页面加载时初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    // 初始化代理管理页面
    initProxyManagement();
    
    // 设置定时刷新（每60秒）
    setInterval(refreshProxyStats, 60000);
    
    // 绑定按钮事件
    bindButtonEvents();
    
    // 绑定搜索事件
    bindSearchEvent();
    
    // 绑定分页事件
    bindPaginationEvents();
});

/**
 * 初始化代理管理页面
 */
async function initProxyManagement() {
    try {
        // 加载代理数据
        const response = await fetch("data/proxies.json");
        proxyData = await response.json();
        
        // 更新代理统计
        updateProxyStats();
        
        // 加载代理列表
        loadProxyList(1);
    } catch (error) {
        console.error("加载代理数据失败:", error);
        document.getElementById('proxy-table-body').innerHTML = 
            '<tr><td colspan="7" class="text-center">加载代理数据失败</td></tr>';
    }
}

/**
 * 更新代理统计信息
 */
function updateProxyStats() {
    // 计算统计数据
    const totalProxies = (proxyData.all && proxyData.all.length) || 0;
    const workingProxies = (proxyData.working && proxyData.working.length) || 0;
    
    document.getElementById('total-proxies').textContent = totalProxies;
    document.getElementById('working-proxies').textContent = workingProxies;
    
    // 计算可用率
    const availabilityRate = totalProxies > 0 ? Math.round((workingProxies / totalProxies) * 100) : 0;
    document.getElementById('proxy-availability').textContent = availabilityRate + '%';
    
    // 格式化更新时间
    if (proxyData.last_update) {
        const updateTime = new Date(proxyData.last_update);
        // 格式化为时:分
        const hours = updateTime.getHours().toString().padStart(2, '0');
        const minutes = updateTime.getMinutes().toString().padStart(2, '0');
        document.getElementById('proxy-update-time').textContent = `${hours}:${minutes}`;
        
        // 显示最后更新时间
        document.getElementById('last-update-time').textContent = 
            updateTime.toLocaleDateString() + ' ' + updateTime.toLocaleTimeString();
    } else {
        document.getElementById('proxy-update-time').textContent = "--:--";
        document.getElementById('last-update-time').textContent = "未更新";
    }
}

/**
 * 刷新代理统计信息
 */
async function refreshProxyStats() {
    try {
        // 重新加载代理数据
        const response = await fetch("data/proxies.json");
        proxyData = await response.json();
        
        // 更新统计信息
        updateProxyStats();
        
        // 重新加载代理列表
        const currentPage = getCurrentPage();
        loadProxyList(currentPage);
    } catch (error) {
        console.error("刷新代理数据失败:", error);
    }
}

/**
 * 获取当前页码
 * @returns {number} 当前页码
 */
function getCurrentPage() {
    const activePage = document.querySelector('#proxy-pagination .page-item.active .page-link');
    return activePage ? parseInt(activePage.getAttribute('data-page')) || 1 : 1;
}

/**
 * 加载代理列表
 * @param {number} page 页码
 * @param {string} searchTerm 搜索关键词
 */
function loadProxyList(page = 1, searchTerm = '') {
    const itemsPerPage = 10;
    const startIndex = (page - 1) * itemsPerPage;
    
    // 获取所有代理
    let allProxies = [];
    if (proxyData.all && Array.isArray(proxyData.all)) {
        // 转换为包含详细信息的代理列表
        allProxies = proxyData.all.map(proxy => {
            const isWorking = proxyData.working && proxyData.working.includes(proxy);
            const failCount = proxyData.failed && proxyData.failed[proxy] ? proxyData.failed[proxy] : 0;
            
            // 解析IP和端口
            let ip = proxy;
            let port = '';
            if (proxy.includes(':')) {
                [ip, port] = proxy.split(':');
            }
            
            return {
                id: proxy,
                ip: ip,
                port: port || '',
                status: isWorking ? 'working' : 'failed',
                responseTime: isWorking ? '300ms' : null, // 没有实际响应时间数据，使用默认值
                lastTested: proxyData.last_update || new Date().toISOString(),
                failCount: failCount
            };
        });
    }
    
    // 根据搜索条件过滤代理
    let filteredProxies = allProxies;
    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filteredProxies = filteredProxies.filter(proxy => 
            proxy.ip.includes(term) || (proxy.port && proxy.port.includes(term))
        );
    }
    
    // 获取当前页的代理
    const pageProxies = filteredProxies.slice(startIndex, startIndex + itemsPerPage);
    
    // 更新表格
    const tableBody = document.getElementById('proxy-table-body');
    tableBody.innerHTML = '';
    
    if (pageProxies.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">没有找到匹配的代理</td></tr>';
        return;
    }
    
    pageProxies.forEach(proxy => {
        const row = document.createElement('tr');
        
        // 根据状态设置行样式
        if (proxy.status === 'failed') {
            row.classList.add('table-danger');
        }
        
        // 格式化最后测试时间
        let lastTestedFormatted = "未测试";
        if (proxy.lastTested) {
            const lastTested = new Date(proxy.lastTested);
            lastTestedFormatted = lastTested.toLocaleDateString() + ' ' + lastTested.toLocaleTimeString();
        }
        
        row.innerHTML = `
            <td>${proxy.ip}</td>
            <td>${proxy.port}</td>
            <td>
                <span class="badge bg-${proxy.status === 'working' ? 'success' : 'danger'} status-badge">
                    ${proxy.status === 'working' ? '可用' : '失效'}
                </span>
            </td>
            <td>${proxy.responseTime || '-'}</td>
            <td>${lastTestedFormatted}</td>
            <td>${proxy.failCount}</td>
            <td>
                <button class="btn btn-sm btn-primary test-proxy-btn" data-proxy-id="${proxy.id}">测试</button>
                <button class="btn btn-sm btn-danger ms-1 delete-proxy-btn" data-proxy-id="${proxy.id}">删除</button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // 更新分页控件
    updatePagination(page, Math.ceil(filteredProxies.length / itemsPerPage), searchTerm);
    
    // 绑定测试和删除按钮事件
    bindProxyActionEvents();
}

/**
 * 更新分页控件
 * @param {number} currentPage 当前页码
 * @param {number} totalPages 总页数
 * @param {string} searchTerm 搜索关键词
 */
function updatePagination(currentPage, totalPages, searchTerm = '') {
    const pagination = document.getElementById('proxy-pagination');
    pagination.innerHTML = '';
    
    // 如果只有一页，不显示分页
    if (totalPages <= 1) {
        return;
    }
    
    // 上一页按钮
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    const prevLink = document.createElement('a');
    prevLink.className = 'page-link';
    prevLink.href = '#';
    prevLink.textContent = '上一页';
    prevLink.setAttribute('data-page', currentPage - 1);
    prevLink.setAttribute('data-search', searchTerm);
    prevLi.appendChild(prevLink);
    pagination.appendChild(prevLi);
    
    // 页码按钮
    const maxPageButtons = 5; // 最多显示5个页码按钮
    const halfMaxButtons = Math.floor(maxPageButtons / 2);
    
    let startPage = Math.max(1, currentPage - halfMaxButtons);
    let endPage = Math.min(totalPages, startPage + maxPageButtons - 1);
    
    // 调整startPage，确保显示maxPageButtons个按钮
    if (endPage - startPage + 1 < maxPageButtons) {
        startPage = Math.max(1, endPage - maxPageButtons + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageLi = document.createElement('li');
        pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
        const pageLink = document.createElement('a');
        pageLink.className = 'page-link';
        pageLink.href = '#';
        pageLink.textContent = i;
        pageLink.setAttribute('data-page', i);
        pageLink.setAttribute('data-search', searchTerm);
        pageLi.appendChild(pageLink);
        pagination.appendChild(pageLi);
    }
    
    // 下一页按钮
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    const nextLink = document.createElement('a');
    nextLink.className = 'page-link';
    nextLink.href = '#';
    nextLink.textContent = '下一页';
    nextLink.setAttribute('data-page', currentPage + 1);
    nextLink.setAttribute('data-search', searchTerm);
    nextLi.appendChild(nextLink);
    pagination.appendChild(nextLi);
}

/**
 * 绑定按钮事件
 */
function bindButtonEvents() {
    // 刷新代理池按钮
    document.getElementById('refresh-proxies-btn').addEventListener('click', function() {
        alert('正在刷新代理池数据...');
        refreshProxyStats();
    });
    
    // 测试所有代理按钮
    document.getElementById('test-proxies-btn').addEventListener('click', function() {
        alert('该功能需要后端支持，暂未实现');
    });
    
    // 导出代理列表按钮
    document.getElementById('export-proxies-btn').addEventListener('click', function() {
        if (!proxyData.all || proxyData.all.length === 0) {
            alert('当前没有可导出的代理');
            return;
        }
        
        // 生成CSV格式
        let csv = 'IP,Port,Status,FailCount\n';
        proxyData.all.forEach(proxy => {
            // 解析IP和端口
            let ip = proxy;
            let port = '';
            if (proxy.includes(':')) {
                [ip, port] = proxy.split(':');
            }
            
            const isWorking = proxyData.working && proxyData.working.includes(proxy);
            const failCount = proxyData.failed && proxyData.failed[proxy] ? proxyData.failed[proxy] : 0;
            
            csv += `${ip},${port},${isWorking ? 'working' : 'failed'},${failCount}\n`;
        });
        
        // 创建下载链接
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.setAttribute('href', url);
        a.setAttribute('download', `proxy_list_${new Date().toISOString().split('T')[0]}.csv`);
        a.click();
    });
    
    // 添加代理按钮
    document.getElementById('add-proxy-btn').addEventListener('click', function() {
        alert('该功能需要后端支持，暂未实现');
    });
}

/**
 * 绑定搜索事件
 */
function bindSearchEvent() {
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('search-proxy');
    
    searchBtn.addEventListener('click', function() {
        const searchTerm = searchInput.value.trim();
        loadProxyList(1, searchTerm);
    });
    
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const searchTerm = searchInput.value.trim();
            loadProxyList(1, searchTerm);
        }
    });
}

/**
 * 绑定分页事件
 */
function bindPaginationEvents() {
    document.getElementById('proxy-pagination').addEventListener('click', function(e) {
        if (e.target.classList.contains('page-link')) {
            e.preventDefault();
            
            // 获取页码和搜索词
            const page = parseInt(e.target.getAttribute('data-page'));
            const searchTerm = e.target.getAttribute('data-search') || '';
            
            // 加载对应页的代理
            loadProxyList(page, searchTerm);
        }
    });
}

/**
 * 绑定代理操作事件（测试和删除）
 */
function bindProxyActionEvents() {
    // 测试代理按钮
    document.querySelectorAll('.test-proxy-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            alert('该功能需要后端支持，暂未实现');
        });
    });
    
    // 删除代理按钮
    document.querySelectorAll('.delete-proxy-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            alert('该功能需要后端支持，暂未实现');
        });
    });
} 