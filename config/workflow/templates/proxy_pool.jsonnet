// 代理池管理工作流模板 - Jsonnet版本 (增强版)

local params = import 'params.libsonnet';
local utils = import 'utils.libsonnet';

// 外部参数
local global_config = std.parseJson(std.extVar('global_config'));

// 确定依赖项
local dependencies = params.proxy_pool.dependencies;

// 代理池配置
local proxy_config = global_config.proxy;
local pool_size = if std.objectHas(proxy_config, 'pool_size') then
  proxy_config.pool_size
else
  20;

local update_interval = if std.objectHas(proxy_config, 'update_interval') then
  proxy_config.update_interval
else
  params.global.default_cron;

// 最小代理数量阈值
local min_proxy_threshold = if std.objectHas(proxy_config, 'min_threshold') then
  proxy_config.min_threshold
else
  5;

{
  name: '代理池管理',
  'run-name': '🔄 代理池管理 #${{ github.run_number }} (${{ github.actor }})',
  
  on: {
    workflow_dispatch: {
      inputs: {
        action: {
          description: '执行操作',
          required: true,
          type: 'choice',
          options: [
            'update',
            'validate',
            'clean',
            'rebuild'
          ],
          default: 'update'
        },
        pool_size: {
          description: '代理池大小 (仅适用于更新操作)',
          required: false,
          type: 'number',
          default: pool_size
        },
        force_update: {
          description: '强制更新代理池',
          required: false,
          type: 'boolean',
          default: false
        }
      }
    },
    schedule: [
      {cron: update_interval}
    ],
    workflow_call: {
      inputs: {
        action: {
          description: '执行操作',
          required: false,
          type: 'string',
          default: 'update'
        }
      }
    }
  },
  
  // 并发控制
  concurrency: {
    group: 'proxy-pool-management',
    'cancel-in-progress': true
  },
  
  jobs: {
    // 预检查作业
    'pre-check': {
      name: '代理池状态检查',
      'runs-on': params.global.runner,
      outputs: {
        current_status: '${{ steps.check_status.outputs.status }}',
        valid_count: '${{ steps.check_status.outputs.valid_count }}',
        needs_update: '${{ steps.check_status.outputs.needs_update }}',
        action: '${{ steps.determine_action.outputs.action }}'
      },
      steps: [
        {
          name: '检出代码',
          uses: 'actions/checkout@v4'
        },
        {
          name: '创建必要目录',
          run: |||
            mkdir -p data/proxies
            mkdir -p status/proxies
            mkdir -p logs
          |||
        },
        {
          name: '检查当前代理池状态',
          id: 'check_status',
          run: |||
            echo "🔍 检查代理池状态..."
            
            # 初始化变量
            VALID_COUNT=0
            STATUS="unknown"
            NEEDS_UPDATE="false"
            
            # 检查状态文件
            if [ -f "status/proxies/pool_status.json" ]; then
              echo "✅ 发现代理池状态文件"
              
              # 解析状态信息
              if command -v jq >/dev/null 2>&1; then
                VALID_COUNT=$(jq -r '.stats.valid_count // 0' status/proxies/pool_status.json)
                LAST_UPDATE=$(jq -r '.last_update // ""' status/proxies/pool_status.json)
                STATUS=$(jq -r '.status // "unknown"' status/proxies/pool_status.json)
              else
                # 没有jq时的简单解析
                VALID_COUNT=$(grep -o '"valid_count":[0-9]*' status/proxies/pool_status.json | grep -o '[0-9]*' | head -1)
                if [ -z "$VALID_COUNT" ]; then
                  VALID_COUNT=0
                fi
              fi
              
              echo "当前有效代理数: $VALID_COUNT"
              echo "当前状态: $STATUS"
              
              # 判断是否需要更新
              if [ "$VALID_COUNT" -lt "%(min_threshold)d" ]; then
                NEEDS_UPDATE="true"
                echo "⚠️ 代理数量不足，需要更新"
              else
                echo "✅ 代理数量充足"
              fi
            else
              echo "⚠️ 未找到代理池状态文件"
              STATUS="missing"
              NEEDS_UPDATE="true"
            fi
            
            # 检查代理池文件
            if [ ! -f "data/proxies/proxy_pool.json" ]; then
              echo "⚠️ 代理池文件不存在"
              STATUS="missing"
              NEEDS_UPDATE="true"
            fi
            
            # 设置输出
            echo "status=$STATUS" >> $GITHUB_OUTPUT
            echo "valid_count=$VALID_COUNT" >> $GITHUB_OUTPUT
            echo "needs_update=$NEEDS_UPDATE" >> $GITHUB_OUTPUT
          ||| % {min_threshold: min_proxy_threshold}
        },
        {
          name: '确定执行动作',
          id: 'determine_action',
          run: |||
            # 获取输入动作
            INPUT_ACTION="${{ github.event.inputs.action || inputs.action || 'update' }}"
            FORCE_UPDATE="${{ github.event.inputs.force_update || 'false' }}"
            NEEDS_UPDATE="${{ steps.check_status.outputs.needs_update }}"
            
            echo "输入动作: $INPUT_ACTION"
            echo "强制更新: $FORCE_UPDATE"
            echo "需要更新: $NEEDS_UPDATE"
            
            # 确定最终动作
            if [ "$INPUT_ACTION" = "update" ] && [ "$NEEDS_UPDATE" = "false" ] && [ "$FORCE_UPDATE" = "false" ]; then
              FINAL_ACTION="skip"
              echo "📋 代理池状态良好，跳过更新"
            else
              FINAL_ACTION="$INPUT_ACTION"
              echo "📋 将执行动作: $FINAL_ACTION"
            fi
            
            echo "action=$FINAL_ACTION" >> $GITHUB_OUTPUT
          |||
        }
      ]
    },
    
    // 代理池管理作业
    manage_proxy_pool: {
      name: '执行代理池管理',
      needs: ['pre-check'],
      'if': "needs.pre-check.outputs.action != 'skip'",
      'runs-on': params.global.runner,
      'timeout-minutes': 30,
      steps: [
        {
          name: '检出代码',
          uses: 'actions/checkout@v4',
          with: {
            'fetch-depth': 0
          }
        },
        {
          name: '设置Python环境',
          uses: 'actions/setup-python@v5',
          with: {
            'python-version': params.global.python_version,
            cache: 'pip'
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
              pip install %(dependencies)s
            fi
          ||| % {dependencies: dependencies}
        },
        {
          name: '创建代理池目录',
          run: |||
            mkdir -p data/proxies
            mkdir -p status/proxies
            mkdir -p logs
          |||
        },
        {
          name: '备份现有代理池',
          'if': "needs.pre-check.outputs.current_status != 'missing'",
          run: |||
            if [ -f "data/proxies/proxy_pool.json" ]; then
              cp data/proxies/proxy_pool.json data/proxies/proxy_pool_backup_$(date +%Y%m%d_%H%M%S).json
              echo "✅ 已备份现有代理池"
            fi
            
            if [ -f "status/proxies/pool_status.json" ]; then
              cp status/proxies/pool_status.json status/proxies/pool_status_backup_$(date +%Y%m%d_%H%M%S).json
              echo "✅ 已备份现有状态文件"
            fi
          |||
        },
        {
          name: '更新代理池',
          'if': "needs.pre-check.outputs.action == 'update' || needs.pre-check.outputs.action == 'rebuild'",
          id: 'update_proxy',
          'continue-on-error': true,
          run: |||
            echo "🔄 开始更新代理池..."
            
            ACTION="${{ needs.pre-check.outputs.action }}"
            POOL_SIZE="${{ github.event.inputs.pool_size || '%(pool_size)d' }}"
            
            # 设置日志文件
            LOG_FILE="logs/proxy_update_$(date +%%Y%%m%%d_%%H%%M%%S).log"
            
            # 执行更新
            if [ "$ACTION" = "rebuild" ]; then
              echo "🔧 重建代理池..."
              python scripts/proxy_manager.py rebuild \
                --output data/proxies/proxy_pool.json \
                --status status/proxies/pool_status.json \
                --size "$POOL_SIZE" \
                --log-file "$LOG_FILE" \
                --validate
            else
              echo "🔄 更新代理池..."
              python scripts/proxy_manager.py update \
                --output data/proxies/proxy_pool.json \
                --status status/proxies/pool_status.json \
                --size "$POOL_SIZE" \
                --log-file "$LOG_FILE" \
                --validate
            fi
            
            # 检查执行结果
            if [ $? -eq 0 ]; then
              echo "update_success=true" >> $GITHUB_OUTPUT
              echo "✅ 代理池更新成功"
            else
              echo "update_success=false" >> $GITHUB_OUTPUT
              echo "❌ 代理池更新失败"
            fi
          ||| % {pool_size: pool_size}
        },
        {
          name: '验证代理池',
          'if': "needs.pre-check.outputs.action == 'validate' || steps.update_proxy.outputs.update_success == 'true'",
          id: 'validate_proxy',
          'continue-on-error': true,
          run: |||
            echo "🔍 验证代理池..."
            
            if [ ! -f "data/proxies/proxy_pool.json" ]; then
              echo "❌ 代理池文件不存在，无法验证"
              echo "validate_success=false" >> $GITHUB_OUTPUT
              exit 1
            fi
            
            # 设置日志文件
            LOG_FILE="logs/proxy_validate_$(date +%%Y%%m%%d_%%H%%M%%S).log"
            
            # 执行验证
            python scripts/proxy_manager.py validate \
              --input data/proxies/proxy_pool.json \
              --output data/proxies/proxy_pool_validated.json \
              --status status/proxies/pool_status.json \
              --log-file "$LOG_FILE"
            
            # 检查验证结果
            if [ $? -eq 0 ] && [ -f "data/proxies/proxy_pool_validated.json" ]; then
              # 替换原始代理池文件
              mv data/proxies/proxy_pool_validated.json data/proxies/proxy_pool.json
              echo "validate_success=true" >> $GITHUB_OUTPUT
              echo "✅ 代理池验证成功"
            else
              echo "validate_success=false" >> $GITHUB_OUTPUT
              echo "❌ 代理池验证失败"
            fi
          |||
        },
        {
          name: '清理代理池',
          'if': "needs.pre-check.outputs.action == 'clean'",
          id: 'clean_proxy',
          'continue-on-error': true,
          run: |||
            echo "🧹 清理代理池..."
            
            if [ ! -f "data/proxies/proxy_pool.json" ]; then
              echo "❌ 代理池文件不存在，无法清理"
              echo "clean_success=false" >> $GITHUB_OUTPUT
              exit 1
            fi
            
            # 设置日志文件
            LOG_FILE="logs/proxy_clean_$(date +%%Y%%m%%d_%%H%%M%%S).log"
            
            # 执行清理
            python scripts/proxy_manager.py clean \
              --input data/proxies/proxy_pool.json \
              --output data/proxies/proxy_pool_cleaned.json \
              --status status/proxies/pool_status.json \
              --log-file "$LOG_FILE"
            
            # 检查清理结果
            if [ $? -eq 0 ] && [ -f "data/proxies/proxy_pool_cleaned.json" ]; then
              # 替换原始代理池文件
              mv data/proxies/proxy_pool_cleaned.json data/proxies/proxy_pool.json
              echo "clean_success=true" >> $GITHUB_OUTPUT
              echo "✅ 代理池清理成功"
            else
              echo "clean_success=false" >> $GITHUB_OUTPUT
              echo "❌ 代理池清理失败"
            fi
          |||
        },
        {
          name: '恢复代理池（如果操作失败）',
          'if': "failure() && needs.pre-check.outputs.current_status != 'missing'",
          run: |||
            echo "💡 尝试恢复代理池..."
            
            # 查找最新的备份文件
            LATEST_BACKUP=$(ls -t data/proxies/proxy_pool_backup_*.json 2>/dev/null | head -1)
            LATEST_STATUS_BACKUP=$(ls -t status/proxies/pool_status_backup_*.json 2>/dev/null | head -1)
            
            if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP" ]; then
              cp "$LATEST_BACKUP" data/proxies/proxy_pool.json
              echo "✅ 已从备份恢复代理池文件"
            fi
            
            if [ -n "$LATEST_STATUS_BACKUP" ] && [ -f "$LATEST_STATUS_BACKUP" ]; then
              cp "$LATEST_STATUS_BACKUP" status/proxies/pool_status.json
              echo "✅ 已从备份恢复状态文件"
            fi
            
            # 清理备份文件（保留最新的3个）
            ls -t data/proxies/proxy_pool_backup_*.json 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
            ls -t status/proxies/pool_status_backup_*.json 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
          |||
        },
        {
          name: '生成最终状态报告',
          id: 'final_status',
          run: |||
            echo "📊 生成最终状态报告..."
            
            # 检查最终状态
            if [ -f "status/proxies/pool_status.json" ]; then
              if command -v jq >/dev/null 2>&1; then
                FINAL_VALID_COUNT=$(jq -r '.stats.valid_count // 0' status/proxies/pool_status.json)
                FINAL_TOTAL_COUNT=$(jq -r '.stats.total_count // 0' status/proxies/pool_status.json)
                FINAL_STATUS=$(jq -r '.status // "unknown"' status/proxies/pool_status.json)
              else
                FINAL_VALID_COUNT=$(grep -o '"valid_count":[0-9]*' status/proxies/pool_status.json | grep -o '[0-9]*' | head -1)
                FINAL_TOTAL_COUNT=$(grep -o '"total_count":[0-9]*' status/proxies/pool_status.json | grep -o '[0-9]*' | head -1)
                FINAL_STATUS="updated"
              fi
              
              echo "最终有效代理数: $FINAL_VALID_COUNT"
              echo "总代理数: $FINAL_TOTAL_COUNT"
              echo "最终状态: $FINAL_STATUS"
              
              # 设置输出
              echo "final_valid_count=$FINAL_VALID_COUNT" >> $GITHUB_OUTPUT
              echo "final_total_count=$FINAL_TOTAL_COUNT" >> $GITHUB_OUTPUT
              echo "final_status=$FINAL_STATUS" >> $GITHUB_OUTPUT
              
              # 判断是否成功
              if [ "$FINAL_VALID_COUNT" -ge "%(min_threshold)d" ]; then
                echo "operation_success=true" >> $GITHUB_OUTPUT
                echo "✅ 代理池操作成功完成"
              else
                echo "operation_success=false" >> $GITHUB_OUTPUT
                echo "⚠️ 代理池操作完成但代理数量不足"
              fi
            else
              echo "operation_success=false" >> $GITHUB_OUTPUT
              echo "❌ 未找到最终状态文件"
            fi
          ||| % {min_threshold: min_proxy_threshold}
        },
        {
          name: '上传代理池文件',
          'if': "always()",
          uses: 'actions/upload-artifact@v4',
          with: {
            name: 'proxy-pool-${{ github.run_number }}',
            path: |||
              data/proxies/proxy_pool.json
              status/proxies/pool_status.json
              logs/proxy_*.log
            |||,
            'retention-days': 7
          }
        },
        {
          name: '提交代理池更新',
          'if': "steps.final_status.outputs.operation_success == 'true'",
          run: |||
            # 配置Git
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            
            # 添加文件
            git add data/proxies/proxy_pool.json
            git add status/proxies/pool_status.json
            
            # 提交更改
            if git diff --staged --quiet; then
              echo "没有代理池变更，无需提交"
            else
              ACTION="${{ needs.pre-check.outputs.action }}"
              VALID_COUNT="${{ steps.final_status.outputs.final_valid_count }}"
              
              git commit -m "🤖 自动更新: 代理池管理 (动作: $ACTION, 有效代理: $VALID_COUNT)"
              git push
              echo "✅ 成功提交代理池更新"
            fi
          |||
        }
      ]
    },
    
    // 通知作业
    notify: {
      name: '发送操作通知',
      needs: ['pre-check', 'manage_proxy_pool'],
      'if': 'always()',
      'runs-on': params.global.runner,
      steps: [
        {
          name: '准备通知内容',
          id: 'prepare_message',
          run: |||
            ACTION="${{ needs.pre-check.outputs.action }}"
            
            if [ "$ACTION" = "skip" ]; then
              echo "status=skipped" >> $GITHUB_OUTPUT
              echo "message=代理池状态良好，跳过更新操作" >> $GITHUB_OUTPUT
            elif [ "${{ needs.manage_proxy_pool.result }}" = "success" ]; then
              VALID_COUNT="${{ needs.manage_proxy_pool.outputs.final_valid_count || '未知' }}"
              echo "status=success" >> $GITHUB_OUTPUT
              echo "message=代理池$ACTION操作成功完成，当前有效代理: $VALID_COUNT" >> $GITHUB_OUTPUT
            else
              echo "status=failure" >> $GITHUB_OUTPUT
              echo "message=代理池$ACTION操作失败" >> $GITHUB_OUTPUT
            fi
          |||
        }
      ]
    }
  }
}
