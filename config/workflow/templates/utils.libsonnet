{
  // Jsonnet工具库 - 为增强版工作流模板提供通用函数
  
  // 获取站点名称
  getSiteName(site_config, site_id)::
    if std.objectHas(site_config, 'site_info') && std.objectHas(site_config.site_info, 'name') then
      site_config.site_info.name
    else if std.objectHas(site_config, 'site') && std.objectHas(site_config.site, 'name') then
      site_config.site.name
    else
      site_id,
  
  // 获取配置部分，如果不存在则返回默认值
  getConfigSection(config, section_name, default_value={})::  
    if std.objectHas(config, section_name) then
      config[section_name]
    else
      default_value,

  // 获取配置值，支持嵌套路径（如 "scraping.engine"）
  getConfigValue(config, path, default_value)::  
    local parts = std.split(path, '.');
    local navigate(obj, idx) =
      if idx >= std.length(parts) then obj
      else if std.objectHas(obj, parts[idx]) then navigate(obj[parts[idx]], idx + 1)
      else default_value;
    navigate(config, 0),

  // 获取分析配置
  getAnalysisConfig(site_config)::
    $.getConfigSection(site_config, 'analysis', {}),
  
  // 获取输出扩展名
  getOutputExtension(analysis_config)::
    if std.objectHas(analysis_config, 'output_format') then
      if analysis_config.output_format == 'json' then 'json'
      else if analysis_config.output_format == 'tsv' then 'tsv'
      else if analysis_config.output_format == 'csv' then 'csv'
      else 'json'
    else
      'tsv',
  
  // 根据引擎类型获取爬虫依赖项
  getCrawlerDependencies(engine_type, dependencies_config)::  
    if engine_type == 'firecrawl' then
      dependencies_config.crawler.firecrawl
    else if engine_type == 'playwright' then
      dependencies_config.crawler.playwright
    else if engine_type == 'selenium' then
      dependencies_config.crawler.selenium
    else
      dependencies_config.crawler.requests,

  // 根据AI提供商获取分析器依赖项
  getAnalyzerDependencies(ai_provider, dependencies_config)::  
    dependencies_config.analyzer + 
    if ai_provider == 'openai' then
      ['openai>=1.0.0']
    else if ai_provider == 'gemini' then
      ['google-generativeai>=0.3.1']
    else
      [],

  // 获取环境变量配置
  getEnvironmentVariables(analysis_config, global_config):: [
    { name: 'OPENAI_API_KEY', secret: 'OPENAI_API_KEY' },
    { name: 'GEMINI_API_KEY', secret: 'GEMINI_API_KEY' },
    { name: 'ANTHROPIC_API_KEY', secret: 'ANTHROPIC_API_KEY' }
  ],
  
  // 获取作业超时设置
  getJobTimeout(job_type, global_config)::  
    local base_timeout = if std.objectHas(global_config, 'runtime') && std.objectHas(global_config.runtime, 'timeout_minutes') 
                       then global_config.runtime.timeout_minutes 
                       else 30;
    
    // 根据作业类型返回适当的超时时间
    if job_type == 'setup' then std.ceil(base_timeout / 3)
    else if job_type == 'crawl' then std.ceil(base_timeout * 2)
    else if job_type == 'analyze' then base_timeout
    else if job_type == 'proxy_pool' then std.ceil(base_timeout / 1.5)
    else if job_type == 'dashboard' then std.ceil(base_timeout / 2)
    else base_timeout,
  
  // 获取错误处理策略
  getErrorHandlingStrategy(step_type, global_config)::  
    // 默认策略
    local default_strategy = {
      'continue-on-error': false,
      'fail-fast': true
    };
    
    // 可以容忍错误的步骤类型
    local tolerant_steps = [
      'crawl', 'analyze', 'notification', 'proxy_validation', 'data_processing'
    ];
    
    // 如果是可容错步骤，则允许继续执行
    if std.member(tolerant_steps, step_type) then
      default_strategy + { 'continue-on-error': true, 'fail-fast': false }
    else
      default_strategy,
  
  // 生成缓存配置
  generateCacheConfig(workflow_type, id, engine='')::  
    local prefix = workflow_type + '-deps-' + id;
    local key_prefix = if engine != '' then prefix + '-' + engine else prefix;
    local paths = ['~/.cache/pip'];
    
    if workflow_type == 'crawler' then
      {
        enabled: true,
        key_prefix: key_prefix,
        paths: paths + ['data/' + id + '/cache']
      }
    else if workflow_type == 'analyzer' then
      {
        enabled: true,
        key_prefix: key_prefix,
        paths: paths + ['analysis/' + id + '/cache']
      }
    else if workflow_type == 'proxy_pool' then
      {
        enabled: true,
        key_prefix: key_prefix,
        paths: paths + ['proxy_pool/cache']
      }
    else if workflow_type == 'dashboard' then
      {
        enabled: true,
        key_prefix: key_prefix,
        paths: paths + ['dashboard/cache']
      }
    else
      {
        enabled: true,
        key_prefix: key_prefix,
        paths: paths
      },

  // 生成工作流环境变量
  generateWorkflowEnv(workflow_type, global_config)::  
    // 基础环境变量
    local paths = if std.objectHas(global_config, 'paths') then global_config.paths else {
      config: 'config',
      config_sites: 'config/sites',
      data_daily: 'data/daily',
      status: 'status',
      logs: 'logs'
    };
    
    local base_env = {
      CONFIG_DIR: paths.config,
      SITES_DIR: paths.config_sites,
      DATA_DIR: paths.data_daily,
      STATUS_DIR: paths.status,
      LOGS_DIR: paths.logs,
      PYTHONUNBUFFERED: '1',
      WORKFLOW_TYPE: workflow_type
    };
    
    // 根据工作流类型添加特定环境变量
    local analysis = if std.objectHas(global_config, 'analysis') then global_config.analysis else {
      provider: 'gemini',
      prompt_dir: 'config/analysis/prompts'
    };
    
    local specific_env = 
      if workflow_type == 'analyzer' then {
        AI_PROVIDER: analysis.provider,
        PROMPT_DIR: analysis.prompt_dir
      }
      else if workflow_type == 'crawler' then {
        PROXY_ENABLED: std.toString(global_config.proxy.enabled)
      }
      else if workflow_type == 'proxy_pool' then {
        PROXY_TIMEOUT: std.toString(30)
      }
      else {};
    
    base_env + specific_env,
  
  // 生成检出代码步骤
  generateCheckoutStep(fetch_depth=1)::  
    {
      name: '检出代码',
      uses: 'actions/checkout@v4',
      [if fetch_depth != 1 then 'with']: {
        'fetch-depth': fetch_depth
      }
    },

  // 生成设置Python步骤
  generatePythonSetupStep(python_version, cache_pip=true)::  
    {
      name: '设置Python',
      uses: 'actions/setup-python@v5',
      with: {
        'python-version': python_version,
        cache: if cache_pip then 'pip' else null
      }
    },

  // 生成缓存步骤
  generateCacheStep(cache_config, hashfiles_pattern)::  
    {
      name: '缓存依赖和数据',
      [if cache_config.enabled then 'if']: 'true',
      uses: 'actions/cache@v3',
      with: {
        path: std.join('\n', cache_config.paths),
        key: cache_config.key_prefix + '-${{ hashFiles(\'' + hashfiles_pattern + '\') }}',
        'restore-keys': cache_config.key_prefix + '-'
      }
    },

  // 生成创建目录步骤
  generateDirectorySetupStep(directories)::  
    {
      name: '创建必要目录',
      run: std.join('\n', ['mkdir -p ' + dir for dir in directories])
    },

  // 构建触发条件
  buildTriggers():: {
    workflow_dispatch: {
      inputs: {
        data_date: {
          description: '数据日期 (YYYY-MM-DD格式)',
          required: true,
          type: 'string'
        },
        data_file: {
          description: '要分析的数据文件路径',
          required: true,
          type: 'string'
        },
        site_id: {
          description: '网站ID',
          required: true,
          type: 'string'
        },
        model: {
          description: 'AI模型选择',
          required: false,
          type: 'choice',
          default: 'default',
          options: ['default', 'gemini-1.5-pro', 'gpt-4-turbo', 'claude-3-sonnet']
        }
      }
    },
    repository_dispatch: {
      types: ['crawler_completed']
    },
    workflow_call: {
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
          description: '网站ID',
          required: true,
          type: 'string'
        }
      },
      secrets: {
        API_KEY: {
          required: false
        }
      }
    }
  },
  
  // 构建全局环境变量
  buildGlobalEnv(site_id, analysis_dir):: {
    PYTHON_VERSION: '3.10',
    ANALYSIS_DIR: analysis_dir + '/daily',
    SITE_ID: site_id,
    TZ: 'Asia/Shanghai'
  },
  
  // 构建权限设置
  buildPermissions():: {
    contents: 'write',
    actions: 'write'
  },
  
  // 构建默认配置
  buildDefaults():: {
    run: {
      shell: 'bash'
    }
  },
  
  // 生成Git提交步骤
  generateGitCommitStep(paths_to_add, commit_message)::  
    local paths_array = if std.type(paths_to_add) == 'array' then paths_to_add else [paths_to_add];
    {
      name: '提交更改',
      run: |||
        # 配置Git
        git config user.name "github-actions[bot]"
        git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

        # 添加文件
        %(add_commands)s

        # 拉取远程更改，避免推送冲突
        git pull --rebase origin main || echo "拉取远程仓库失败，尝试继续提交"

        # 提交更改
        if git diff --staged --quiet; then
          echo "没有变更需要提交"
        else
          git commit -m "%(commit_message)s"
          git push
          echo "✅ 成功提交并推送更改"
        fi
      ||| % {
        add_commands: std.join('\n', ['git add ' + std.strReplace(path, '"', '') for path in paths_array]),
        commit_message: commit_message
      }
    },

  // 生成工作流手动触发配置
  generateWorkflowDispatchTrigger(inputs)::  
    {
      workflow_dispatch: {
        inputs: inputs
      }
    },

  // 生成定时触发配置
  generateScheduleTrigger(cron_expression)::  
    {
      schedule: [
        {cron: cron_expression}
      ]
    },

  // 生成并发控制配置
  generateConcurrencyConfig(workflow_type, id)::  
    {
      group: workflow_type + '-' + id + '-${{ github.ref }}',
      'cancel-in-progress': true
    },

  // 构建并发控制
  buildConcurrency(site_id):: {
    group: 'analyzer-' + site_id + '-${{ github.ref }}',
    'cancel-in-progress': true
  },
  
  // 构建预检查作业
  buildPreCheckJob():: {
    name: '准备分析环境',
    'runs-on': 'ubuntu-latest',
    outputs: {
      data_date: '${{ steps.params.outputs.data_date }}',
      data_file: '${{ steps.params.outputs.data_file }}',
      site_id: '${{ steps.params.outputs.site_id }}',
      analysis_dir: '${{ steps.params.outputs.analysis_dir }}',
      cache_key: '${{ steps.params.outputs.cache_key }}'
    },
    steps: [
      {
        name: '检出代码',
        uses: 'actions/checkout@v4'
      },
      {
        name: '确定分析参数',
        id: 'params',
        run: |||
          # 从参数中获取数据日期和文件路径
          if [ "${{ github.event_name }}" == "workflow_dispatch" ]; then
            DATA_DATE="${{ github.event.inputs.data_date }}"
            DATA_FILE="${{ github.event.inputs.data_file }}"
            SITE_ID="${{ github.event.inputs.site_id }}"
          elif [ "${{ github.event_name }}" == "repository_dispatch" ]; then
            DATA_DATE="${{ github.event.client_payload.data_date }}"
            DATA_FILE="${{ github.event.client_payload.data_file }}"
            SITE_ID="${{ github.event.client_payload.site_id }}"
          elif [ "${{ github.event_name }}" == "workflow_call" ]; then
            DATA_DATE="${{ inputs.data_date }}"
            DATA_FILE="${{ inputs.data_file }}"
            SITE_ID="${{ inputs.site_id }}"
          else
            # 从状态文件获取最新数据
            if [ -f "status/crawler_status.json" ]; then
              DATA_DATE=$(jq -r '.date' status/crawler_status.json)
              DATA_FILE=$(jq -r '.file_path' status/crawler_status.json)
              SITE_ID="${{ env.SITE_ID }}"
            else
              echo "❌ 错误: 无法确定数据日期和文件路径"
              exit 1
            fi
          fi
          
          # 确保日期目录存在
          mkdir -p "${ANALYSIS_DIR}/${DATA_DATE}"
          
          # 设置输出参数
          echo "data_date=${DATA_DATE}" >> $GITHUB_OUTPUT
          echo "data_file=${DATA_FILE}" >> $GITHUB_OUTPUT
          echo "site_id=${SITE_ID}" >> $GITHUB_OUTPUT
          echo "analysis_dir=${ANALYSIS_DIR}/${DATA_DATE}" >> $GITHUB_OUTPUT
          
          # 生成缓存键
          if [ -f "requirements.txt" ]; then
            HASH=$(sha256sum requirements.txt | cut -d ' ' -f 1 | head -c 8)
            echo "cache_key=deps-analysis-$HASH-v1" >> $GITHUB_OUTPUT
          else
            echo "cache_key=deps-analysis-default-v1" >> $GITHUB_OUTPUT
          fi
          
          echo "📌 设置分析参数: 日期=${DATA_DATE}, 文件=${DATA_FILE}, 站点=${SITE_ID}"
        |||
      },
      {
        name: '检查数据文件是否存在',
        run: |||
          if [ ! -f "${{ steps.params.outputs.data_file }}" ]; then
            echo "❌ 错误: 数据文件 ${{ steps.params.outputs.data_file }} 不存在"
            exit 1
          else
            echo "✅ 数据文件存在，准备分析"
          fi
        |||
      }
    ]
  },
  
  // 构建分析作业
  buildAnalyzeJob(site_config, global_config):: {
    local analysis_config = $.getAnalysisConfig(site_config),
    local output_extension = $.getOutputExtension(analysis_config),
    local env_vars = $.getEnvironmentVariables(analysis_config, global_config),
    local send_notification = if std.objectHas(global_config, 'notification') && std.objectHas(global_config.notification, 'enabled') then
      global_config.notification.enabled
    else
      false,
    local analyzer_script = if std.objectHas(site_config, 'analysis') && std.objectHas(site_config.analysis, 'script') then
      site_config.analysis.script
    else
      'scripts/ai_analyzer.py',
    local notification_script = if std.objectHas(global_config, 'notification') && std.objectHas(global_config.notification, 'script') then
      global_config.notification.script
    else
      'scripts/notifier.py',
    
    name: '执行AI分析',
    needs: 'pre-check',
    'runs-on': 'ubuntu-latest',
    'timeout-minutes': 30,
    env: {
      DATA_DATE: '${{ needs.pre-check.outputs.data_date }}',
      DATA_FILE: '${{ needs.pre-check.outputs.data_file }}',
      SITE_ID: '${{ needs.pre-check.outputs.site_id }}',
      ANALYSIS_DIR: '${{ needs.pre-check.outputs.analysis_dir }}'
    },
    steps: [
      {
        name: '检出代码',
        uses: 'actions/checkout@v4'
      },
      {
        name: '设置Python环境',
        uses: 'actions/setup-python@v5',
        with: {
          'python-version': '${{ env.PYTHON_VERSION }}',
          cache: 'pip',
          'cache-dependency-path': '**/requirements.txt'
        }
      },
      {
        name: '安装依赖',
        run: |||
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then
            pip install -r requirements.txt
          else
            echo "安装必要的依赖..."
            pip install requests pyyaml pandas openai google-generativeai
          fi
        |||
      },
      {
        name: '运行AI分析',
        id: 'run_analysis',
        'continue-on-error': true,
        env: {
          [env_var.name]: '${{ secrets.' + env_var.secret + ' }}'
          for env_var in env_vars
        } + {
          MODEL: '${{ github.event.inputs.model || \'default\' }}',
          HEIMAO_KEYWORDS: '${{ vars.HEIMAO_KEYWORDS || \'\' }}',
          ENABLE_NOTIFICATION: '${{ vars.ENABLE_NOTIFICATION || \'false\' }}',
          NOTIFICATION_TYPE: '${{ vars.NOTIFICATION_TYPE || \'none\' }}',
          NOTIFICATION_WEBHOOK: '${{ vars.NOTIFICATION_WEBHOOK || \'\' }}',
          GITHUB_REPOSITORY: '${{ github.repository }}'
        },
        run: |||
          echo "📊 开始分析数据文件: $DATA_FILE"
          
          # 指定模型配置
          if [ "$MODEL" != "default" ]; then
            MODEL_ARG="--model $MODEL"
            echo "🧠 使用指定模型: $MODEL"
          else
            MODEL_ARG=""
            echo "🧠 使用默认模型"
          fi
          
          # 运行AI分析脚本
          python %(analyzer_script)s --file "$DATA_FILE" --site "$SITE_ID" --output "$ANALYSIS_DIR/analysis_$DATA_DATE.%(output_extension)s" $MODEL_ARG
          
          # 检查分析结果文件
          if [ -f "$ANALYSIS_DIR/analysis_$DATA_DATE.%(output_extension)s" ]; then
            echo "✅ 分析成功完成，已生成结果文件"
            echo "analysis_exists=true" >> $GITHUB_OUTPUT
            echo "analysis_file=$ANALYSIS_DIR/analysis_$DATA_DATE.%(output_extension)s" >> $GITHUB_OUTPUT
          else
            echo "⚠️ 警告：未找到分析结果文件"
            echo "analysis_exists=false" >> $GITHUB_OUTPUT
          fi
        ||| % {
          analyzer_script: analyzer_script,
          output_extension: output_extension
        }
      },
      {
        name: '创建分析状态文件',
        run: |||
          mkdir -p status
          # 创建状态文件
          if [ "${{ steps.run_analysis.outcome }}" == "success" ] && [ "${{ steps.run_analysis.outputs.analysis_exists }}" == "true" ]; then
            cat > status/analyzer_$SITE_ID.json << EOF
            {
              "status": "success",
              "site_id": "$SITE_ID",
              "date": "$DATA_DATE",
              "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
              "data_file": "$DATA_FILE",
              "analysis_file": "$ANALYSIS_DIR/analysis_$DATA_DATE.%(output_extension)s",
              "run_id": "${{ github.run_id }}",
              "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}",
              "message": "数据分析成功完成"
            }
          EOF
          else
            cat > status/analyzer_$SITE_ID.json << EOF
            {
              "status": "failed",
              "site_id": "$SITE_ID",
              "date": "$DATA_DATE",
              "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
              "data_file": "$DATA_FILE",
              "run_id": "${{ github.run_id }}",
              "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}",
              "message": "数据分析失败或无结果"
            }
          EOF
          fi
          echo "已创建分析状态文件"
        ||| % {
          output_extension: output_extension
        }
      },
      {
        name: '提交分析结果和状态',
        run: |||
          echo "正在提交分析结果和状态..."
          # 设置git配置
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          
          # 添加需要提交的文件
          if [ -f "$ANALYSIS_DIR/analysis_$DATA_DATE.%(output_extension)s" ]; then
            git add "$ANALYSIS_DIR/" || echo "没有分析目录变更"
          fi
          git add status/analyzer_$SITE_ID.json
          
          # 检查是否有变更需要提交
          if git diff --staged --quiet; then
            echo "没有变更需要提交"
          else
            # 创建提交
            git commit -m "🤖 自动更新: %(site_name)s分析结果 ($DATA_DATE)"
            # 推送到仓库
            git push
            echo "✅ 成功提交并推送分析结果和状态"
          fi
        ||| % {
          output_extension: output_extension,
          site_name: $.getSiteName(site_config, std.extVar('site_id'))
        }
      },
      {
        name: '上传分析结果 (作为工件)',
        'if': 'steps.run_analysis.outputs.analysis_exists == \'true\'',
        uses: 'actions/upload-artifact@v4',
        with: {
          name: std.extVar('site_id') + '-analysis-${{ needs.pre-check.outputs.data_date }}',
          path: '${{ steps.run_analysis.outputs.analysis_file }}',
          'retention-days': 5
        }
      }
    ] + (
      if send_notification then [
        {
          name: '发送分析结果通知',
          'if': 'steps.run_analysis.outputs.analysis_exists == \'true\'',
          env: {
            ENABLE_NOTIFICATION: '${{ vars.ENABLE_NOTIFICATION || \'false\' }}',
            NOTIFICATION_TYPE: '${{ vars.NOTIFICATION_TYPE || \'none\' }}',
            NOTIFICATION_WEBHOOK: '${{ vars.NOTIFICATION_WEBHOOK || \'\' }}',
            ANALYSIS_FILE: '${{ steps.run_analysis.outputs.analysis_file }}'
          },
          run: |||
            if [ "$ENABLE_NOTIFICATION" = "true" ] && [ -n "$NOTIFICATION_WEBHOOK" ]; then
              echo "📢 发送分析结果通知..."
              python %(notification_script)s --file "$ANALYSIS_FILE" --site "$SITE_ID"
            else
              echo "ℹ️ 未启用通知或缺少配置，跳过通知发送"
            fi
          ||| % {
            notification_script: notification_script
          }
        }
      ] else []
    ) + [
      {
        name: '触发仪表盘更新工作流',
        'if': 'steps.run_analysis.outputs.analysis_exists == \'true\'',
        uses: 'benc-uk/workflow-dispatch@v1',
        with: {
          workflow: 'update_dashboard.yml',
          token: '${{ secrets.GITHUB_TOKEN }}',
          inputs: '{"site_id": "${{ needs.pre-check.outputs.site_id }}"}'
        }
      }
    ]
  },
  
  // 生成工作流状态报告步骤
  generateWorkflowStatusStep(workflow_type, site_id, parent_param='parent_workflow_id'):: {
    name: '报告工作流状态',
    'if': 'always()',
    run: |||
      # 创建状态目录
      mkdir -p status/workflow
      
      # 生成状态文件
      cat > status/workflow/%(workflow_type)s_%(site_id)s.json << EOF
      {
        "workflow_id": "${{ github.run_id }}",
        "parent_workflow_id": "${{ github.event.inputs.%(parent_param)s || '' }}",
        "workflow_type": "%(workflow_type)s",
        "site_id": "%(site_id)s",
        "status": "${{ job.status }}",
        "timestamp": "$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)",
        "data_date": "${{ needs.pre-check.outputs.run_date }}",
        "artifacts": [
          "%(site_id)s-data-${{ needs.pre-check.outputs.run_date }}",
          "%(site_id)s-status-${{ needs.pre-check.outputs.run_date }}"
        ],
        "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
      }
      EOF
      
      # 如果是由主工作流触发的，则推送状态
      if [ -n "${{ github.event.inputs.%(parent_param)s }}" ]; then
        # 配置Git
        git config user.name "github-actions[bot]"
        git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
        
        # 添加状态文件
        git add status/workflow/%(workflow_type)s_%(site_id)s.json
        
        # 拉取远程更改，避免推送冲突
        git pull --rebase origin main || echo "拉取远程仓库失败，尝试继续提交"
        
        # 提交更改
        if ! git diff --staged --quiet; then
          git commit -m "📊 工作流状态更新: %(workflow_type)s_%(site_id)s (${{ needs.pre-check.outputs.run_date }})"
          git push
        fi
      fi
    ||| % {
      workflow_type: workflow_type,
      site_id: site_id,
      parent_param: parent_param
    }
  },

  // 生成子工作流状态检查步骤
  generateWorkflowStatusCheckStep(workflow_type, id, timeout_seconds=300)::  
    {
      name: '检查' + workflow_type + '_' + id + '状态',
      id: 'check_' + workflow_type + '_' + id + '_status',
      run: |||
        # 设置超时时间
        TIMEOUT_SECONDS=%(timeout_seconds)d
        START_TIME=$(date +%%s)
        END_TIME=$((START_TIME + TIMEOUT_SECONDS))
        
        echo "开始检查工作流状态，最大等待时间: $TIMEOUT_SECONDS 秒"
        
        # 循环检查状态文件
        while true; do
          CURRENT_TIME=$(date +%%s)
          
          # 检查是否超时
          if [ $CURRENT_TIME -gt $END_TIME ]; then
            echo "::warning::等待工作流状态超时"
            echo "status=timeout" >> $GITHUB_OUTPUT
            break
          fi
          
          # 检查状态文件是否存在
          if [ -f "status/workflow/%(workflow_type)s_%(id)s.json" ]; then
            # 读取状态
            STATUS=$(jq -r '.status' status/workflow/%(workflow_type)s_%(id)s.json)
            echo "当前状态: $STATUS"
            
            # 如果状态是终态，则退出循环
            if [ "$STATUS" == "success" ] || [ "$STATUS" == "failed" ] || [ "$STATUS" == "skipped" ]; then
              echo "status=$STATUS" >> $GITHUB_OUTPUT
              break
            fi
          fi
          
          # 等待10秒后再次检查
          echo "工作流仍在运行，等待10秒后再次检查..."
          sleep 10
        done
      ||| % {workflow_type: workflow_type, id: id, timeout_seconds: timeout_seconds}
    },
    
  // 生成可重试步骤
  generateRetryableStep(step_name, command, max_retries=3, retry_delay=5)::  
    {
      name: step_name,
      id: std.strReplace(std.asciiLower(step_name), ' ', '_'),
      run: |||
        # 可重试命令执行
        MAX_RETRIES=%(max_retries)d
        RETRY_DELAY=%(retry_delay)d
        STEP_SUCCESS=false
        
        for ((i=1; i<=MAX_RETRIES; i++)); do
          echo "尝试执行 #$i/$MAX_RETRIES..."
          
          # 执行命令
          %(command)s
          EXIT_CODE=$?
          
          # 检查结果
          if [ $EXIT_CODE -eq 0 ]; then
            echo "✅ 命令成功执行"
            STEP_SUCCESS=true
            echo "success=true" >> $GITHUB_OUTPUT
            break
          else
            echo "❌ 命令执行失败 (错误码: $EXIT_CODE)"
            if [ $i -lt $MAX_RETRIES ]; then
              echo "等待 $RETRY_DELAY 秒后重试..."
              sleep $RETRY_DELAY
            fi
          fi
        done
        
        if [ "$STEP_SUCCESS" != "true" ]; then
          echo "❌ 达到最大重试次数，命令执行失败"
          echo "success=false" >> $GITHUB_OUTPUT
          exit 1
        fi
      ||| % {command: command, max_retries: max_retries, retry_delay: retry_delay}
    },  
      // 生成工作流状态报告步骤
  generateWorkflowStatusStep(workflow_type, site_id, parent_param='parent_workflow_id'):: {
    name: '报告工作流状态',
    'if': 'always()',
    run: |||
      # 创建状态目录
      mkdir -p status/workflow
      
      # 生成状态文件
      cat > status/workflow/%(workflow_type)s_%(site_id)s.json << EOF
      {
        "workflow_id": "${{ github.run_id }}",
        "parent_workflow_id": "${{ github.event.inputs.%(parent_param)s || '' }}",
        "workflow_type": "%(workflow_type)s",
        "site_id": "%(site_id)s",
        "status": "${{ job.status }}",
        "timestamp": "$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)",
        "data_date": "${{ needs.pre-check.outputs.run_date }}",
        "artifacts": [
          "%(site_id)s-data-${{ needs.pre-check.outputs.run_date }}",
          "%(site_id)s-status-${{ needs.pre-check.outputs.run_date }}"
        ],
        "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
      }
      EOF
      
      # 如果是由主工作流触发的，则推送状态
      if [ -n "${{ github.event.inputs.%(parent_param)s }}" ]; then
        # 配置Git
        git config user.name "github-actions[bot]"
        git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
        
        # 添加状态文件
        git add status/workflow/%(workflow_type)s_%(site_id)s.json
        
        # 拉取远程更改，避免推送冲突
        git pull --rebase origin main || echo "拉取远程仓库失败，尝试继续提交"
        
        # 提交更改
        if ! git diff --staged --quiet; then
          git commit -m "📊 工作流状态更新: %(workflow_type)s_%(site_id)s (${{ needs.pre-check.outputs.run_date }})"
          git push
        fi
      fi
    ||| % {
      workflow_type: workflow_type,
      site_id: site_id,
      max_wait: max_wait
    }
  },

  // 构建通知作业
  buildNotifyJob(site_config, global_config):: {
    local site_id = std.extVar('site_id'),
    
    name: '发送通知',
    needs: ['pre-check', 'analyze'],
    'if': 'always()',
    'runs-on': 'ubuntu-latest',
    steps: [
      {
        name: '检出代码',
        'if': 'contains(needs.*.result, \'failure\') || contains(needs.*.result, \'cancelled\')',
        uses: 'actions/checkout@v4'
      },
      {
        name: '设置Python环境',
        uses: 'actions/setup-python@v4',
        with: {
          'python-version': '3.9'
        }
      },
      {
        name: '安装依赖',
        run: |||
          pip install -r requirements.txt
        |||
      },
      {
        name: '下载分析结果',
        'if': 'needs.analyze.result == \'success\'',
        uses: 'actions/download-artifact@v4',
        with: {
          name: site_id + '-analysis-${{ needs.pre-check.outputs.data_date }}',
          path: 'temp-analysis/'
        },
        'continue-on-error': true
      },
      {
        name: '准备通知内容并发送',
        env: {
          DINGTALK_WEBHOOK_URL: '${{ secrets.DINGTALK_WEBHOOK }}',
          FEISHU_WEBHOOK_URL: '${{ secrets.FEISHU_WEBHOOK }}',
          WECHAT_WORK_WEBHOOK_URL: '${{ secrets.WECHAT_WEBHOOK }}'
        },
        run: |||
          # 查找分析结果文件
          ANALYSIS_FILE=""
          if [ -d "temp-analysis" ] && [ "$(ls -A temp-analysis)" ]; then
            ANALYSIS_FILE=$(find temp-analysis -name "*.json" | head -1)
            echo "找到分析文件: $ANALYSIS_FILE"
          fi
          
          # 如果没有分析文件，创建一个临时的状态文件
          if [ -z "$ANALYSIS_FILE" ] || [ ! -f "$ANALYSIS_FILE" ]; then
            mkdir -p temp-analysis
            cat > temp-analysis/workflow_status.json << EOF
          {
            "workflow_status": {
              "pre_check": "${{ needs.pre-check.result }}",
              "analyze": "${{ needs.analyze.result }}",
              "site_id": "%(site_id)s",
              "date": "${{ needs.pre-check.outputs.data_date }}",
              "run_id": "${{ github.run_id }}",
              "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
          }
          EOF
            ANALYSIS_FILE="temp-analysis/workflow_status.json"
            echo "创建状态文件: $ANALYSIS_FILE"
          fi
          
          # 发送通知
          echo "📢 发送通知..."
          python scripts/notify.py --file "$ANALYSIS_FILE" --site "%(site_name)s"
        ||| % {
          site_id: site_id,
          site_name: $.getSiteName(site_config, site_id)
        }
      }
    ]
  },
  
  // 构建完整的分析器作业集合
  buildAnalyzerJobs(site_config, global_config):: {
    'pre-check': $.buildPreCheckJob(),
    analyze: $.buildAnalyzeJob(site_config, global_config),
    notify: $.buildNotifyJob(site_config, global_config)
  },
  
  // 生成记录开始时间步骤
  generateStartTimeStep()::{
    name: '记录开始时间',
    id: 'setup_start',
    run: |||
      echo "start_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $GITHUB_OUTPUT
    |||
  },
  
  // 生成工作流执行指标收集步骤
  generateMetricsCollectionStep(workflow_type, id)::{
    name: '收集执行指标',
    id: 'metrics_collection',
    if: "always()",
    run: |||
      # 创建指标目录
      mkdir -p metrics/workflow
      
      # 记录执行时间
      START_TIME="${{ steps.setup_start.outputs.start_time || github.event.repository.pushed_at }}"
      END_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      
      # 计算执行时间（秒）
      START_SECONDS=$(date -d "$START_TIME" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$START_TIME" +%s 2>/dev/null || echo "0")
      END_SECONDS=$(date -d "$END_TIME" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$END_TIME" +%s 2>/dev/null || echo "0")
      
      if [ "$START_SECONDS" != "0" ] && [ "$END_SECONDS" != "0" ]; then
        DURATION=$((END_SECONDS - START_SECONDS))
      else
        DURATION=0
      fi
      
      # 获取资源使用情况
      MEMORY_USAGE=$(ps -o rss= -p $$ 2>/dev/null || echo "0")
      MEMORY_USAGE=$((MEMORY_USAGE / 1024)) # 转换为MB
      
      # 创建指标文件
      cat > metrics/workflow/%(workflow_type)s_%(id)s_$(date -u +%%Y%%m%%d).json << EOF
      {
        "workflow_type": "%(workflow_type)s",
        "id": "%(id)s",
        "run_id": "${{ github.run_id }}",
        "start_time": "$START_TIME",
        "end_time": "$END_TIME",
        "duration_seconds": $DURATION,
        "status": "${{ job.status }}",
        "memory_usage_mb": $MEMORY_USAGE,
        "date": "$(date -u +%%Y-%%m-%%d)",
        "timestamp": "$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)"
      }
      EOF
      
      echo "✅ 执行指标已保存到 metrics/workflow/%(workflow_type)s_%(id)s_$(date -u +%%Y%%m%%d).json"
      
      # 输出关键指标
      echo "执行时间: $DURATION 秒"
      echo "内存使用: $MEMORY_USAGE MB"
      echo "状态: ${{ job.status }}"
      
      # 提交指标文件
      if [ "${{ github.event_name }}" != "pull_request" ]; then
        git config user.name "github-actions[bot]"
        git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
        git add metrics/workflow/%(workflow_type)s_%(id)s_$(date -u +%%Y%%m%%d).json
        git commit -m "📊 添加工作流执行指标: %(workflow_type)s_%(id)s" || echo "没有更改需要提交"
        git pull --rebase origin main || echo "拉取失败，继续执行"
        git push || echo "推送失败，但继续执行"
      fi
    ||| % {workflow_type: workflow_type, id: id}
  },
  
  // 生成智能调度步骤
  generateSmartSchedulingStep(workflow_type, id)::{
    name: '智能调度分析',
    id: 'smart_scheduling',
    run: |||
      # 创建指标目录（如果不存在）
      mkdir -p metrics/workflow
      
      echo "🧠 开始智能调度分析..."
      
      # 检查历史指标文件
      METRICS_DIR="metrics/workflow"
      METRICS_PATTERN="%(workflow_type)s_%(id)s_*.json"
      
      # 查找所有历史指标文件
      HISTORY_FILES=$(find $METRICS_DIR -name "$METRICS_PATTERN" 2>/dev/null | sort)
      HISTORY_COUNT=$(echo "$HISTORY_FILES" | wc -l)
      
      if [ "$HISTORY_COUNT" -lt 5 ]; then
        echo "⚠️ 历史数据不足，需要至少5个历史记录进行智能调度分析"
        echo "当前仅有 $HISTORY_COUNT 个历史记录"
        echo "scheduling_recommendation=default" >> $GITHUB_OUTPUT
        exit 0
      fi
      
      echo "📊 找到 $HISTORY_COUNT 个历史记录，开始分析..."
      
      # 分析执行时间模式
      TOTAL_DURATION=0
      SUCCESS_COUNT=0
      FAILURE_COUNT=0
      MAX_DURATION=0
      MIN_DURATION=999999
      
      # 按时间段统计成功率
      MORNING_SUCCESS=0
      MORNING_TOTAL=0
      AFTERNOON_SUCCESS=0
      AFTERNOON_TOTAL=0
      EVENING_SUCCESS=0
      EVENING_TOTAL=0
      NIGHT_SUCCESS=0
      NIGHT_TOTAL=0
      
      # 分析每个指标文件
      for FILE in $HISTORY_FILES; do
        if [ -f "$FILE" ]; then
          # 提取关键指标
          DURATION=$(jq -r '.duration_seconds' "$FILE")
          STATUS=$(jq -r '.status' "$FILE")
          START_TIME=$(jq -r '.start_time' "$FILE")
          
          # 统计总时长
          TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
          
          # 更新最大/最小时长
          if [ $DURATION -gt $MAX_DURATION ]; then
            MAX_DURATION=$DURATION
          fi
          
          if [ $DURATION -lt $MIN_DURATION ]; then
            MIN_DURATION=$DURATION
          fi
          
          # 统计成功/失败次数
          if [ "$STATUS" == "success" ]; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            
            # 提取小时
            HOUR=$(date -d "$START_TIME" "+%H" 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$START_TIME" "+%H" 2>/dev/null || echo "0")
            
            # 按时间段统计
            if [ $HOUR -ge 6 ] && [ $HOUR -lt 12 ]; then
              MORNING_SUCCESS=$((MORNING_SUCCESS + 1))
              MORNING_TOTAL=$((MORNING_TOTAL + 1))
            elif [ $HOUR -ge 12 ] && [ $HOUR -lt 18 ]; then
              AFTERNOON_SUCCESS=$((AFTERNOON_SUCCESS + 1))
              AFTERNOON_TOTAL=$((AFTERNOON_TOTAL + 1))
            elif [ $HOUR -ge 18 ] && [ $HOUR -lt 24 ]; then
              EVENING_SUCCESS=$((EVENING_SUCCESS + 1))
              EVENING_TOTAL=$((EVENING_TOTAL + 1))
            else
              NIGHT_SUCCESS=$((NIGHT_SUCCESS + 1))
              NIGHT_TOTAL=$((NIGHT_TOTAL + 1))
            fi
          else
            FAILURE_COUNT=$((FAILURE_COUNT + 1))
            
            # 提取小时（对于失败的情况）
            HOUR=$(date -d "$START_TIME" "+%H" 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$START_TIME" "+%H" 2>/dev/null || echo "0")
            
            # 按时间段统计总数
            if [ $HOUR -ge 6 ] && [ $HOUR -lt 12 ]; then
              MORNING_TOTAL=$((MORNING_TOTAL + 1))
            elif [ $HOUR -ge 12 ] && [ $HOUR -lt 18 ]; then
              AFTERNOON_TOTAL=$((AFTERNOON_TOTAL + 1))
            elif [ $HOUR -ge 18 ] && [ $HOUR -lt 24 ]; then
              EVENING_TOTAL=$((EVENING_TOTAL + 1))
            else
              NIGHT_TOTAL=$((NIGHT_TOTAL + 1))
            fi
          fi
        fi
      done
      
      # 计算平均执行时间
      if [ $HISTORY_COUNT -gt 0 ]; then
        AVG_DURATION=$((TOTAL_DURATION / HISTORY_COUNT))
      else
        AVG_DURATION=0
      fi
      
      # 计算成功率
      if [ $HISTORY_COUNT -gt 0 ]; then
        SUCCESS_RATE=$((SUCCESS_COUNT * 100 / HISTORY_COUNT))
      else
        SUCCESS_RATE=0
      fi
      
      # 计算各时段成功率
      if [ $MORNING_TOTAL -gt 0 ]; then
        MORNING_RATE=$((MORNING_SUCCESS * 100 / MORNING_TOTAL))
      else
        MORNING_RATE=0
      fi
      
      if [ $AFTERNOON_TOTAL -gt 0 ]; then
        AFTERNOON_RATE=$((AFTERNOON_SUCCESS * 100 / AFTERNOON_TOTAL))
      else
        AFTERNOON_RATE=0
      fi
      
      if [ $EVENING_TOTAL -gt 0 ]; then
        EVENING_RATE=$((EVENING_SUCCESS * 100 / EVENING_TOTAL))
      else
        EVENING_RATE=0
      fi
      
      if [ $NIGHT_TOTAL -gt 0 ]; then
        NIGHT_RATE=$((NIGHT_SUCCESS * 100 / NIGHT_TOTAL))
      else
        NIGHT_RATE=0
      fi
      
      # 输出分析结果
      echo "📈 分析结果:"
      echo "- 平均执行时间: $AVG_DURATION 秒"
      echo "- 最长执行时间: $MAX_DURATION 秒"
      echo "- 最短执行时间: $MIN_DURATION 秒"
      echo "- 总成功率: $SUCCESS_RATE%"
      echo "- 上午成功率(6-12点): $MORNING_RATE% (成功: $MORNING_SUCCESS, 总数: $MORNING_TOTAL)"
      echo "- 下午成功率(12-18点): $AFTERNOON_RATE% (成功: $AFTERNOON_SUCCESS, 总数: $AFTERNOON_TOTAL)"
      echo "- 晚上成功率(18-24点): $EVENING_RATE% (成功: $EVENING_SUCCESS, 总数: $EVENING_TOTAL)"
      echo "- 凌晨成功率(0-6点): $NIGHT_RATE% (成功: $NIGHT_SUCCESS, 总数: $NIGHT_TOTAL)"
      
      # 确定最佳执行时段
      BEST_RATE=0
      BEST_TIME="morning"
      
      if [ $MORNING_RATE -gt $BEST_RATE ] && [ $MORNING_TOTAL -ge 3 ]; then
        BEST_RATE=$MORNING_RATE
        BEST_TIME="morning"
      fi
      
      if [ $AFTERNOON_RATE -gt $BEST_RATE ] && [ $AFTERNOON_TOTAL -ge 3 ]; then
        BEST_RATE=$AFTERNOON_RATE
        BEST_TIME="afternoon"
      fi
      
      if [ $EVENING_RATE -gt $BEST_RATE ] && [ $EVENING_TOTAL -ge 3 ]; then
        BEST_RATE=$EVENING_RATE
        BEST_TIME="evening"
      fi
      
      if [ $NIGHT_RATE -gt $BEST_RATE ] && [ $NIGHT_TOTAL -ge 3 ]; then
        BEST_RATE=$NIGHT_RATE
        BEST_TIME="night"
      fi
      
      # 根据最佳时段生成cron表达式
      case $BEST_TIME in
        morning)
          CRON_EXPR="0 9 * * *"  # 上午9点
          TIME_DESC="上午9点"
          ;;
        afternoon)
          CRON_EXPR="0 14 * * *"  # 下午2点
          TIME_DESC="下午2点"
          ;;
        evening)
          CRON_EXPR="0 20 * * *"  # 晚上8点
          TIME_DESC="晚上8点"
          ;;
        night)
          CRON_EXPR="0 2 * * *"  # 凌晨2点
          TIME_DESC="凌晨2点"
          ;;
        *)
          CRON_EXPR="0 0 * * *"  # 默认午夜
          TIME_DESC="午夜12点"
          ;;
      esac
      
      # 根据成功率调整执行频率
      if [ $SUCCESS_RATE -lt 50 ]; then
        # 成功率低于50%，减少执行频率
        FREQ_RECOMMENDATION="减少执行频率，建议每周执行一次"
        CRON_EXPR="0 $(echo $CRON_EXPR | cut -d' ' -f2-) * * 0"  # 每周日
      elif [ $SUCCESS_RATE -gt 90 ]; then
        # 成功率高于90%，可以增加执行频率
        FREQ_RECOMMENDATION="成功率高，可以增加执行频率，建议每天执行"
      else
        # 成功率适中，维持当前频率
        FREQ_RECOMMENDATION="成功率适中，维持当前执行频率"
      fi
      
      echo "🔮 调度建议:"
      echo "- 最佳执行时段: $BEST_TIME ($TIME_DESC)"
      echo "- 建议的cron表达式: $CRON_EXPR"
      echo "- 频率建议: $FREQ_RECOMMENDATION"
      
      # 保存调度建议到输出
      echo "scheduling_recommendation=$BEST_TIME" >> $GITHUB_OUTPUT
      echo "cron_expression=$CRON_EXPR" >> $GITHUB_OUTPUT
      
      # 创建调度配置文件
      cat > metrics/workflow/%(workflow_type)s_%(id)s_schedule.json << EOF
      {
        "workflow_type": "%(workflow_type)s",
        "id": "%(id)s",
        "best_time": "$BEST_TIME",
        "cron_expression": "$CRON_EXPR",
        "success_rate": $SUCCESS_RATE,
        "avg_duration": $AVG_DURATION,
        "morning_rate": $MORNING_RATE,
        "afternoon_rate": $AFTERNOON_RATE,
        "evening_rate": $EVENING_RATE,
        "night_rate": $NIGHT_RATE,
        "recommendation": "$FREQ_RECOMMENDATION",
        "last_updated": "$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)"
      }
      EOF
      
      echo "✅ 调度配置已保存到 metrics/workflow/%(workflow_type)s_%(id)s_schedule.json"
      
      # 提交调度配置
      if [ "${{ github.event_name }}" != "pull_request" ]; then
        git config user.name "github-actions[bot]"
        git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
        git add metrics/workflow/%(workflow_type)s_%(id)s_schedule.json
        git commit -m "⏱️ 更新智能调度配置: %(workflow_type)s_%(id)s" || echo "没有更改需要提交"
        git pull --rebase origin main || echo "拉取失败，继续执行"
        git push || echo "推送失败，但继续执行"
      fi
    ||| % {workflow_type: workflow_type, id: id}
  },
  
  // 生成应用智能调度的步骤
  generateApplyScheduleStep(workflow_type, id)::{
    name: '应用智能调度',
    id: 'apply_schedule',
    needs: ['smart_scheduling'],
    run: |||
      # 检查是否有调度建议
      SCHEDULE_RECOMMENDATION="${{ needs.smart_scheduling.outputs.scheduling_recommendation }}"
      CRON_EXPRESSION="${{ needs.smart_scheduling.outputs.cron_expression }}"
      
      if [ -z "$SCHEDULE_RECOMMENDATION" ] || [ "$SCHEDULE_RECOMMENDATION" == "default" ]; then
        echo "⚠️ 没有足够的历史数据进行智能调度，使用默认调度"
        exit 0
      fi
      
      echo "🔄 应用智能调度: $SCHEDULE_RECOMMENDATION ($CRON_EXPRESSION)"
      
      # 更新工作流文件中的调度表达式
      # 注意：这里需要根据实际的工作流文件结构进行调整
      WORKFLOW_FILE=".github/workflows/%(workflow_type)s_%(id)s.yml"
      
      if [ -f "$WORKFLOW_FILE" ]; then
        # 备份原文件
        cp "$WORKFLOW_FILE" "$WORKFLOW_FILE.bak"
        
        # 更新cron表达式
        # 这里使用sed命令替换cron表达式，需要根据实际文件格式调整
        sed -i.tmp "s/cron: '[^']*'/cron: '$CRON_EXPRESSION'/" "$WORKFLOW_FILE" || \
        sed -i "s/cron: '[^']*'/cron: '$CRON_EXPRESSION'/" "$WORKFLOW_FILE"
        
        # 清理临时文件
        rm -f "$WORKFLOW_FILE.tmp"
        
        echo "✅ 已更新工作流调度配置"
        
        # 提交更改
        if [ "${{ github.event_name }}" != "pull_request" ]; then
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add "$WORKFLOW_FILE"
          git commit -m "⏱️ 自动更新工作流调度: %(workflow_type)s_%(id)s" || echo "没有更改需要提交"
          git pull --rebase origin main || echo "拉取失败，继续执行"
          git push || echo "推送失败，但继续执行"
        fi
      else
        echo "⚠️ 工作流文件不存在: $WORKFLOW_FILE"
      fi
    ||| % {workflow_type: workflow_type, id: id}
  }
} 