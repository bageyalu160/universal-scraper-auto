// 爬虫工作流模板 - Jsonnet版本 (增强版)

local params = import 'params.libsonnet';
local utils = import 'utils.libsonnet';

// 外部参数
local site_id = std.extVar('site_id');
local site_config = std.parseJson(std.extVar('site_config'));
local global_config = std.parseJson(std.extVar('global_config'));

// 站点信息
local site_name = if std.objectHas(site_config, 'site_info') && std.objectHas(site_config.site_info, 'name') then
  site_config.site_info.name
else
  site_id + ' 站点';

// 爬取配置
local scraping_config = if std.objectHas(site_config, 'scraping') then
  site_config.scraping
else
  {};

// 引擎类型
local engine = if std.objectHas(scraping_config, 'engine') then
  scraping_config.engine
else
  'custom';

// 确定依赖项
local dependencies = if engine == 'firecrawl' then
  params.crawler.dependencies.firecrawl
else if engine == 'playwright' then
  params.crawler.dependencies.playwright
else
  params.crawler.dependencies.default;

// 确定cron表达式
local schedule = if std.objectHas(scraping_config, 'schedule') then
  scraping_config.schedule
else
  params.global.default_cron;

// 确定输出文件名
local output_filename = if std.objectHas(site_config, 'output') && std.objectHas(site_config.output, 'filename') then
  site_config.output.filename
else if std.objectHas(site_config, 'site_info') && std.objectHas(site_config.site_info, 'output_filename') then
  site_config.site_info.output_filename
else
  site_id + '_data.json';

// 检查是否需要运行分析
local run_analysis = if std.objectHas(site_config, 'analysis') && std.objectHas(site_config.analysis, 'enabled') then
  site_config.analysis.enabled
else
  true;

// 检查代理配置
local proxy_config = if std.objectHas(scraping_config, 'proxy') then
  scraping_config.proxy
else
  {};
local use_proxy = if std.objectHas(proxy_config, 'enabled') then
  proxy_config.enabled
else
  false;

// 环境变量
local env_vars = if std.objectHas(scraping_config, 'api') && std.objectHas(scraping_config.api, 'key_env') then
  [{
    name: scraping_config.api.key_env,
    secret: scraping_config.api.key_env
  }]
else
  [];

