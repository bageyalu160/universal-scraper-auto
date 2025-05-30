// 爬虫工作流模板 - Jsonnet版本 (增强版)

local params = import 'params.libsonnet';
local utils = import 'utils.libsonnet';

// 外部参数
local site_id = std.extVar('site_id');
local site_config = std.parseJson(std.extVar('site_config'));
local global_config = std.parseJson(std.extVar('global_config'));

// 站点信息
local site_name = utils.getSiteName(site_config, site_id);

// 爬取配置
local scraping_config = utils.getConfigSection(site_config, 'scraping', {});

// 引擎类型
local engine = utils.getConfigValue(scraping_config, 'engine', 'custom');

// 确定依赖项
local dependencies = utils.getCrawlerDependencies(engine, params.dependencies);

// 缓存配置
local cache_config = utils.generateCacheConfig('crawler', site_id, engine);

// 超时设置
local crawl_timeout = utils.getJobTimeout('crawl', global_config);
local setup_timeout = utils.getJobTimeout('setup', global_config);

// 错误处理策略
local crawl_error_strategy = utils.getErrorHandlingStrategy('crawl', global_config);

// 环境变量
local workflow_env = utils.generateWorkflowEnv('crawler', global_config) + {
  SITE_ID: site_id,
  ENGINE_TYPE: engine
};

// 确定cron表达式
local schedule = if std.objectHas(scraping_config, 'schedule') then
  scraping_config.schedule
else
  params.schedules.master;

// 确定输出文件名
local output_filename = utils.getConfigValue(site_config, 'output.filename', 
                         utils.getConfigValue(site_config, 'site_info.output_filename', 
                         site_id + '_data.json'));

// 检查是否需要运行分析
local run_analysis = utils.getConfigValue(site_config, 'analysis.enabled', true);

// 检查代理配置
local proxy_config = utils.getConfigSection(scraping_config, 'proxy', {});
local use_proxy = utils.getConfigValue(proxy_config, 'enabled', false);

// 环境变量
local env_vars = if std.objectHas(scraping_config, 'api') && std.objectHas(scraping_config.api, 'key_env') then
  [{
    name: scraping_config.api.key_env,
    secret: scraping_config.api.key_env
  }]
else
  [];

