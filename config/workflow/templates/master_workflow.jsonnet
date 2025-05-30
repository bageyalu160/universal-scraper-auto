// 主调度工作流模板 - Jsonnet版本 (增强版)
// 修复版本 - 已修复以下问题：
// 1. ✅ 修复语法错误（schedule数组格式）
// 2. ✅ 更新数据目录路径逻辑（使用data/daily/$DATE结构）
// 3. ✅ 改进错误处理机制（宽松的错误处理，不中断流程）
// 4. ✅ 添加条件执行逻辑（仅在数据文件存在时触发分析）
// 5. ✅ 使用公共函数优化代码结构和可维护性

local params = import 'params.libsonnet';
local utils = import 'utils.libsonnet';

// 外部参数
local global_config = std.parseJson(std.extVar('global_config'));

// 缓存配置
local cache_config = utils.generateCacheConfig('master', 'workflow');

// 超时设置
local setup_timeout = utils.getJobTimeout('setup', global_config);
local summary_timeout = utils.getJobTimeout('setup', global_config) / 2;

// 错误处理策略
local master_error_strategy = utils.getErrorHandlingStrategy('master_workflow', global_config);

// 环境变量
local workflow_env = utils.generateWorkflowEnv('master', global_config);

{
  name: '主调度工作流',
  'run-name': '🚀 主调度工作流 #${{ github.run_number }} (${{ github.actor }})',
  
  on: utils.generateWorkflowDispatchTrigger({
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
  }) + utils.generateScheduleTrigger('0 0 * * *'),
  
  permissions: {
    contents: 'write',
    actions: 'write',
    pages: 'write',
    'id-token': 'write'
  },
  
  // 并发控制 - 避免主工作流并行运行
  concurrency: utils.generateConcurrencyConfig('master', 'workflow'),
  
  // 全局环境变量
  env: workflow_env,
  
  jobs: {
    // 准备环境任务
    setup: {
      name: '准备环境',
      'runs-on': params.runtime.runner,
      'timeout-minutes': setup_timeout,
      outputs: {
        date: '${{ steps.set-date.outputs.date }}',
        sites: '${{ steps.list-sites.outputs.sites }}'
      },
      steps: [
        utils.generateCheckoutStep(),
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
      'if': "github.event.inputs.action == 'update_proxy_pool' || github.event.inputs.action == 'full_pipeline' || github.event_name == 'schedule'",
      'runs-on': params.runtime.runner,
      steps: [
        {
          name: '触发代理池更新工作流',
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
      'if': "always() && (github.event.inputs.action == 'crawl_all' || github.event.inputs.action == 'full_pipeline' || github.event_name == 'schedule')",
      'runs-on': params.runtime.runner,
      outputs: {
        status: '${{ steps.crawl_summary.outputs.status }}',
        success_count: '${{ steps.crawl_summary.outputs.success_count }}',
        failed_count: '${{ steps.crawl_summary.outputs.failed_count }}',
        failed_sites: '${{ steps.crawl_summary.outputs.failed_sites }}'
      },
      strategy: {
        matrix: {
          site_id: '${{ fromJSON(needs.setup.outputs.sites) }}'
        },
        'fail-fast': master_error_strategy['fail-fast']
      },
      steps: [
        utils.generateCheckoutStep(),
        utils.generateDirectorySetupStep(['status/workflow']),
        {
          name: '触发爬虫工作流',
          id: 'trigger_crawler',
          uses: 'benc-uk/workflow-dispatch@v1',
          with: {
            workflow: 'crawler_${{ matrix.site_id }}.yml',
            token: '${{ secrets.GITHUB_TOKEN }}',
            inputs: '{"date": "${{ needs.setup.outputs.date }}", "parent_workflow_id": "${{ github.run_id }}"}'
          }
        },
        // 初始化工作流状态
        {
          name: '初始化工作流状态',
          run: |||
            # 创建初始状态文件
            mkdir -p status/workflow
            cat > status/workflow/crawler_${{ matrix.site_id }}.json << EOF
            {
              "workflow_id": "${{ steps.trigger_crawler.outputs.workflow_id }}",
              "parent_workflow_id": "${{ github.run_id }}",
              "workflow_type": "crawler",
              "site_id": "${{ matrix.site_id }}",
              "status": "running",
              "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
              "data_date": "${{ needs.setup.outputs.date }}",
              "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ steps.trigger_crawler.outputs.workflow_id }}"
            }
            EOF
          |||
        },
        // 检查爬虫工作流状态
        utils.generateWorkflowStatusCheckStep('crawler', '${{ matrix.site_id }}', 300),
        // 处理爬虫结果
        {
          name: '处理爬虫结果',
          if: "always()",
          run: |||
            STATUS="${{ steps.check_crawler_${{ matrix.site_id }}_status.outputs.status || 'unknown' }}"
            echo "爬虫工作流状态: $STATUS"
            
            if [ "$STATUS" != "success" ]; then
              echo "::warning::爬虫工作流执行失败或超时，站点: ${{ matrix.site_id }}"
            fi
          |||
        },
        // 汇总爬虫结果
        {
          name: '汇总爬虫结果',
          id: 'crawl_summary',
          if: "always()",
          run: |||
            # 记录每个站点的状态
            mkdir -p status/workflow
            
            # 写入当前状态
            echo "site_id=${{ matrix.site_id }}" >> $GITHUB_OUTPUT
            echo "status=${{ steps.check_crawler_${{ matrix.site_id }}_status.outputs.status || 'unknown' }}" >> $GITHUB_OUTPUT
          |||
        }
      ]
    },
    
    // 分析数据任务
    analyze: {
      name: '分析数据',
      needs: ['setup', 'crawl'],
      'if': "always() && (github.event.inputs.action == 'analyze_all' || github.event.inputs.action == 'full_pipeline' || github.event_name == 'schedule')",
      'runs-on': params.runtime.runner,
      outputs: {
        status: '${{ steps.analyze_summary.outputs.status }}',
        success_count: '${{ steps.analyze_summary.outputs.success_count }}',
        failed_count: '${{ steps.analyze_summary.outputs.failed_count }}',
        failed_sites: '${{ steps.analyze_summary.outputs.failed_sites }}'
      },
      strategy: {
        matrix: {
          site_id: '${{ fromJSON(needs.setup.outputs.sites) }}'
        },
        'fail-fast': master_error_strategy['fail-fast']
      },
      steps: [
        utils.generateCheckoutStep(),
        utils.generateDirectorySetupStep(['status/workflow']),
        {
          name: '获取最新数据文件',
          id: 'get-latest-file',
          run: |||
            SITE_ID="${{ matrix.site_id }}"
            DATE="${{ needs.setup.outputs.date }}"
            DATA_DIR="data/daily/$DATE"
            
            echo "=== 数据文件查找 ==="
            echo "站点ID: $SITE_ID"
            echo "日期: $DATE"
            echo "目录: $DATA_DIR"
            
            # 检查指定日期目录下的数据文件
            if [ -d "$DATA_DIR" ]; then
              DATA_FILE=$(find "$DATA_DIR" -name "${SITE_ID}_*.json" -o -name "${SITE_ID}_*.csv" -o -name "${SITE_ID}_*.tsv" | head -1)
              
              if [ -n "$DATA_FILE" ] && [ -f "$DATA_FILE" ]; then
                echo "找到数据文件: $DATA_FILE"
                echo "data_file=$DATA_FILE" >> $GITHUB_OUTPUT
              else
                echo "在 $DATA_DIR 中未找到 ${SITE_ID} 的数据文件"
                echo "data_file=" >> $GITHUB_OUTPUT
              fi
            else
              echo "$DATA_DIR 目录不存在"
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
          id: 'trigger_analyzer',
          'if': "steps.get-latest-file.outputs.data_file != ''",
          uses: 'benc-uk/workflow-dispatch@v1',
          with: {
            workflow: 'analyzer_${{ matrix.site_id }}.yml',
            token: '${{ secrets.GITHUB_TOKEN }}',
            inputs: |||
              {
                "data_date": "${{ needs.setup.outputs.date }}",
                "data_file": "${{ steps.get-latest-file.outputs.data_file }}",
                "site_id": "${{ matrix.site_id }}",
                "parent_workflow_id": "${{ github.run_id }}"
              }
            |||
          }
        },
        // 初始化工作流状态
        {
          name: '初始化分析工作流状态',
          if: "steps.get-latest-file.outputs.data_file != ''",
          run: |||
            # 创建初始状态文件
            mkdir -p status/workflow
            cat > status/workflow/analyzer_${{ matrix.site_id }}.json << EOF
            {
              "workflow_id": "${{ steps.trigger_analyzer.outputs.workflow_id || '' }}",
              "parent_workflow_id": "${{ github.run_id }}",
              "workflow_type": "analyzer",
              "site_id": "${{ matrix.site_id }}",
              "status": "running",
              "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
              "data_date": "${{ needs.setup.outputs.date }}",
              "data_file": "${{ steps.get-latest-file.outputs.data_file }}",
              "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ steps.trigger_analyzer.outputs.workflow_id || '' }}"
            }
            EOF
          |||
        },
        // 记录没有数据文件的情况
        {
          name: '记录无数据文件状态',
          if: "steps.get-latest-file.outputs.data_file == ''",
          run: |||
            # 创建状态文件
            mkdir -p status/workflow
            cat > status/workflow/analyzer_${{ matrix.site_id }}.json << EOF
            {
              "workflow_id": "none",
              "parent_workflow_id": "${{ github.run_id }}",
              "workflow_type": "analyzer",
              "site_id": "${{ matrix.site_id }}",
              "status": "skipped",
              "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
              "data_date": "${{ needs.setup.outputs.date }}",
              "message": "无数据文件可分析"
            }
            EOF
          |||
        },
        // 检查分析器工作流状态
        utils.generateWorkflowStatusCheckStep('analyzer', '${{ matrix.site_id }}', 600),
        // 处理分析器结果
        {
          name: '处理分析器结果',
          if: "steps.get-latest-file.outputs.data_file != ''",
          run: |||
            STATUS="${{ steps.check_analyzer_${{ matrix.site_id }}_status.outputs.status || 'unknown' }}"
            echo "分析器工作流状态: $STATUS"
            
            if [ "$STATUS" != "success" ]; then
              echo "::warning::分析器工作流执行失败或超时，站点: ${{ matrix.site_id }}"
            fi
          |||
        },
        // 汇总分析器结果
        {
          name: '汇总分析器结果',
          id: 'analyze_summary',
          if: "always()",
          run: |||
            # 记录每个站点的状态
            mkdir -p status/workflow
            
            # 写入当前状态
            echo "site_id=${{ matrix.site_id }}" >> $GITHUB_OUTPUT
            
            if [ "${{ steps.get-latest-file.outputs.data_file }}" == "" ]; then
              echo "status=skipped" >> $GITHUB_OUTPUT
            else
              echo "status=${{ steps.check_analyzer_${{ matrix.site_id }}_status.outputs.status || 'unknown' }}" >> $GITHUB_OUTPUT
            fi
          |||
        }
      ]
    },
    
    // 更新仪表盘任务
    update_dashboard: {
      name: '更新仪表盘',
      needs: ['setup', 'analyze'],
      'if': "always() && (github.event.inputs.action == 'update_dashboard' || github.event.inputs.action == 'full_pipeline' || github.event_name == 'schedule') && (needs.analyze.result == 'success' || needs.analyze.result == 'skipped')",
      'runs-on': params.runtime.runner,
      steps: [
        {
          name: '触发仪表盘更新工作流',
          uses: 'benc-uk/workflow-dispatch@v1',
          with: {
            workflow: 'update_dashboard.yml',
            token: '${{ secrets.GITHUB_TOKEN }}',
            inputs: '{"date": "${{ needs.setup.outputs.date }}"}'
          }
        }
      ]
    },
    
    // 工作流总结任务
    workflow_summary: {
      name: '工作流总结',
      needs: ['setup', 'update_proxy_pool', 'crawl', 'analyze', 'update_dashboard'],
      'if': 'always()',
      'runs-on': params.runtime.runner,
      'timeout-minutes': summary_timeout,
      steps: [
        utils.generateCheckoutStep(),
        utils.generateDirectorySetupStep(['status/workflow']),
        {
          name: '生成执行摘要',
          id: 'workflow_summary',
          run: |||
            echo "=== 🚀 主工作流执行摘要 ==="
            echo "执行日期: ${{ needs.setup.outputs.date }}"
            echo "触发方式: ${{ github.event_name }}"
            echo "操作类型: ${{ github.event.inputs.action || '定时任务' }}"
            echo "处理站点: ${{ needs.setup.outputs.sites }}"
            echo ""
            
            # 统计子工作流状态
            echo "=== 📊 子工作流状态统计 ==="
            
            # 爬虫工作流统计
            CRAWLER_SUCCESS=0
            CRAWLER_FAILED=0
            CRAWLER_SKIPPED=0
            CRAWLER_UNKNOWN=0
            CRAWLER_FAILED_SITES=""
            
            # 分析器工作流统计
            ANALYZER_SUCCESS=0
            ANALYZER_FAILED=0
            ANALYZER_SKIPPED=0
            ANALYZER_UNKNOWN=0
            ANALYZER_FAILED_SITES=""
            
            # 遍历状态文件目录
            for STATUS_FILE in status/workflow/crawler_*.json; do
              if [ -f "$STATUS_FILE" ]; then
                SITE_ID=$(basename "$STATUS_FILE" | sed 's/crawler_\(.*\)\.json/\1/')
                STATUS=$(jq -r '.status' "$STATUS_FILE")
                
                case "$STATUS" in
                  "success")
                    CRAWLER_SUCCESS=$((CRAWLER_SUCCESS + 1))
                    ;;
                  "failed")
                    CRAWLER_FAILED=$((CRAWLER_FAILED + 1))
                    CRAWLER_FAILED_SITES="$CRAWLER_FAILED_SITES $SITE_ID"
                    ;;
                  "skipped")
                    CRAWLER_SKIPPED=$((CRAWLER_SKIPPED + 1))
                    ;;
                  *)
                    CRAWLER_UNKNOWN=$((CRAWLER_UNKNOWN + 1))
                    ;;
                esac
              fi
            done
            
            for STATUS_FILE in status/workflow/analyzer_*.json; do
              if [ -f "$STATUS_FILE" ]; then
                SITE_ID=$(basename "$STATUS_FILE" | sed 's/analyzer_\(.*\)\.json/\1/')
                STATUS=$(jq -r '.status' "$STATUS_FILE")
                
                case "$STATUS" in
                  "success")
                    ANALYZER_SUCCESS=$((ANALYZER_SUCCESS + 1))
                    ;;
                  "failed")
                    ANALYZER_FAILED=$((ANALYZER_FAILED + 1))
                    ANALYZER_FAILED_SITES="$ANALYZER_FAILED_SITES $SITE_ID"
                    ;;
                  "skipped")
                    ANALYZER_SKIPPED=$((ANALYZER_SKIPPED + 1))
                    ;;
                  *)
                    ANALYZER_UNKNOWN=$((ANALYZER_UNKNOWN + 1))
                    ;;
                esac
              fi
            done
            
            echo "爬虫工作流: 成功=$CRAWLER_SUCCESS, 失败=$CRAWLER_FAILED, 跳过=$CRAWLER_SKIPPED, 未知=$CRAWLER_UNKNOWN"
            if [ -n "$CRAWLER_FAILED_SITES" ]; then
              echo "爬虫失败站点:$CRAWLER_FAILED_SITES"
            fi
            
            echo "分析工作流: 成功=$ANALYZER_SUCCESS, 失败=$ANALYZER_FAILED, 跳过=$ANALYZER_SKIPPED, 未知=$ANALYZER_UNKNOWN"
            if [ -n "$ANALYZER_FAILED_SITES" ]; then
              echo "分析失败站点:$ANALYZER_FAILED_SITES"
            fi
            
            echo ""
            echo "=== 📊 各步骤执行结果 ==="
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
              "crawler_stats": {
                "success": $CRAWLER_SUCCESS,
                "failed": $CRAWLER_FAILED,
                "skipped": $CRAWLER_SKIPPED,
                "unknown": $CRAWLER_UNKNOWN,
                "failed_sites": "$CRAWLER_FAILED_SITES"
              },
              "analyzer_stats": {
                "success": $ANALYZER_SUCCESS,
                "failed": $ANALYZER_FAILED,
                "skipped": $ANALYZER_SKIPPED,
                "unknown": $ANALYZER_UNKNOWN,
                "failed_sites": "$ANALYZER_FAILED_SITES"
              },
              "url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
            EOF
            
            # 输出到 GITHUB_OUTPUT
            echo "crawler_success=$CRAWLER_SUCCESS" >> $GITHUB_OUTPUT
            echo "crawler_failed=$CRAWLER_FAILED" >> $GITHUB_OUTPUT
            echo "crawler_skipped=$CRAWLER_SKIPPED" >> $GITHUB_OUTPUT
            echo "crawler_failed_sites=$CRAWLER_FAILED_SITES" >> $GITHUB_OUTPUT
            
            echo "analyzer_success=$ANALYZER_SUCCESS" >> $GITHUB_OUTPUT
            echo "analyzer_failed=$ANALYZER_FAILED" >> $GITHUB_OUTPUT
            echo "analyzer_skipped=$ANALYZER_SKIPPED" >> $GITHUB_OUTPUT
            echo "analyzer_failed_sites=$ANALYZER_FAILED_SITES" >> $GITHUB_OUTPUT
            
            echo "✅ 执行摘要已保存到 status/workflow/master_workflow_summary.json"
          |||
        },
        {
          name: '配置Git并提交工作流摘要',
          run: |
            # 配置Git
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

            # 添加文件
            git add status/workflow/

            # 拉取远程更改，避免推送冲突
            git pull --rebase origin main || echo "拉取远程仓库失败，尝试继续提交"

            # 提交更改
            if git diff --staged --quiet; then
              echo "没有变更需要提交"
            else
              git commit -m "📊 自动更新: 主工作流执行摘要 (${{ needs.setup.outputs.date }})"
              git push
              echo "✅ 成功提交并推送工作流摘要"
            fi
          |||
        }
      ]
    },
    
    // 通知完成任务
    notify_completion: {
      name: '通知完成',
      needs: ['setup', 'update_proxy_pool', 'crawl', 'analyze', 'update_dashboard', 'workflow_summary'],
      'if': 'always()',
      'runs-on': params.runtime.runner,
      steps: [
        utils.generateCheckoutStep(),
        utils.generatePythonSetupStep(params.runtime.python_version, true),
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
                "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}",
                "crawler_stats": {
                  "success": "${{ needs.workflow_summary.outputs.crawler_success || '0' }}",
                  "failed": "${{ needs.workflow_summary.outputs.crawler_failed || '0' }}",
                  "skipped": "${{ needs.workflow_summary.outputs.crawler_skipped || '0' }}",
                  "failed_sites": "${{ needs.workflow_summary.outputs.crawler_failed_sites || '' }}"
                },
                "analyzer_stats": {
                  "success": "${{ needs.workflow_summary.outputs.analyzer_success || '0' }}",
                  "failed": "${{ needs.workflow_summary.outputs.analyzer_failed || '0' }}",
                  "skipped": "${{ needs.workflow_summary.outputs.analyzer_skipped || '0' }}",
                  "failed_sites": "${{ needs.workflow_summary.outputs.analyzer_failed_sites || '' }}"
                }
              }
            }
            EOF
            
            # 准备通知内容
            TITLE="📢 Universal Scraper 工作流执行报告"
            DATE="${{ needs.setup.outputs.date }}"
            RUN_URL="${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            
            # 汇总数据
            CRAWLER_SUCCESS="${{ needs.workflow_summary.outputs.crawler_success || '0' }}"
            CRAWLER_FAILED="${{ needs.workflow_summary.outputs.crawler_failed || '0' }}"
            CRAWLER_SKIPPED="${{ needs.workflow_summary.outputs.crawler_skipped || '0' }}"
            CRAWLER_FAILED_SITES="${{ needs.workflow_summary.outputs.crawler_failed_sites || '' }}"
            
            ANALYZER_SUCCESS="${{ needs.workflow_summary.outputs.analyzer_success || '0' }}"
            ANALYZER_FAILED="${{ needs.workflow_summary.outputs.analyzer_failed || '0' }}"
            ANALYZER_SKIPPED="${{ needs.workflow_summary.outputs.analyzer_skipped || '0' }}"
            ANALYZER_FAILED_SITES="${{ needs.workflow_summary.outputs.analyzer_failed_sites || '' }}"
            
            # 生成通知内容
            cat > temp-notification/notification_content.md << EOF
            ### $TITLE
            
            **数据日期:** $DATE
            
            **爬虫结果:**
            - 成功: $CRAWLER_SUCCESS
            - 失败: $CRAWLER_FAILED
            - 跳过: $CRAWLER_SKIPPED
            EOF
            
            if [ -n "$CRAWLER_FAILED_SITES" ]; then
              echo "- 失败站点:$CRAWLER_FAILED_SITES" >> temp-notification/notification_content.md
            fi
            
            cat >> temp-notification/notification_content.md << EOF
            
            **分析结果:**
            - 成功: $ANALYZER_SUCCESS
            - 失败: $ANALYZER_FAILED
            - 跳过: $ANALYZER_SKIPPED
            EOF
            
            if [ -n "$ANALYZER_FAILED_SITES" ]; then
              echo "- 失败站点:$ANALYZER_FAILED_SITES" >> temp-notification/notification_content.md
            fi
            
            echo -e "\n[查看工作流详情]($RUN_URL)" >> temp-notification/notification_content.md
            
            # 发送通知
            echo "📢 发送主工作流完成通知..."
            python scripts/notify.py --file "temp-notification/master_workflow_status.json" --site "主工作流" --content "$(cat temp-notification/notification_content.md)"
          |||
        }
      ]
    }
  }
}