{
  name: site_name + ' 爬虫',
  'run-name': '🕷️ ' + site_name + ' 爬虫 #${{ github.run_number }} (${{ github.actor }})',
  
  on: {
    workflow_dispatch: {
      inputs: {
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
        }
      }
    },
    schedule: [
      {cron: schedule}
    ]
  },
  
  // 并发控制 - 避免相同站点的任务并行运行
  concurrency: {
    group: 'crawler-' + site_id + '-${{ github.ref }}',
    'cancel-in-progress': true
  },
  
  jobs: {
    // 预检查作业
    'pre-check': {
      name: '环境与配置检查',
      'runs-on': params.global.runner,
      outputs: {
        run_date: '${{ steps.prepare_env.outputs.date }}',
        cache_key: '${{ steps.prepare_env.outputs.cache_key }}',
        site_config_valid: '${{ steps.validate_config.outputs.valid }}',
        use_proxy: '${{ steps.prepare_env.outputs.use_proxy }}'
      },
      steps: [
        {
          name: '检出代码',
          uses: 'actions/checkout@v4'
        },
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
      'runs-on': params.global.runner,
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
              pip install requests pyyaml
            fi
          |||
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
          name: '检查代理池状态',
          id: 'check_proxy_pool',
          run: |||
            # 检查代理状态文件是否存在
            if [ -f "status/proxies/pool_status.json" ]; then
              echo "发现代理池状态文件"
              
              # 获取代理统计
              if [ -x "$(command -v jq)" ]; then
                valid_count=$(cat status/proxies/pool_status.json | jq '.stats.valid_count')
              else
                valid_count=$(grep -o '"valid_count":[0-9]*' status/proxies/pool_status.json | grep -o '[0-9]*')
              fi
              
              echo "当前有效代理数: $valid_count"
              
              # 检查代理数量是否足够
              if [ "$valid_count" -lt "5" ]; then
                echo "⚠️ 代理数量不足 ($valid_count < 5)，需要更新代理池"
                echo "sufficient=false" >> $GITHUB_OUTPUT
              else
                echo "✅ 代理数量充足 ($valid_count >= 5)"
                echo "sufficient=true" >> $GITHUB_OUTPUT
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
            if ! python scripts/proxy_manager.py --action update --source all; then
              echo "更新失败，尝试恢复..."
              if ! python scripts/proxy_manager.py --action recover; then
                echo "恢复失败，尝试重建..."
                python scripts/proxy_manager.py --action rebuild --source all
              fi
            fi
            
            # 检查更新后的状态
            if [ -f "status/proxies/pool_status.json" ]; then
              if [ -x "$(command -v jq)" ]; then
                valid_count=$(cat status/proxies/pool_status.json | jq '.stats.valid_count')
              else
                valid_count=$(grep -o '"valid_count":[0-9]*' status/proxies/pool_status.json | grep -o '[0-9]*')
              fi
              
              echo "更新后的有效代理数: $valid_count"
            else
              echo "⚠️ 更新后仍未找到代理池状态文件"
            fi
          |||
        },
        {
          name: '提交代理池状态',
          'if': "steps.check_proxy_pool.outputs.sufficient == 'false'",
          run: |||
            # 配置Git
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            
            # 添加状态文件
            git add status/proxies/pool_status.json
            git add data/proxies/
            
            # 提交更改
            if git diff --staged --quiet; then
              echo "没有代理池状态变更，无需提交"
            else
              git commit -m "🔄 爬虫任务前的代理池更新 (站点: %(site_id)s)"
              git push
              echo "✅ 成功提交代理池状态更新"
            fi
          ||| % {site_id: site_id}
        }
      ]
    },
    
    // 爬虫作业
    crawl: {
      name: '运行爬虫',
      needs: ['pre-check', 'check-proxy'],
      'if': "always() && needs.pre-check.outputs.site_config_valid == 'true' && (needs.check-proxy.result == 'success' || needs.pre-check.outputs.use_proxy != 'true')",
      'runs-on': params.global.runner,
      env: {
        RUN_DATE: '${{ needs.pre-check.outputs.run_date }}',
        USE_PROXY: '${{ needs.pre-check.outputs.use_proxy }}'
      },
      steps: [
        {
          name: '检出代码',
          uses: 'actions/checkout@v4'
        },
        {
          name: '设置Python',
          uses: 'actions/setup-python@v5',
          with: {
            'python-version': params.global.python_version,
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
              pip install %(dependencies)s
            fi
          ||| % {dependencies: dependencies}
        },
        {
          name: '创建输出目录',
          run: |||
            mkdir -p data/%(site_id)s
            mkdir -p status/%(site_id)s
            mkdir -p logs
          ||| % {site_id: site_id}
        },
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
              --output "data/%(site_id)s/%(output_filename)s" \
              --status "status/%(site_id)s/status.json" \
              --log-file "logs/%(site_id)s_$RUN_DATE.log" \
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
            'retention-days': 7
          }
        },
        {
          name: '上传状态文件',
          uses: 'actions/upload-artifact@v4',
          with: {
            name: site_id + '-status-${{ needs.pre-check.outputs.run_date }}',
            path: 'status/' + site_id + '/status.json',
            'retention-days': 7
          }
        },
        {
          name: '上传日志文件',
          uses: 'actions/upload-artifact@v4',
          with: {
            name: site_id + '-logs-${{ needs.pre-check.outputs.run_date }}',
            path: 'logs/' + site_id + '_${{ needs.pre-check.outputs.run_date }}.log',
            'retention-days': 3
          }
        },
        {
          name: '提交结果和状态',
          run: |||
            # 配置Git
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            
            # 添加文件
            git add data/%(site_id)s/
            git add status/%(site_id)s/
            
            # 提交更改
            if git diff --staged --quiet; then
              echo "没有变更需要提交"
            else
              git commit -m "🤖 自动更新: %(site_name)s爬虫结果 ($RUN_DATE)"
              git push
              echo "✅ 成功提交爬虫结果"
            fi
          ||| % {site_id: site_id, site_name: site_name}
        }
      ]
    }
  }
}
