// 主调度工作流模板 - Jsonnet版本
// 修复版本 - 已修复以下问题：
// 1. ✅ 修复语法错误（schedule数组格式）
// 2. ✅ 更新数据目录路径逻辑（使用data/daily/$DATE结构）
// 3. ✅ 改进错误处理机制（宽松的错误处理，不中断流程）
// 4. ✅ 添加条件执行逻辑（仅在数据文件存在时触发分析）

local params = import 'params.libsonnet';

{
  name: '主调度工作流',
  'run-name': '🚀 主调度工作流 #${{ github.run_number }} (${{ github.actor }})',
  
  on: {
    workflow_dispatch: {
      inputs: {
        action: {
          description: '执行操作',
          required: true,
          type: 'choice',
          options: [
            'crawl_all',
            'analyze_all',
            'update_dashboard',
            'update_proxy_pool',
            'full_pipeline'
          ]
        },
        site_id: {
          description: '站点ID (仅适用于单站点操作)',
          required: false,
          type: 'string'
        },
        date: {
          description: '数据日期 (留空则使用当前日期)',
          required: false,
          type: 'string'
        }
      }
    },
    schedule: [
      {cron: '0 0 * * *'}
    ]
  },
  
  permissions: {
    contents: 'write',
    actions: 'write',
    pages: 'write',
    'id-token': 'write'
  },
  
  jobs: {
    // 准备环境任务
    setup: {
      name: '准备环境',
      'runs-on': 'ubuntu-latest',
      outputs: {
        date: '${{ steps.set-date.outputs.date }}',
        sites: '${{ steps.list-sites.outputs.sites }}'
      },
      steps: [
        {
          name: '检出代码',
          uses: 'actions/checkout@v4'
        },
        {
          name: '设置日期',
          id: 'set-date',
          run: |||
            if [ -n "${{ github.event.inputs.date }}" ]; then
              echo "date=${{ github.event.inputs.date }}" >> $GITHUB_OUTPUT
            else
              echo "date=$(date +%Y-%m-%d)" >> $GITHUB_OUTPUT
            fi
          |||
        },
        {
          name: '列出可用站点',
          id: 'list-sites',
          run: |||
            if [ -n "${{ github.event.inputs.site_id }}" ]; then
              SITES="[\"${{ github.event.inputs.site_id }}\"]"
            else
              SITES="["
              FIRST=true
              for site in config/sites/*.yaml; do
                SITE_ID=$(basename $site .yaml)
                if [ "$SITE_ID" = "example" ]; then
                  continue
                fi
                if [ "$FIRST" = true ]; then
                  FIRST=false
                else
                  SITES="$SITES,"
                fi
                SITES="$SITES\"$SITE_ID\""
              done
              SITES="$SITES]"
            fi
            echo "sites=$SITES" >> $GITHUB_OUTPUT
            echo "发现站点: $SITES"
          |||
        },
        {
          name: '环境信息收集',
          run: |||
            echo "=== 环境信息 ==="
            echo "运行时间: $(date)"
            echo "触发方式: ${{ github.event_name }}"
            echo "操作类型: ${{ github.event.inputs.action || '定时任务' }}"
            echo "指定站点: ${{ github.event.inputs.site_id || '全部站点' }}"
            echo "指定日期: ${{ github.event.inputs.date || '当前日期' }}"
            echo "运行ID: ${{ github.run_id }}"
            echo "=== 项目结构检查 ==="
            ls -la config/sites/ | head -10
            echo "=== 数据目录检查 ==="
            if [ -d "data/daily" ]; then
              echo "最近的数据目录:"
              ls -la data/daily/ | tail -5
            else
              echo "数据目录不存在"
            fi
          |||
        }
      ]
    },
    
    // 代理池更新任务
    update_proxy_pool: {
      name: '更新代理池',
      needs: 'setup',
      'if': 'github.event.inputs.action == \'update_proxy_pool\' || github.event.inputs.action == \'full_pipeline\' || github.event_name == \'schedule\'',
      'runs-on': 'ubuntu-latest',
      steps: [
        {
          name: '触发代理池工作流',
          uses: 'benc-uk/workflow-dispatch@v1',
          with: {
            workflow: 'proxy_pool_manager.yml',
            token: '${{ secrets.GITHUB_TOKEN }}',
            inputs: '{"action": "update"}'
          }
        }
      ]
    },
    
    // 爬取数据任务
    crawl: {
      name: '爬取数据',
      needs: ['setup', 'update_proxy_pool'],
      'if': 'always() && (github.event.inputs.action == \'crawl_all\' || github.event.inputs.action == \'full_pipeline\' || github.event_name == \'schedule\') && (needs.update_proxy_pool.result == \'success\' || needs.update_proxy_pool.result == \'skipped\')',
      'runs-on': 'ubuntu-latest',
      strategy: {
        matrix: {
          site_id: '${{ fromJSON(needs.setup.outputs.sites) }}'
        },
        'fail-fast': false
      },
      steps: [
        {
          name: '触发爬虫工作流',
          uses: 'benc-uk/workflow-dispatch@v1',
          with: {
            workflow: 'crawler_${{ matrix.site_id }}.yml',
            token: '${{ secrets.GITHUB_TOKEN }}',
            inputs: '{"date": "${{ needs.setup.outputs.date }}"}'
          }
        }
      ]
    },
    
    // 分析数据任务
    analyze: {
      name: '分析数据',
      needs: ['setup', 'crawl'],
      'if': 'always() && (github.event.inputs.action == \'analyze_all\' || github.event.inputs.action == \'full_pipeline\' || github.event_name == \'schedule\') && (needs.crawl.result == \'success\' || needs.crawl.result == \'skipped\')',
      'runs-on': 'ubuntu-latest',
      strategy: {
        matrix: {
          site_id: '${{ fromJSON(needs.setup.outputs.sites) }}'
        },
        'fail-fast': false
      },
      steps: [
        {
          name: '检出代码',
          uses: 'actions/checkout@v4'
        },
        {
          name: '获取最新数据文件',
          id: 'get-latest-file',
          run: |||
            SITE_ID="${{ matrix.site_id }}"
            DATE="${{ needs.setup.outputs.date }}"
            DATA_DIR="data/daily/$DATE"
            
            echo "=== 数据文件查找 ==="
            echo "站点ID: $SITE_ID"
            echo "目标日期: $DATE"
            echo "数据目录: $DATA_DIR"
            
            if [ -d "$DATA_DIR" ]; then
              echo "✅ 数据目录存在"
              echo "目录内容:"
              ls -la "$DATA_DIR" | grep -E "(${SITE_ID}|\.json|\.csv)" || echo "无相关文件"
              
              FILE=$(find $DATA_DIR -name "*${SITE_ID}*" -type f | sort | tail -n 1)
              if [ -n "$FILE" ]; then
                echo "data_file=$FILE" >> $GITHUB_OUTPUT
                echo "found=true" >> $GITHUB_OUTPUT
                echo "✅ 找到数据文件: $FILE"
                echo "文件大小: $(du -h "$FILE" | cut -f1)"
                echo "文件时间: $(ls -l "$FILE" | awk '{print $6, $7, $8}')"
              else
                echo "data_file=" >> $GITHUB_OUTPUT
                echo "found=false" >> $GITHUB_OUTPUT
                echo "⚠️ 未找到匹配的数据文件"
                echo "尝试查找所有文件:"
                find $DATA_DIR -type f | head -5
              fi
            else
              echo "data_file=" >> $GITHUB_OUTPUT
              echo "found=false" >> $GITHUB_OUTPUT
              echo "⚠️ 数据目录不存在: $DATA_DIR"
              echo "可用的数据目录:"
              if [ -d "data/daily" ]; then
                ls -1 data/daily/ | tail -3
              else
                echo "data/daily 目录不存在"
              fi
            fi
          |||
        },
        {
          name: '触发分析工作流',
          'if': 'steps.get-latest-file.outputs.data_file != \'\'',
          uses: 'benc-uk/workflow-dispatch@v1',
          with: {
            workflow: 'analyzer_${{ matrix.site_id }}.yml',
            token: '${{ secrets.GITHUB_TOKEN }}',
            inputs: |||
              {
                "data_date": "${{ needs.setup.outputs.date }}",
                "data_file": "${{ steps.get-latest-file.outputs.data_file }}",
                "site_id": "${{ matrix.site_id }}"
              }
            |||
          }
        }
      ]
    },
    
    // 更新仪表盘任务
    update_dashboard: {
      name: '更新仪表盘',
      needs: ['setup', 'analyze'],
      'if': 'always() && (github.event.inputs.action == \'update_dashboard\' || github.event.inputs.action == \'full_pipeline\' || github.event_name == \'schedule\') && (needs.analyze.result == \'success\' || needs.analyze.result == \'skipped\')',
      uses: './.github/workflows/update_dashboard.yml'
    },

    // 工作流执行摘要
    workflow_summary: {
      name: '执行摘要',
      needs: ['setup', 'update_proxy_pool', 'crawl', 'analyze', 'update_dashboard'],
      'if': 'always()',
      'runs-on': 'ubuntu-latest',
      steps: [
        {
          name: '生成执行摘要',
          run: |||
            echo "=== 🚀 主调度工作流执行摘要 ==="
            echo "执行时间: $(date)"
            echo "运行ID: ${{ github.run_id }}"
            echo "触发方式: ${{ github.event_name }}"
            echo "执行操作: ${{ github.event.inputs.action || '定时任务' }}"
            echo "目标站点: ${{ github.event.inputs.site_id || '全部站点' }}"
            echo "数据日期: ${{ needs.setup.outputs.date }}"
            echo ""
            echo "=== 📊 各阶段执行结果 ==="
            echo "1️⃣ 环境准备: ${{ needs.setup.result }}"
            echo "2️⃣ 代理池更新: ${{ needs.update_proxy_pool.result }}"
            echo "3️⃣ 数据爬取: ${{ needs.crawl.result }}"
            echo "4️⃣ 数据分析: ${{ needs.analyze.result }}"
            echo "5️⃣ 仪表盘更新: ${{ needs.update_dashboard.result }}"
            echo ""
            echo "=== 🔗 相关链接 ==="
            echo "工作流运行: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            if [[ "${{ needs.update_dashboard.result }}" == "success" ]]; then
              echo "监控仪表盘: https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/"
            fi
            echo ""
            
            # 创建状态文件
            mkdir -p status/workflow
            cat > status/workflow/master_workflow_summary.json << EOF
            {
              "workflow_id": "${{ github.run_id }}",
              "trigger": "${{ github.event_name }}",
              "action": "${{ github.event.inputs.action || '定时任务' }}",
              "date": "${{ needs.setup.outputs.date }}",
              "sites": ${{ needs.setup.outputs.sites }},
              "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
              "results": {
                "setup": "${{ needs.setup.result }}",
                "proxy_pool": "${{ needs.update_proxy_pool.result }}",
                "crawl": "${{ needs.crawl.result }}",
                "analyze": "${{ needs.analyze.result }}",
                "dashboard": "${{ needs.update_dashboard.result }}"
              },
              "url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
            EOF
            echo "✅ 执行摘要已保存到 status/workflow/master_workflow_summary.json"
          |||
        }
      ]
    },
    
    // 通知完成任务
    notify_completion: {
      name: '通知完成',
      needs: ['setup', 'update_proxy_pool', 'crawl', 'analyze', 'update_dashboard', 'workflow_summary'],
      'if': 'always()',
      'runs-on': 'ubuntu-latest',
      steps: [
        {
          name: '检出代码',
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
          name: '准备通知内容并发送',
          id: 'send_notification',
          env: {
            DINGTALK_WEBHOOK_URL: '${{ secrets.DINGTALK_WEBHOOK }}',
            FEISHU_WEBHOOK_URL: '${{ secrets.FEISHU_WEBHOOK }}',
            WECHAT_WORK_WEBHOOK_URL: '${{ secrets.WECHAT_WEBHOOK }}'
          },
          run: |||
            # 创建工作流状态文件
            mkdir -p temp-notification
            cat > temp-notification/master_workflow_status.json << EOF
            {
              "workflow_status": {
                "setup": "${{ needs.setup.result }}",
                "proxy_pool": "${{ needs.update_proxy_pool.result }}",
                "crawl": "${{ needs.crawl.result }}",
                "analyze": "${{ needs.analyze.result }}",
                "dashboard": "${{ needs.update_dashboard.result }}",
                "date": "${{ needs.setup.outputs.date }}",
                "sites": ${{ needs.setup.outputs.sites }},
                "action": "${{ github.event.inputs.action || '定时任务' }}",
                "run_id": "${{ github.run_id }}",
                "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
              }
            }
            EOF
            
            # 发送通知
            echo "📢 发送主工作流完成通知..."
            python scripts/notify.py --file "temp-notification/master_workflow_status.json" --site "主工作流"
          |||
        }
      ]
    }
  }
}
