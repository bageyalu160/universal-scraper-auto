// 工作流参数库
// 从统一的settings.yaml配置文件中读取配置，避免重复定义

local settings = std.parseYaml(importstr '../../settings.yaml');

{
  // 基础运行环境配置
  runtime: settings.runtime,

  // GitHub Actions 配置
  github_actions: settings.github_actions,

  // 调度配置
  schedules: settings.schedules,

  // 路径配置
  paths: settings.paths,

  // 脚本配置
  scripts: settings.scripts,

  // 依赖项配置
  dependencies: settings.dependencies,

  // 环境变量配置
  environment_variables: settings.environment_variables,

  // 分析配置
  analysis: settings.analysis,

  // 通知配置
  notification: settings.notification,

  // 代理池配置
  proxy_pool: settings.proxy_pool,

  // 高级配置
  advanced: settings.advanced,

  // 项目信息
  project: settings.project,

  // AI Issue摘要工作流参数
  ai_issue_summary: {
    permissions: settings.github_actions.permissions.ai,
    
    // 默认配置
    defaults: {
      language: 'zh-CN',
      style: 'professional',
      include_labels: true,
      auto_assign: false
    },
    
    // 标签检测关键词
    label_keywords: {
      bug: ['error', 'fail', 'crash', '错误', '失败', '崩溃', 'bug', '异常', '超时', '无法访问'],
      enhancement: ['feature', 'enhancement', 'improve', '功能', '改进', '增强', '优化', '新增', '扩展'],
      scraper: ['scraper', 'crawler', 'parse', '爬虫', '抓取', '解析', '数据采集'],
      data: ['数据', 'data', '分析', 'analysis', '统计', '报告', '可视化'],
      urgent: ['urgent', 'critical', 'blocking', '紧急', '严重', '阻塞', '生产环境', '数据丢失'],
      config: ['配置', 'config', '设置', '参数', '环境', '部署']
    }
  },

  // 工具函数：获取依赖项字符串
  getDependencies(type, engine=null):: 
    if engine != null && std.objectHas($.dependencies[type], engine) then
      std.join(' ', $.dependencies[type][engine])
    else if std.type($.dependencies[type]) == 'array' then
      std.join(' ', $.dependencies[type])
    else if std.objectHas($.dependencies[type], 'requests') then
      std.join(' ', $.dependencies[type].requests)
    else
      '',

  // 工具函数：构建依赖项安装命令
  buildInstallCommand(type, engine=null):: 
    local deps = $.getDependencies(type, engine);
    local base_deps = std.join(' ', $.dependencies.base);
    
    if deps != '' then
      'pip install ' + base_deps + ' ' + deps
    else
      'pip install ' + base_deps,

  // 工具函数：获取环境变量配置
  getEnvVars(category)::
    if std.objectHas($.environment_variables, category) then
      $.environment_variables[category]
    else
      {},

  // 工具函数：构建并发控制配置
  buildConcurrency(workflow_name)::
    local concurrency_config = $.github_actions.concurrency;
    if concurrency_config.enabled then
      {
        group: concurrency_config.group_prefix + '-' + workflow_name + '-${{ github.ref }}',
        'cancel-in-progress': concurrency_config.cancel_in_progress
      }
    else
      null,

  // 工具函数：构建权限配置
  buildPermissions(type='standard')::
    if std.objectHas($.github_actions.permissions, type) then
      $.github_actions.permissions[type]
    else
      $.github_actions.permissions.standard,

  // 工具函数：构建工件配置
  buildArtifactConfig(type='data')::
    {
      'retention-days': if std.objectHas($.github_actions.artifacts.retention, type) then
        $.github_actions.artifacts.retention[type]
      else
        $.github_actions.artifacts.default_retention_days
    },

  // 工具函数：获取Action版本
  getAction(name)::
    if std.objectHas($.github_actions.actions, name) then
      $.github_actions.actions[name]
    else
      error 'Unknown action: ' + name,

  // 工具函数：构建通知环境变量
  buildNotificationEnv()::
    local notification_env = $.environment_variables.notification;
    {
      [notification_env.dingtalk.webhook]: '${{ secrets.' + notification_env.dingtalk.webhook + ' }}',
      [notification_env.feishu.webhook]: '${{ secrets.' + notification_env.feishu.webhook + ' }}',
      [notification_env.wechat.webhook]: '${{ secrets.' + notification_env.wechat.webhook + ' }}'
    }
}
