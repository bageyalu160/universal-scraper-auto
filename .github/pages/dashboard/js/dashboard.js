/**
 * 通用爬虫监控系统 - 仪表盘JavaScript
 * 使用真实数据展示
 */

// 页面加载时初始化仪表盘
document.addEventListener('DOMContentLoaded', function() {
    // 初始化仪表盘
    initDashboard();
    
    // 设置定时刷新（每60秒）
    setInterval(refreshDashboard, 60000);
    
    // 绑定导航切换事件
    document.getElementById('proxy-tab').addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = "proxy.html";
    });
});

/**
 * 初始化仪表盘数据和图表
 */
async function initDashboard() {
    try {
        // 加载状态数据
        const statusResponse = await fetch("data/status.json");
        const statusData = await statusResponse.json();
        
        // 加载任务数据
        const tasksResponse = await fetch("data/tasks.json");
        const tasksData = await tasksResponse.json();
        
        // 加载代理数据
        const proxyResponse = await fetch("data/proxies.json");
        const proxyData = await proxyResponse.json();
        
        // 加载数据统计
        const statsResponse = await fetch("data/data_stats.json");
        const dataStats = await statsResponse.json();
        
        // 更新统计数据
        updateStats(statusData);
        
        // 更新任务表格
        updateTaskTable(tasksData.tasks);
        
        // 更新代理池状态
        updateProxyStatus(proxyData);
        
        // 更新数据统计图表
        initDataChart(dataStats);
        
        // 更新最新日志
        updateRecentLogs();
    } catch (error) {
        console.error("加载仪表盘数据失败:", error);
    }
}

/**
 * 刷新仪表盘数据
 */
async function refreshDashboard() {
    try {
        // 加载最新状态数据
        const statusResponse = await fetch("data/status.json");
        const statusData = await statusResponse.json();
        
        // 更新统计数据
        updateStats(statusData);
        
        // 刷新任务表格
        const tasksResponse = await fetch("data/tasks.json");
        const tasksData = await tasksResponse.json();
        updateTaskTable(tasksData.tasks);
        
    } catch (error) {
        console.error("刷新仪表盘数据失败:", error);
    }
}

/**
 * 更新统计数据
 * @param {Object} statusData 状态数据
 */
function updateStats(statusData) {
    if (!statusData) return;
    
    document.getElementById('active-crawlers').textContent = statusData.activeCrawlers || 0;
    document.getElementById('available-proxies').textContent = statusData.availableProxies || 0;
    document.getElementById('success-rate').textContent = (statusData.successRate || 0) + '%';
    document.getElementById('data-count').textContent = (statusData.dataCount || 0).toLocaleString();
    
    // 格式化最后更新时间
    if (statusData.lastUpdate) {
        const lastUpdate = new Date(statusData.lastUpdate);
        document.getElementById('last-update-time').textContent = 
            lastUpdate.toLocaleDateString() + ' ' + lastUpdate.toLocaleTimeString();
    } else {
        document.getElementById('last-update-time').textContent = "未更新";
    }
}

/**
 * 更新任务表格
 * @param {Array} tasks 任务数据
 */
function updateTaskTable(tasks) {
    const tableBody = document.getElementById('task-table-body');
    tableBody.innerHTML = '';
    
    if (!tasks || tasks.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center">暂无任务数据</td></tr>';
        return;
    }
    
    tasks.forEach(task => {
        const row = document.createElement('tr');
        
        // 格式化最后运行时间
        let lastRunFormatted = "未运行";
        if (task.endTime) {
            const lastRun = new Date(task.endTime);
            lastRunFormatted = lastRun.toLocaleDateString() + ' ' + lastRun.toLocaleTimeString();
        }
        
        // 获取任务状态颜色
        const statusColor = getStatusColor(task.status);
        
        row.innerHTML = `
            <td>${task.name || task.id || '未命名任务'}</td>
            <td>${task.site || '-'}</td>
            <td><span class="badge bg-${statusColor} status-badge">${task.status || '未知'}</span></td>
            <td>${lastRunFormatted}</td>
            <td>${task.result && task.result.count ? task.result.count.toLocaleString() : '-'}</td>
        `;
        
        tableBody.appendChild(row);
    });
}

/**
 * 获取任务状态对应的颜色
 * @param {string} status 任务状态
 * @returns {string} 对应的Bootstrap颜色类
 */
function getStatusColor(status) {
    const statusColors = {
        'success': 'success',
        'failed': 'danger',
        'running': 'primary',
        'active': 'success',
        'scheduled': 'primary',
        'completed': 'secondary',
        'paused': 'warning'
    };
    
    return statusColors[status] || 'secondary';
}

/**
 * 更新代理池状态
 * @param {Object} proxyData 代理数据
 */
function updateProxyStatus(proxyData) {
    if (!proxyData) return;
    
    // 计算统计数据
    const totalProxies = (proxyData.all && proxyData.all.length) || 0;
    const workingProxies = (proxyData.working && proxyData.working.length) || 0;
    
    document.getElementById('total-proxies').textContent = totalProxies;
    
    // 计算并显示可用率
    const availabilityRate = totalProxies > 0 ? Math.round((workingProxies / totalProxies) * 100) : 0;
    document.getElementById('proxy-availability').textContent = availabilityRate + '%';
    
    // 格式化更新时间
    if (proxyData.last_update) {
        const updateTime = new Date(proxyData.last_update);
        document.getElementById('proxy-update-time').textContent = 
            updateTime.toLocaleDateString() + ' ' + updateTime.toLocaleTimeString();
    } else {
        document.getElementById('proxy-update-time').textContent = "未更新";
    }
    
    // 绘制代理饼图
    const ctx = document.getElementById('proxy-chart').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['可用代理', '失效代理'],
            datasets: [{
                data: [workingProxies, totalProxies - workingProxies],
                backgroundColor: ['#28a745', '#dc3545'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

/**
 * 初始化数据统计图表
 * @param {Object} dataStats 数据统计
 */
function initDataChart(dataStats) {
    if (!dataStats || !dataStats.dates || !dataStats.counts) {
        console.error("数据统计格式不正确");
        return;
    }
    
    const ctx = document.getElementById('data-chart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dataStats.dates,
            datasets: [{
                label: '采集数据量',
                data: dataStats.counts,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * 更新最新日志
 */
function updateRecentLogs() {
    // 目前没有实时日志数据，使用固定的提示
    const logsContainer = document.getElementById('recent-logs');
    logsContainer.innerHTML = '<div class="text-center">日志查看功能即将上线</div>';
    
    // 在将来可以通过API获取最新日志
    // fetch("data/logs/recent.json")
    //     .then(response => response.json())
    //     .then(logs => {
    //         // 处理日志数据
    //     })
    //     .catch(error => {
    //         console.error("获取日志数据失败:", error);
    //     });
} 