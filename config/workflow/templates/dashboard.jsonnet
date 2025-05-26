// 仪表盘更新工作流模板 - Jsonnet版本

local params = import 'params.libsonnet';

// 外部参数
local global_config = std.parseJson(std.extVar('global_config'));

// 确定依赖项
local dependencies = params.dashboard.dependencies;

{
  name: '仪表盘更新',
  'run-name': '📊 仪表盘更新 #${{ github.run_number }} (${{ github.actor }})',
  
  on: {
    workflow_dispatch: {
      inputs: {
        date: {
          description: '数据日期 (留空则使用当前日期)',
          required: false,
          type: 'string'
        }
      }
    },
    workflow_call: {}
  },
  
  // 配置权限
  permissions: {
    contents: 'write',
    pages: 'write',
    'id-token': 'write'
  },
  
  jobs: {
    build: {
      name: '构建仪表盘',
      'runs-on': params.global.runner,
      steps: [
        {
          name: '检出代码',
          uses: 'actions/checkout@v4'
        },
        {
          name: '设置Python',
          uses: 'actions/setup-python@v4',
          with: {
            'python-version': params.global.python_version,
            cache: 'pip'
          }
        },
        {
          name: '安装依赖',
          run: 'pip install ' + dependencies
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
          name: '生成仪表盘',
          run: |||
            python scripts/dashboard_generator.py \
              --date "${{ steps.set-date.outputs.date }}" \
              --data-dir "data" \
              --analysis-dir "analysis" \
              --output-dir "dashboard"
          |||
        },
        {
          name: '设置Pages',
          uses: 'actions/configure-pages@v3'
        },
        {
          name: '上传Pages构建产物',
          uses: 'actions/upload-pages-artifact@v2',
          with: {
            path: 'dashboard'
          }
        }
      ]
    },
    
    deploy: {
      name: '部署仪表盘',
      needs: 'build',
      'runs-on': params.global.runner,
      
      // 部署到GitHub Pages环境
      environment: {
        name: 'github-pages',
        url: '${{ steps.deployment.outputs.page_url }}'
      },
      
      steps: [
        {
          name: '部署到GitHub Pages',
          id: 'deployment',
          uses: 'actions/deploy-pages@v2'
        }
      ]
    }
  }
}
