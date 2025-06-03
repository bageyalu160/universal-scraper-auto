// 分析工作流模板 - Jsonnet版本 (增强版)

local params = import 'params.libsonnet';
local utils = import 'utils.libsonnet';

// 外部参数
local site_id = std.extVar('site_id');
local site_config = std.parseJson(std.extVar('site_config'));
local global_config = std.parseJson(std.extVar('global_config'));

// 站点信息
local site_name = utils.getSiteName(site_config, site_id);

// 分析配置
local analysis_config = utils.getConfigSection(site_config, 'analysis', {});

// 确定AI提供商
local ai_provider = utils.getConfigValue(analysis_config, 'provider', 'openai');

// 确定依赖项
local dependencies = utils.getAnalyzerDependencies(ai_provider, params.dependencies);

// 缓存配置
local cache_config = utils.generateCacheConfig('analyzer', site_id, ai_provider);

// 超时设置
local analyze_timeout = utils.getJobTimeout('analyze', global_config);

// 错误处理策略
local analyze_error_strategy = utils.getErrorHandlingStrategy('analyze', global_config);

// 确定提示词模板
local prompt_template = utils.getConfigValue(analysis_config, 'prompt_template', 'default');

// 环境变量
local workflow_env = utils.generateWorkflowEnv('analyzer', global_config);

{
  name: site_name + ' (' + site_id + ') 数据分析',
  'run-name': '🧠 ' + site_name + ' (' + site_id + ') 数据分析 #${{ github.run_number }} (${{ github.actor }})',
  
  // 定义工作流的权限
  permissions: {
    contents: 'write',  // 允许推送到仓库
    actions: 'write'    // 允许触发其他工作流
  },
  
  on: utils.generateWorkflowDispatchTrigger({
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
      type: 'string'
    },
    model: {
      description: 'AI模型',
      required: false,
      type: 'string',
      default: ai_model
    },
    parent_workflow_id: {
      description: '父工作流ID(由主工作流触发时使用)',
      required: false,
      type: 'string'
    },
    retry: {
      description: '是否为重试执行',
      required: false,
      type: 'boolean',
      default: false
    }
  }),
  
  // 全局环境变量
  env: workflow_env,
  
  jobs: {
    analyze: {
      name: '分析数据',
      'runs-on': params.runtime.runner,
      'timeout-minutes': analyze_timeout,
      'continue-on-error': analyze_error_strategy['continue-on-error'],
      steps: [
        utils.generateCheckoutStep(),
        utils.generateStartTimeStep(),
        utils.generatePythonSetupStep(params.runtime.python_version, true),
        utils.generateCacheStep(cache_config, '**/requirements.txt, config/sites/' + site_id + '.yaml'),
        utils.generateRetryableStep('安装依赖', 'pip install ' + std.join(' ', dependencies), 3, 10),
        utils.generateDirectorySetupStep(['analysis/' + site_id, 'analysis/' + site_id + '/cache']),
        {
          name: '准备分析环境',
          id: 'prepare_analysis',
          env: {
            OPENAI_API_KEY: '${{ secrets.OPENAI_API_KEY }}',
            GEMINI_API_KEY: '${{ secrets.GEMINI_API_KEY }}',
            ANTHROPIC_API_KEY: '${{ secrets.ANTHROPIC_API_KEY }}'
          },
          run: |||
            # 设置分析输出路径
            echo "analysis_output=analysis/${{ github.event.inputs.site_id }}/${{ github.event.inputs.site_id }}_${{ github.event.inputs.data_date }}_analysis.json" >> $GITHUB_OUTPUT
            echo "analysis_success=false" >> $GITHUB_OUTPUT
          |||
        },
        utils.generateRetryableStep('运行分析', |||
          python scripts/ai_analyzer.py \
            --site ${{ github.event.inputs.site_id }} \
            --date "${{ github.event.inputs.data_date }}" \
            --input ${{ github.event.inputs.data_file }} \
            --output analysis/${{ github.event.inputs.site_id }}/${{ github.event.inputs.site_id }}_${{ github.event.inputs.data_date }}_analysis.json \
            --prompt-template %(prompt_template)s \
            --provider %(ai_provider)s
            
          # 检查结果
          if [ -f "analysis/${{ github.event.inputs.site_id }}/${{ github.event.inputs.site_id }}_${{ github.event.inputs.data_date }}_analysis.json" ]; then
            echo "✅ 分析成功完成"
          else
            echo "❌ 分析失败或无结果"
            exit 1
          fi
        ||| % {
          prompt_template: prompt_template,
          ai_provider: ai_provider
        }, 3, 30),
        {
          name: '检查分析结果',
          id: 'check_analysis_result',
          'if': "always()",
          run: |||
            if [ -f "analysis/${{ github.event.inputs.site_id }}/${{ github.event.inputs.site_id }}_${{ github.event.inputs.data_date }}_analysis.json" ]; then
              echo "analysis_success=true" >> $GITHUB_OUTPUT
              echo "✅ 分析成功完成"
            else
              echo "analysis_success=false" >> $GITHUB_OUTPUT
              echo "❌ 分析失败或无结果"
            fi
          |||
        },
        {
          name: '上传分析结果',
          'if': "steps.check_analysis_result.outputs.analysis_success == 'true'",
          uses: 'actions/upload-artifact@v4',
          with: {
            name: '${{ github.event.inputs.site_id }}-analysis-${{ github.event.inputs.data_date }}',
            path: 'analysis/${{ github.event.inputs.site_id }}/${{ github.event.inputs.site_id }}_${{ github.event.inputs.data_date }}_analysis.json',
            'retention-days': 7,
            'if-no-files-found': 'warn'
          }
        },
        {
          name: '配置Git并提交分析结果',
          run: |
            # 配置Git
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

            # 添加文件
            git add analysis/%(site_id)s/

            # 拉取远程更改，避免推送冲突
            git pull --rebase origin main || echo "拉取远程仓库失败，尝试继续提交"

            # 提交更改
            if git diff --staged --quiet; then
              echo "没有变更需要提交"
            else
              git commit -m "🥸 自动更新: %(site_name)s分析结果 (${{ github.event.inputs.data_date }})"
              git push
              echo "✅ 成功提交并推送分析结果"
            fi
          ||| % {site_id: site_id, site_name: site_name}
        },
        // 添加工作流状态报告
        utils.generateWorkflowStatusStep('analyzer', site_id),
        // 添加执行指标收集
        utils.generateMetricsCollectionStep('analyzer', site_id),
        // 添加智能调度分析
        utils.generateSmartSchedulingStep('analyzer', site_id),
        // 应用智能调度
        utils.generateApplyScheduleStep('analyzer', site_id)
      ]
    }
  }
}