{
  name: site_name + ' (' + site_id + ') 爬虫',
  'run-name': '🕷️ ' + site_name + ' (' + site_id + ') 爬虫 #${{ github.run_number }} (${{ github.actor }})',
  
  // 定义工作流的权限
  permissions: {
    contents: 'write',  // 允许推送到仓库
    actions: 'write'    // 允许触发其他工作流
  },
  
  on: utils.generateWorkflowDispatchTrigger({
    date: {
      description: '数据日期 (留空则使用当前日期)',
      required: false,
      type: 'string'
    },
    use_proxy: {
      description: '是否使用代理',
      required: false,
      type: 'boolean',
      default: use_proxy
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
  }) + utils.generateScheduleTrigger(schedule),
  
  // 并发控制 - 避免相同站点的任务并行运行
  concurrency: utils.generateConcurrencyConfig('crawler', site_id),
  
  // 全局环境变量
  env: workflow_env,
  
  jobs: {
    // 预检查作业
    'pre-check': {
      name: '环境与配置检查',
      'runs-on': params.runtime.runner,
      'timeout-minutes': setup_timeout,
      outputs: {
        run_date: '${{ steps.prepare_env.outputs.date }}',
        cache_key: '${{ steps.prepare_env.outputs.cache_key }}',
        site_config_valid: '${{ steps.validate_config.outputs.valid }}',
        use_proxy: '${{ steps.prepare_env.outputs.use_proxy }}'
      },
      steps: [
        utils.generateCheckoutStep(),
        {
          name: '准备环境变量',
          id: 'prepare_env',
          run: |||
            # 设置运行日期
            if [ -n "${{ github.event.inputs.date }}" ]; then
              echo "使用指定日期: ${{ github.event.inputs.date }}"
              echo "date=${{ github.event.inputs.date }}" >> $GITHUB_OUTPUT
            else
              echo "使用当前日期"
              echo "date=$(date +%%Y-%%m-%%d)" >> $GITHUB_OUTPUT
            fi
            
            # 生成缓存键
            if [ -f "requirements.txt" ]; then
              HASH=$(sha256sum requirements.txt | cut -d ' ' -f 1 | head -c 8)
              echo "cache_key=deps-%(site_id)s-$HASH-v1" >> $GITHUB_OUTPUT
            else
              echo "cache_key=deps-%(site_id)s-default-v1" >> $GITHUB_OUTPUT
            fi
            
            # 设置是否使用代理
            USE_PROXY="${{ github.event.inputs.use_proxy || '%(use_proxy)s' }}"
            echo "use_proxy=$USE_PROXY" >> $GITHUB_OUTPUT
            echo "代理使用设置: $USE_PROXY"
          ||| % {site_id: site_id, use_proxy: use_proxy}
        },
        {
          name: '验证站点配置',
          id: 'validate_config',
          run: |||
            if [ -f "config/sites/%(site_id)s.yaml" ]; then
              echo "✅ 站点配置有效"
              echo "valid=true" >> $GITHUB_OUTPUT
            else
              echo "❌ 站点配置文件不存在"
              echo "valid=false" >> $GITHUB_OUTPUT
              exit 1
            fi
          ||| % {site_id: site_id}
        }
      ]
    },
    
    // 检查代理可用性（如果需要）
    'check-proxy': {
      name: '检查代理可用性',
      needs: ['pre-check'],
      'if': "needs.pre-check.outputs.use_proxy == 'true'",
      'runs-on': params.runtime.runner,
      steps: [
        utils.generateCheckoutStep(0),
        utils.generatePythonSetupStep(params.runtime.python_version, true),
        {
          name: '安装依赖',
          run: |||
            python -m pip install --upgrade pip
            if [ -f requirements.txt ]; then
              pip install -r requirements.txt
            else
              echo "安装必要的依赖..."
              pip install requests pyyaml
            fi
          |||
        },
        utils.generateDirectorySetupStep(['data/proxies', 'status/proxies', 'logs']),
        {
          name: '检查代理池状态',
          id: 'check_proxy_pool',
          run: |||
            # 检查代理状态文件是否存在
            if [ -f "status/proxies/pool_status.json" ]; then
              echo "找到代理池状态文件"
              
              # 检查可用代理数量
              VALID_COUNT=$(jq '.valid_count' status/proxies/pool_status.json)
              THRESHOLD=5
              
              echo "当前有效代理数: $VALID_COUNT"
              echo "最低需求阈值: $THRESHOLD"
              
              if [ "$VALID_COUNT" -ge "$THRESHOLD" ]; then
                echo "✅ 代理池状态良好，有足够的代理"
                echo "sufficient=true" >> $GITHUB_OUTPUT
              else
                echo "⚠️ 代理池中的有效代理不足，需要更新"
                echo "sufficient=false" >> $GITHUB_OUTPUT
              fi
            else
              echo "⚠️ 未找到代理池状态文件，需要初始化代理池"
              echo "sufficient=false" >> $GITHUB_OUTPUT
            fi
          |||
        },
        {
          name: '更新代理池',
          'if': "steps.check_proxy_pool.outputs.sufficient == 'false'",
          run: |||
            echo "开始更新代理池..."
            
            # 尝试执行更新，如果失败则尝试恢复
            python scripts/proxy_manager.py update --min-count 10 --timeout 10
            
            # 检查更新后的状态
            if [ -f "status/proxies/pool_status.json" ]; then
              valid_count=$(jq '.valid_count' status/proxies/pool_status.json)
              echo "更新后的有效代理数: $valid_count"
              
              # 如果更新后代理仍然不足，尝试恢复备份
              if [ "$valid_count" -lt "5" ] && [ -f "data/proxies/proxy_pool_backup.json" ]; then
                echo "⚠️ 更新后代理仍然不足，尝试恢复备份..."
                cp data/proxies/proxy_pool_backup.json data/proxies/proxy_pool.json
                python scripts/proxy_manager.py validate --timeout 5
                
                if [ -f "status/proxies/pool_status.json" ]; then
                  valid_count=$(jq '.valid_count' status/proxies/pool_status.json)
                  echo "恢复备份后的有效代理数: $valid_count"
                fi
              fi
              
              echo "更新后的有效代理数: $valid_count"
            else
              echo "⚠️ 更新后仍未找到代理池状态文件"
            fi
          |||
        },
        utils.generateGitCommitStep(
          ["data/proxies/", "status/proxies/"],
          "🔄 爬虫任务前的代理池更新 (站点: " + site_id + ")"
        )
      ]
    },
    
    // 爬虫作业
    crawl: {
      name: '运行爬虫',
      needs: ['pre-check', 'check-proxy'],
      'if': "always() && needs.pre-check.outputs.site_config_valid == 'true' && (needs.check-proxy.result == 'success' || needs.pre-check.outputs.use_proxy != 'true')",
      'runs-on': params.runtime.runner,
      'timeout-minutes': crawl_timeout,
      strategy: {
        'fail-fast': crawl_error_strategy['fail-fast']
      },
      env: {
        RUN_DATE: '${{ needs.pre-check.outputs.run_date }}',
        USE_PROXY: '${{ needs.pre-check.outputs.use_proxy }}'
      },
      steps: [
        utils.generateCheckoutStep(),
        utils.generatePythonSetupStep(params.runtime.python_version, true),
        utils.generateCacheStep(cache_config, 'requirements.txt'),
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
        utils.generateDirectorySetupStep(['data/' + site_id, 'status/' + site_id, 'logs']),
        {
          name: '运行爬虫',
          id: 'run_scraper',
          'continue-on-error': true,
          env: {
            [env_var.name]: '${{ secrets.' + env_var.secret + ' }}'
            for env_var in env_vars
          },
          run: |||
            echo "🕷️ 开始爬取数据: %(site_id)s"
            echo "📅 运行日期: $RUN_DATE"
            echo "🔄 使用代理: $USE_PROXY"
            
            # 构建命令参数
            PROXY_ARG=""
            if [ "$USE_PROXY" = "true" ] && [ -f "data/proxies/proxy_pool.json" ]; then
              PROXY_ARG="--proxy-file data/proxies/proxy_pool.json"
              echo "📋 使用代理池文件"
            fi
            
            # 执行爬虫
            python scripts/scraper.py \
              --site %(site_id)s \
              --date "$RUN_DATE" \
              --output data/%(site_id)s/%(output_filename)s \
              --status status/%(site_id)s/status.json \
              --log-file logs/%(site_id)s_$RUN_DATE.log \
              $PROXY_ARG
            
            # 检查结果
            if [ -f "data/%(site_id)s/%(output_filename)s" ]; then
              echo "scraper_success=true" >> $GITHUB_OUTPUT
              echo "✅ 爬虫执行成功"
            else
              echo "scraper_success=false" >> $GITHUB_OUTPUT
              echo "❌ 爬虫执行失败或无数据"
            fi
          ||| % {
            site_id: site_id,
            output_filename: output_filename
          }
        },
        {
          name: '上传数据文件',
          'if': "steps.run_scraper.outputs.scraper_success == 'true'",
          uses: 'actions/upload-artifact@v4',
          with: {
            name: site_id + '-data-${{ needs.pre-check.outputs.run_date }}',
            path: 'data/' + site_id + '/' + output_filename,
            'retention-days': 7,
            'if-no-files-found': 'warn'
          }
        },
        {
          name: '上传状态文件',
          uses: 'actions/upload-artifact@v4',
          with: {
            name: site_id + '-status-${{ needs.pre-check.outputs.run_date }}',
            path: 'status/' + site_id + '/status.json',
            'retention-days': 7,
            'if-no-files-found': 'warn'
          }
        },
        {
          name: '上传日志文件',
          uses: 'actions/upload-artifact@v4',
          with: {
            name: site_id + '-logs-${{ needs.pre-check.outputs.run_date }}',
            path: 'logs/' + site_id + '_${{ needs.pre-check.outputs.run_date }}.log',
            'retention-days': 3,
            'if-no-files-found': 'warn'
          }
        },
        {
          name: '配置Git并提交更改',
          run: |
            # 配置Git
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

            # 添加文件
            git add data/%(site_id)s/
            git add status/%(site_id)s/

            # 拉取远程更改，避免推送冲突
            git pull --rebase origin main || echo "拉取远程仓库失败，尝试继续提交"

            # 提交更改
            if git diff --staged --quiet; then
              echo "没有变更需要提交"
            else
              git commit -m "🤖 自动更新: %(site_name)s爬虫结果 ($RUN_DATE)"
              git push
              echo "✅ 成功提交并推送爬虫结果"
            fi
          ||| % {site_id: site_id, site_name: site_name}
        },
        // 添加工作流状态报告
        utils.generateWorkflowStatusStep('crawler', site_id)
      ]
    }
  }
}
