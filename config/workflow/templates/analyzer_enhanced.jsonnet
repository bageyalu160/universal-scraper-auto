// 增强版分析工作流模板 - 使用utils.libsonnet工具库
// 完整对标analyzer.yml.template的所有功能

local params = import 'params.libsonnet';
local utils = import 'utils.libsonnet';

// 外部参数
local site_id = std.extVar('site_id');
local site_config = std.parseJson(std.extVar('site_config'));
local global_config = std.parseJson(std.extVar('global_config'));

// 动态参数计算
local site_name = utils.getSiteName(site_config, site_id);
local analysis_dir = if std.objectHas(global_config, 'general') && std.objectHas(global_config.general, 'analysis_dir') then
  global_config.general.analysis_dir
else
  'analysis';

{
  // 工作流基本信息
  name: site_name + ' AI分析任务',
  'run-name': '🧠 ' + site_name + '分析 #${{ github.run_number }} (${{ github.actor }} 触发)',
  
  // 复杂触发条件 - 使用工具库函数
  on: utils.buildTriggers(),
  
  // 全局设置 - 使用工具库函数
  env: utils.buildGlobalEnv(site_id, analysis_dir),
  permissions: utils.buildPermissions(),
  defaults: utils.buildDefaults(),
  concurrency: utils.buildConcurrency(site_id),
  
  // 多作业工作流 - 使用工具库函数
  jobs: utils.buildAnalyzerJobs(site_config, global_config)
} 