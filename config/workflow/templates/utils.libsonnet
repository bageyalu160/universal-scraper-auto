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
  
  // 获取分析配置
  getAnalysisConfig(site_config)::
    if std.objectHas(site_config, 'analysis') then
      site_config.analysis
    else
      {},
  
  // 获取输出扩展名
  getOutputExtension(analysis_config)::
    if std.objectHas(analysis_config, 'output_format') then
      if analysis_config.output_format == 'json' then 'json'
      else if analysis_config.output_format == 'tsv' then 'tsv'
      else if analysis_config.output_format == 'csv' then 'csv'
      else 'json'
    else
      'tsv',
  
  // 获取环境变量配置
  getEnvironmentVariables(analysis_config, global_config):: [
    { name: 'OPENAI_API_KEY', secret: 'OPENAI_API_KEY' },
    { name: 'GEMINI_API_KEY', secret: 'GEMINI_API_KEY' },
    { name: 'ANTHROPIC_API_KEY', secret: 'ANTHROPIC_API_KEY' }
  ],
  
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
  }
} 