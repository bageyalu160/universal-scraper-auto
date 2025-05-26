// 分析工作流模板 - Jsonnet版本

local params = import 'params.libsonnet';

// 外部参数
local site_id = std.extVar('site_id');
local site_config = std.parseJson(std.extVar('site_config'));
local global_config = std.parseJson(std.extVar('global_config'));

// 站点信息
local site_name = if std.objectHas(site_config, 'site_info') && std.objectHas(site_config.site_info, 'name') then
  site_config.site_info.name
else
  site_id + ' 站点';

// 分析配置
local analysis_config = if std.objectHas(site_config, 'analysis') then
  site_config.analysis
else
  {};

// 确定AI提供商
local ai_provider = if std.objectHas(analysis_config, 'provider') then
  analysis_config.provider
else
  'openai';

// 确定依赖项
local dependencies = if std.objectHas(params, 'dependencies') && std.objectHas(params.dependencies, 'analyzer') then
  std.join(' ', params.dependencies.analyzer)
else
  'pandas>=2.0.3 openai>=1.0.0 google-generativeai>=0.3.1 numpy>=1.22.0';

// 确定提示词模板
local prompt_template = if std.objectHas(analysis_config, 'prompt_template') then
  analysis_config.prompt_template
else
  'default';

// 环境变量
local openai_vars = if ai_provider == 'openai' then [{
  name: 'OPENAI_API_KEY',
  secret: 'OPENAI_API_KEY'
}] else [];

// Gemini API密钥
local gemini_vars = if ai_provider == 'gemini' then [{
  name: 'GEMINI_API_KEY',
  secret: 'GEMINI_API_KEY'
}] else [];

// 合并环境变量
local env_vars = openai_vars + gemini_vars;

{
  name: site_name + ' 数据分析',
  'run-name': '🧠 ' + site_name + ' 数据分析 #${{ github.run_number }} (${{ github.actor }})',
  
  on: {
    workflow_dispatch: {
      inputs: {
        data_date: {
          description: '数据日期',
          required: true,
          type: 'string'
        },
        data_file: {
          description: '数据文件路径',
          required: true,
          type: 'string'
        },
        site_id: {
          description: '站点ID',
          required: true,
          type: 'string',
          default: site_id
        }
      }
    }
  },
  
  jobs: {
    analyze: {
      name: '分析数据',
      'runs-on': params.runtime.runner,
      steps: [
        {
          name: '检出代码',
          uses: 'actions/checkout@v4'
        },
        {
          name: '设置Python',
          uses: 'actions/setup-python@v4',
          with: {
            'python-version': params.runtime.python_version,
            cache: 'pip'
          }
        },
        {
          name: '安装依赖',
          run: 'pip install ' + dependencies
        },
        {
          name: '创建输出目录',
          run: |||
            mkdir -p analysis/%(site_id)s
          ||| % {site_id: site_id}
        },
        {
          name: '运行分析',
          env: {
            [env_var.name]: '${{ secrets.' + env_var.secret + ' }}'
            for env_var in env_vars
          },
          run: |||
            python scripts/ai_analyzer.py \
              --site "${{ github.event.inputs.site_id }}" \
              --date "${{ github.event.inputs.data_date }}" \
              --input "${{ github.event.inputs.data_file }}" \
              --output "analysis/${{ github.event.inputs.site_id }}/${{ github.event.inputs.site_id }}_${{ github.event.inputs.data_date }}_analysis.json" \
              --prompt-template "%(prompt_template)s" \
              --provider "%(ai_provider)s"
          ||| % {
            prompt_template: prompt_template,
            ai_provider: ai_provider
          }
        },
        {
          name: '上传分析结果',
          uses: 'actions/upload-artifact@v3',
          with: {
            name: '${{ github.event.inputs.site_id }}-analysis-${{ github.event.inputs.data_date }}',
            path: 'analysis/${{ github.event.inputs.site_id }}/${{ github.event.inputs.site_id }}_${{ github.event.inputs.data_date }}_analysis.json',
            'retention-days': 7
          }
        }
      ]
    }
  }
}
