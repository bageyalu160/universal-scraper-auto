// 代理池管理工作流模板 - Jsonnet版本 (增强版)

local params = import 'params.libsonnet';
local utils = import 'utils.libsonnet';

// 外部参数
local global_config = std.parseJson(std.extVar('global_config'));

// 确定依赖项
local dependencies = params.dependencies.proxy_pool;

// 代理池配置
local proxy_config = global_config.proxy;
local pool_size = utils.getConfigValue(proxy_config, 'pool_size', 20);

// 缓存配置
local cache_config = utils.generateCacheConfig('proxy_pool', 'main');

// 超时设置
local proxy_timeout = utils.getJobTimeout('proxy_pool', global_config);

// 错误处理策略
local proxy_error_strategy = utils.getErrorHandlingStrategy('proxy_validation', global_config);

// 环境变量
local workflow_env = utils.generateWorkflowEnv('proxy_pool', global_config);

// 更新间隔
local update_interval = utils.getConfigValue(proxy_config, 'update_interval', params.schedules.master);

// 最小代理数量阈值
local min_proxy_threshold = utils.getConfigValue(proxy_config, 'min_threshold', 5);

{
  name: '代理池管理',
  'run-name': '🔄 代理池管理 #${{ github.run_number }} (${{ github.actor }})',
  
  // 定义工作流的权限
  permissions: {
    contents: 'write',  // 允许推送到仓库
    actions: 'write'    // 允许触发其他工作流
  },
  
  on: utils.generateWorkflowDispatchTrigger({
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
  }) + utils.generateScheduleTrigger(update_interval) + {
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
  concurrency: utils.generateConcurrencyConfig('proxy_pool', 'main'),
  
  // 全局环境变量
  env: workflow_env,
  
  jobs: {
    // 预检查作业
    'pre-check': {
      name: '代理池状态检查',
      'runs-on': params.runtime.runner,
      'timeout-minutes': proxy_timeout / 2,
      outputs: {
        current_status: '${{ steps.check_status.outputs.status }}',
        valid_count: '${{ steps.check_status.outputs.valid_count }}',
        needs_update: '${{ steps.check_status.outputs.needs_update }}',
        action: '${{ steps.determine_action.outputs.action }}'
      },
      steps: [
        utils.generateCheckoutStep(),
        utils.generateDirectorySetupStep(['data/proxies', 'status/proxies', 'logs', 'proxy_pool/cache']),
        utils.generatePythonSetupStep(params.runtime.python_version, true),
        utils.generateCacheStep(cache_config, '**/requirements.txt, config/settings.yaml'),
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
            if [ -f status/proxies/pool_status.json ]; then
              echo "✅ 发现代理池状态文件"
              
              # 解析状态信息
              if command -v jq &> /dev/null; then
                VALID_COUNT=$(jq -r '.valid_count // 0' status/proxies/pool_status.json)
                TOTAL_COUNT=$(jq -r '.total_count // 0' status/proxies/pool_status.json)
                LAST_UPDATE=$(jq -r '.last_update // "unknown"' status/proxies/pool_status.json)
                STATUS=$(jq -r '.status // "unknown"' status/proxies/pool_status.json)
              else
                VALID_COUNT=$(grep -o '"valid_count":[0-9]*' status/proxies/pool_status.json | grep -o '[0-9]*' | head -1)
                TOTAL_COUNT=$(grep -o '"total_count":[0-9]*' status/proxies/pool_status.json | grep -o '[0-9]*' | head -1)
                LAST_UPDATE=$(grep -o '"last_update":"[^"]*"' status/proxies/pool_status.json | cut -d'"' -f4)
                STATUS=$(grep -o '"status":"[^"]*"' status/proxies/pool_status.json | cut -d'"' -f4)
              fi
              
              echo "当前状态: $STATUS"
              echo "有效代理数: $VALID_COUNT"
              echo "总代理数: $TOTAL_COUNT"
              echo "最后更新: $LAST_UPDATE"
              
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
              echo "⚠️ 未找到代理池文件"
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
            
            # 确定最终动作
            if [ "$INPUT_ACTION" = "update" ] && [ "$NEEDS_UPDATE" = "false" ] && [ "$FORCE_UPDATE" != "true" ]; then
              FINAL_ACTION="skip"
              echo "✅ 代理池状态良好，跳过更新"
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
      'runs-on': params.runtime.runner,
      'timeout-minutes': proxy_timeout,
      'continue-on-error': proxy_error_strategy['continue-on-error'],
      outputs: {
        final_valid_count: '${{ steps.final_status.outputs.final_valid_count }}',
        final_total_count: '${{ steps.final_status.outputs.final_total_count }}',
        final_status: '${{ steps.final_status.outputs.final_status }}',
        operation_success: '${{ steps.final_status.outputs.operation_success }}'
      },
      steps: [
        utils.generateCheckoutStep(0),
        utils.generatePythonSetupStep(params.runtime.python_version, true),
        utils.generateCacheStep(cache_config, '**/requirements.txt, config/settings.yaml'),
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
        utils.generateDirectorySetupStep(['data/proxies', 'status/proxies', 'logs']),
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
            
            # 确定代理池大小
            POOL_SIZE="${{ github.event.inputs.pool_size || '%(pool_size)d' }}"
            echo "目标代理池大小: $POOL_SIZE"
            
            # 执行更新
            ACTION="${{ needs.pre-check.outputs.action }}"
            if [ "$ACTION" = "rebuild" ]; then
              echo "🔨 重建代理池..."
              python scripts/proxy_manager.py rebuild --min-count $POOL_SIZE --timeout 30
            else
              echo "🔄 更新代理池..."
              python scripts/proxy_manager.py update --min-count $POOL_SIZE --timeout 30
            fi
            
            # 检查结果
            if [ $? -eq 0 ]; then
              echo "✅ 代理池更新成功"
            else
              echo "⚠️ 代理池更新过程中出现错误"
            fi
          ||| % {pool_size: pool_size}
        },
        {
          name: '验证代理池',
          'if': "needs.pre-check.outputs.action == 'validate' || needs.pre-check.outputs.action == 'update' || needs.pre-check.outputs.action == 'rebuild'",
          id: 'validate_proxy',
          'continue-on-error': true,
          run: |||
            echo "🔍 开始验证代理池..."
            
            # 执行验证
            python scripts/proxy_manager.py validate --timeout 15
            
            # 检查结果
            if [ $? -eq 0 ]; then
              echo "✅ 代理池验证成功"
            else
              echo "⚠️ 代理池验证过程中出现错误"
            fi
          |||
        },
        {
          name: '清理代理池',
          'if': "needs.pre-check.outputs.action == 'clean'",
          id: 'clean_proxy',
          'continue-on-error': true,
          run: |||
            echo "🧹 开始清理代理池..."
            
            # 执行清理
            python scripts/proxy_manager.py clean
            
            # 检查结果
            if [ $? -eq 0 ]; then
              echo "✅ 代理池清理成功"
            else
              echo "⚠️ 代理池清理过程中出现错误"
            fi
          |||
        },
        {
          name: '检查最终状态',
          id: 'final_status',
          run: |||
            echo "🔍 检查代理池最终状态..."
            
            # 检查状态文件
            if [ -f "status/proxies/pool_status.json" ]; then
              echo "✅ 发现代理池状态文件"
              
              # 解析状态信息
              if command -v jq &> /dev/null; then
                FINAL_VALID_COUNT=$(jq -r '.valid_count // 0' status/proxies/pool_status.json)
                FINAL_TOTAL_COUNT=$(jq -r '.total_count // 0' status/proxies/pool_status.json)
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
            'retention-days': 7,
            'if-no-files-found': 'warn'
          }
        },
        utils.generateGitCommitStep(
          ["data/proxies/proxy_pool.json", "status/proxies/pool_status.json"],
          "🤖 自动更新: 代理池管理 (动作: ${{ needs.pre-check.outputs.action }}, 有效代理: ${{ steps.final_status.outputs.final_valid_count }})"
        )
      ]
    },
    
    // 通知作业
    notify: {
      name: '发送操作通知',
      needs: ['pre-check', 'manage_proxy_pool'],
      'if': 'always()',
      'runs-on': params.runtime.runner,
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
