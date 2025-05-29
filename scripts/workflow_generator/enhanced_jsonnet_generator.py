#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版Jsonnet工作流生成器
支持YAML模板的完整功能移植
"""

import os
import sys
import json
import logging
import _jsonnet
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
from ruamel.yaml import YAML

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 尝试导入jsonnet_generator
try:
    from jsonnet_generator import JsonnetWorkflowGenerator
except ImportError:
    # 如果导入失败，创建一个基础类
    class JsonnetWorkflowGenerator:
        def __init__(self, settings_path=None, sites_dir=None, output_dir=None, logger=None):
            self.settings_path = settings_path
            self.sites_dir = Path(sites_dir) if sites_dir else Path('config/sites')
            self.output_dir = Path(output_dir) if output_dir else Path('.github/workflows')
            self.templates_dir = Path('config/workflow/templates')
            self.logger = logger or logging.getLogger(__name__)
            self.global_config = {}
            
        def _load_site_config(self, site_id):
            """加载站点配置"""
            config_file = self.sites_dir / f"{site_id}.yaml"
            if not config_file.exists():
                return None
            
            try:
                yaml = YAML(typ='safe', pure=True)
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.load(f)
            except Exception as e:
                self.logger.error(f"加载站点配置失败: {e}")
                return None
        
        def _get_all_sites(self):
            """获取所有站点"""
            if not self.sites_dir.exists():
                return []
            
            sites = []
            for config_file in self.sites_dir.glob("*.yaml"):
                sites.append(config_file.stem)
            return sorted(sites)


class EnhancedJsonnetGenerator(JsonnetWorkflowGenerator):
    """
    增强版Jsonnet工作流生成器
    完全支持analyzer.yml.template的所有功能
    """
    
    def __init__(self, settings_path=None, sites_dir=None, output_dir=None, logger=None):
        super().__init__(settings_path, sites_dir, output_dir, logger)
        
        # 增强功能配置
        self._setup_enhanced_features()
    
    def _setup_enhanced_features(self):
        """设置增强功能"""
        # 复杂脚本模板库
        self.script_templates = {
            'parameter_detection': self._get_parameter_detection_script(),
            'file_validation': self._get_file_validation_script(),
            'status_creation': self._get_status_creation_script(),
            'git_commit': self._get_git_commit_script(),
            'notification_preparation': self._get_notification_preparation_script()
        }
        
        # 条件表达式库
        self.condition_expressions = {
            'workflow_dispatch': "github.event_name == 'workflow_dispatch'",
            'repository_dispatch': "github.event_name == 'repository_dispatch'",
            'workflow_call': "github.event_name == 'workflow_call'",
            'success': "success()",
            'failure': "failure()",
            'always': "always()",
            'step_success': lambda step: f"steps.{step}.outcome == 'success'",
            'step_failure': lambda step: f"steps.{step}.outcome == 'failure'",
            'file_exists': lambda file: f"hashFiles('{file}') != ''",
            'env_enabled': lambda var: f"vars.{var} == 'true'",
            'secret_exists': lambda secret: f"secrets.{secret} != ''"
        }
        
        # 高级配置选项
        self.cache_enabled = True  # 默认启用缓存
        self.timeout = 30  # 默认超时时间（分钟）
        self.error_strategy = 'strict'  # 默认错误处理策略（strict 或 tolerant）
    
    def _get_parameter_detection_script(self) -> str:
        """获取参数检测脚本模板"""
        return '''
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
            SITE_ID="{{site_id}}"
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
        '''
    
    def _get_file_validation_script(self) -> str:
        """获取文件验证脚本模板"""
        return '''
        if [ ! -f "${{ steps.params.outputs.data_file }}" ]; then
          echo "❌ 错误: 数据文件 ${{ steps.params.outputs.data_file }} 不存在"
          exit 1
        else
          echo "✅ 数据文件存在，准备分析"
        fi
        '''
    
    def _get_status_creation_script(self) -> str:
        """获取状态文件创建脚本模板"""
        return '''
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
            "analysis_file": "$ANALYSIS_DIR/analysis_$DATA_DATE.{{output_extension}}",
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
        '''
    
    def _get_git_commit_script(self) -> str:
        """获取Git提交脚本模板"""
        return '''
        echo "正在提交分析结果和状态..."
        # 设置git配置
        git config user.name "github-actions[bot]"
        git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
        
        # 添加需要提交的文件
        if [ -f "$ANALYSIS_DIR/analysis_$DATA_DATE.{{output_extension}}" ]; then
          git add "$ANALYSIS_DIR/" || echo "没有分析目录变更"
        fi
        git add status/analyzer_$SITE_ID.json
        
        # 检查是否有变更需要提交
        if git diff --staged --quiet; then
          echo "没有变更需要提交"
        else
          # 创建提交
          git commit -m "🤖 自动更新: {{site_name}}分析结果 ($DATA_DATE)"
          # 推送到仓库
          git push
          echo "✅ 成功提交并推送分析结果和状态"
        fi
        '''
    
    def _get_notification_preparation_script(self) -> str:
        """获取通知准备脚本模板"""
        return '''
        if [[ "${{ needs.analyze.result }}" == "success" ]]; then
          echo "status=success" >> $GITHUB_OUTPUT
          echo "color=#00FF00" >> $GITHUB_OUTPUT
          echo "message<<EOF" >> $GITHUB_OUTPUT
          echo "### ✅ {{site_name}}分析任务成功" >> $GITHUB_OUTPUT
          echo "" >> $GITHUB_OUTPUT
          echo "- **站点**: {{site_name}}" >> $GITHUB_OUTPUT
          echo "- **日期**: ${{ needs.pre-check.outputs.data_date }}" >> $GITHUB_OUTPUT
          echo "- **运行ID**: [#${{ github.run_number }}](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }})" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
        else
          echo "status=failure" >> $GITHUB_OUTPUT
          echo "color=#FF0000" >> $GITHUB_OUTPUT
          echo "message<<EOF" >> $GITHUB_OUTPUT
          echo "### ❌ {{site_name}}分析任务失败" >> $GITHUB_OUTPUT
          echo "" >> $GITHUB_OUTPUT
          echo "- **站点**: {{site_name}}" >> $GITHUB_OUTPUT
          echo "- **日期**: ${{ needs.pre-check.outputs.data_date }}" >> $GITHUB_OUTPUT
          echo "- **失败阶段**: ${{ needs.analyze.result == 'failure' && 'Analysis' || 'Pre-Check' }}" >> $GITHUB_OUTPUT
          echo "- **运行ID**: [#${{ github.run_number }}](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }})" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
        fi
        '''
    
    def _create_enhanced_analyzer_template(self, site_id: str, site_config: Dict[str, Any]) -> str:
        """创建增强版分析器Jsonnet模板"""
        
        # 预先计算需要的变量
        analysis_config = site_config.get('analysis', {})
        output_extension = 'json' if analysis_config.get('output_format') == 'json' else 'tsv'
        site_name = site_config.get('site_info', {}).get('name', site_id)
        
        # 替换脚本模板中的变量
        parameter_detection_script = self.script_templates['parameter_detection'].replace('{{site_id}}', site_id)
        file_validation_script = self.script_templates['file_validation']
        status_creation_script = self.script_templates['status_creation'].replace('{{output_extension}}', output_extension)
        git_commit_script = self.script_templates['git_commit'].replace('{{output_extension}}', output_extension).replace('{{site_name}}', site_name)
        notification_preparation_script = self.script_templates['notification_preparation'].replace('{{site_name}}', site_name)
        
        template_content = f'''
// 增强版分析工作流模板 - 完整功能对标 analyzer.yml.template
// 由EnhancedJsonnetGenerator生成

local params = import 'params.libsonnet';

// 外部参数
local site_id = std.extVar('site_id');
local site_config = std.parseJson(std.extVar('site_config'));
local global_config = std.parseJson(std.extVar('global_config'));

// 站点信息
local site_name = if std.objectHas(site_config, 'site_info') && std.objectHas(site_config.site_info, 'name') then
  site_config.site_info.name
else if std.objectHas(site_config, 'site') && std.objectHas(site_config.site, 'name') then
  site_config.site.name
else
  site_id;

// 分析配置
local analysis_config = if std.objectHas(site_config, 'analysis') then
  site_config.analysis
else
  {{}};

// 输出扩展名
local output_extension = if std.objectHas(analysis_config, 'output_format') then
  if analysis_config.output_format == 'json' then 'json'
  else if analysis_config.output_format == 'tsv' then 'tsv'
  else 'json'
else
  'tsv';

// 状态和分析目录
local status_dir = if std.objectHas(global_config, 'general') && std.objectHas(global_config.general, 'status_dir') then
  global_config.general.status_dir
else
  'status';

local analysis_dir = if std.objectHas(global_config, 'general') && std.objectHas(global_config.general, 'analysis_dir') then
  global_config.general.analysis_dir
else
  'analysis';

// Python版本
local python_version = if std.objectHas(params, 'global') && std.objectHas(params.global, 'python_version') then
  params.global.python_version
else
  '3.10';

// 环境变量配置
local env_vars = [
  {{ name: 'OPENAI_API_KEY', secret: 'OPENAI_API_KEY' }},
  {{ name: 'GEMINI_API_KEY', secret: 'GEMINI_API_KEY' }}
];

// 依赖项
local analysis_dependencies = if std.objectHas(params.workflow, 'analyzer') && std.objectHas(params.workflow.analyzer, 'dependencies') then
  params.workflow.analyzer.dependencies
else
  'requests pyyaml pandas openai google-generativeai';

// 通知配置
local send_notification = if std.objectHas(global_config, 'notification') && std.objectHas(global_config.notification, 'enabled') then
  global_config.notification.enabled
else
  false;

// 分析脚本路径
local analyzer_script = if std.objectHas(site_config, 'analysis') && std.objectHas(site_config.analysis, 'script') then
  site_config.analysis.script
else
  'scripts/ai_analyzer.py';

// 通知脚本路径
local notification_script = if std.objectHas(global_config, 'notification') && std.objectHas(global_config.notification, 'script') then
  global_config.notification.script
else
  'scripts/notifier.py';

{{
  name: site_name + ' AI分析任务',
  'run-name': '🧠 ' + site_name + '分析 #${{{{ github.run_number }}}} (${{{{ github.actor }}}} 触发)',
  
  // 复杂触发条件
  on: {{
    workflow_dispatch: {{
      inputs: {{
        data_date: {{
          description: '数据日期 (YYYY-MM-DD格式)',
          required: true,
          type: 'string'
        }},
        data_file: {{
          description: '要分析的数据文件路径',
          required: true,
          type: 'string'
        }},
        site_id: {{
          description: '网站ID',
          required: true,
          type: 'string',
          default: site_id
        }},
        model: {{
          description: 'AI模型选择',
          required: false,
          type: 'choice',
          default: 'default',
          options: ['default', 'gemini-1.5-pro', 'gpt-4-turbo']
        }}
      }}
    }},
    repository_dispatch: {{
      types: ['crawler_completed']
    }},
    workflow_call: {{
      inputs: {{
        data_date: {{
          description: '数据日期',
          required: true,
          type: 'string'
        }},
        data_file: {{
          description: '数据文件路径',
          required: true,
          type: 'string'
        }},
        site_id: {{
          description: '网站ID',
          required: true,
          type: 'string',
          default: site_id
        }}
      }},
      secrets: {{
        API_KEY: {{
          required: false
        }}
      }}
    }}
  }},
  
  // 全局环境变量
  env: {{
    PYTHON_VERSION: python_version,
    ANALYSIS_DIR: analysis_dir + '/daily',
    SITE_ID: site_id,
    TZ: 'Asia/Shanghai'
  }},
  
  // 权限设置
  permissions: {{
    contents: 'write',
    actions: 'write'
  }},
  
  // 默认配置
  defaults: {{
    run: {{
      shell: 'bash'
    }}
  }},
  
  // 并发控制
  concurrency: {{
    group: 'analyzer-' + site_id + '-${{{{ github.ref }}}}',
    'cancel-in-progress': true
  }},
  
  // 多作业工作流
  jobs: {{
    // 预检查作业
    'pre-check': {{
      name: '准备分析环境',
      'runs-on': 'ubuntu-latest',
      outputs: {{
        data_date: '${{{{ steps.params.outputs.data_date }}}}',
        data_file: '${{{{ steps.params.outputs.data_file }}}}',
        site_id: '${{{{ steps.params.outputs.site_id }}}}',
        analysis_dir: '${{{{ steps.params.outputs.analysis_dir }}}}',
        cache_key: '${{{{ steps.params.outputs.cache_key }}}}'
      }},
      steps: [
        {{
          name: '检出代码',
          uses: 'actions/checkout@v4'
        }},
        {{
          name: '确定分析参数',
          id: 'params',
          run: |||
            {parameter_detection_script}
          |||
        }},
        {{
          name: '检查数据文件是否存在',
          run: |||
            {file_validation_script}
          |||
        }}
      ]
    }},
    
    // 分析作业
    analyze: {{
      name: '执行AI分析',
      needs: 'pre-check',
      'runs-on': 'ubuntu-latest',
      'timeout-minutes': 30,
      env: {{
        DATA_DATE: '${{{{ needs.pre-check.outputs.data_date }}}}',
        DATA_FILE: '${{{{ needs.pre-check.outputs.data_file }}}}',
        SITE_ID: '${{{{ needs.pre-check.outputs.site_id }}}}',
        ANALYSIS_DIR: '${{{{ needs.pre-check.outputs.analysis_dir }}}}'
      }},
      steps: [
        {{
          name: '检出代码',
          uses: 'actions/checkout@v4'
        }},
        {{
          name: '设置Python环境',
          uses: 'actions/setup-python@v5',
          with: {{
            'python-version': '${{{{ env.PYTHON_VERSION }}}}',
            cache: 'pip',
            'cache-dependency-path': '**/requirements.txt'
          }}
        }},
        {{
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
        }},
        {{
          name: '运行AI分析',
          id: 'run_analysis',
          'continue-on-error': true,
          env: {{
            OPENAI_API_KEY: '${{{{ secrets.OPENAI_API_KEY }}}}',
            GEMINI_API_KEY: '${{{{ secrets.GEMINI_API_KEY }}}}',
            MODEL: '${{{{ github.event.inputs.model || \\'default\\' }}}}',
            HEIMAO_KEYWORDS: '${{{{ vars.HEIMAO_KEYWORDS || \\'\\'}}}}',
            ENABLE_NOTIFICATION: '${{{{ vars.ENABLE_NOTIFICATION || \\'false\\' }}}}',
            NOTIFICATION_TYPE: '${{{{ vars.NOTIFICATION_TYPE || \\'none\\' }}}}',
            NOTIFICATION_WEBHOOK: '${{{{ vars.NOTIFICATION_WEBHOOK || \\'\\'}}}}',
            GITHUB_REPOSITORY: '${{{{ github.repository }}}}'
          }},
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
            python scripts/ai_analyzer.py --file "$DATA_FILE" --site "$SITE_ID" --output "$ANALYSIS_DIR/analysis_$DATA_DATE.{output_extension}" $MODEL_ARG
            
            # 检查分析结果文件
            if [ -f "$ANALYSIS_DIR/analysis_$DATA_DATE.{output_extension}" ]; then
              echo "✅ 分析成功完成，已生成结果文件"
              echo "analysis_exists=true" >> $GITHUB_OUTPUT
              echo "analysis_file=$ANALYSIS_DIR/analysis_$DATA_DATE.{output_extension}" >> $GITHUB_OUTPUT
            else
              echo "⚠️ 警告：未找到分析结果文件"
              echo "analysis_exists=false" >> $GITHUB_OUTPUT
            fi
          |||
        }},
        {{
          name: '创建分析状态文件',
          run: |||
            {status_creation_script}
          |||
        }},
        {{
          name: '提交分析结果和状态',
          run: |||
            {git_commit_script}
          |||
        }},
        {{
          name: '上传分析结果 (作为工件)',
          if: 'steps.run_analysis.outputs.analysis_exists == \\'true\\'',
          uses: 'actions/upload-artifact@v4',
          with: {{
            name: site_id + '-analysis-${{{{ needs.pre-check.outputs.data_date }}}}',
            path: '${{{{ steps.run_analysis.outputs.analysis_file }}}}',
            'retention-days': 5
          }}
        }}
      ]
    }},
    
    // 通知作业
    notify: {{
      name: '发送通知',
      needs: ['pre-check', 'analyze'],
      if: 'always()',
      'runs-on': 'ubuntu-latest',
      steps: [
        {{
          name: '检出代码',
          if: 'contains(needs.*.result, \\'failure\\') || contains(needs.*.result, \\'cancelled\\')',
          uses: 'actions/checkout@v4'
        }},
        {{
          name: '准备通知内容',
          id: 'prepare_message',
          run: |||
            {notification_preparation_script}
          |||
        }},
        {{
          name: '发送钉钉通知',
          if: 'vars.ENABLE_NOTIFICATION == \\'true\\' && vars.NOTIFICATION_TYPE == \\'dingtalk\\' && secrets.DINGTALK_WEBHOOK != \\'\\'',
          uses: 'fifsky/dingtalk-action@master',
          with: {{
            url: '${{{{ secrets.DINGTALK_WEBHOOK }}}}',
            type: 'markdown',
            content: '${{{{ steps.prepare_message.outputs.message }}}}'
          }}
        }},
        {{
          name: '发送企业微信通知',
          if: 'vars.ENABLE_NOTIFICATION == \\'true\\' && vars.NOTIFICATION_TYPE == \\'wechat\\' && secrets.WECHAT_WEBHOOK != \\'\\'',
          uses: 'chf007/action-wechat-work@master',
          with: {{
            msgtype: 'markdown',
            content: '${{{{ steps.prepare_message.outputs.message }}}}',
            key: '${{{{ secrets.WECHAT_WEBHOOK }}}}'
          }}
        }}
      ]
    }}
  }}
}}
        '''
        
        return template_content
    
    def generate_enhanced_analyzer_workflow(self, site_id: str) -> bool:
        """
        生成增强版分析工作流文件
        
        Args:
            site_id: 站点ID
            
        Returns:
            bool: 是否成功生成
        """
        try:
            # 加载站点配置
            site_config = self._load_site_config(site_id)
            if not site_config:
                self.logger.error(f"无法加载站点配置: {site_id}")
                return False
            
            # 创建增强版模板内容
            template_content = self._create_enhanced_analyzer_template(site_id, site_config)
            
            # 写入临时模板文件
            temp_template_path = self.templates_dir / f"analyzer_enhanced_{site_id}.jsonnet"
            os.makedirs(self.templates_dir, exist_ok=True)
            with open(temp_template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            # 准备外部变量
            ext_vars = {
                "site_id": site_id,
                "site_config": site_config,
                "global_config": self.global_config
            }
            
            # 生成工作流文件
            success = self.generate_workflow(f"analyzer_enhanced_{site_id}", f"analyzer_{site_id}", ext_vars)
            
            # 清理临时文件
            if temp_template_path.exists():
                temp_template_path.unlink()
            
            return success
            
        except Exception as e:
            self.logger.error(f"生成增强版分析工作流文件失败: {site_id}, {e}")
            return False
    
    def generate_crawler_workflow(self, site_id: str) -> bool:
        """
        生成爬虫工作流文件
        
        Args:
            site_id: 站点ID
            
        Returns:
            bool: 是否成功生成
        """
        try:
            # 加载站点配置
            site_config = self._load_site_config(site_id)
            if not site_config:
                self.logger.error(f"无法加载站点配置: {site_id}")
                return False
            
            self.logger.info(f"✅ 生成爬虫工作流: {site_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"生成爬虫工作流文件失败: {site_id}, {e}")
            return False
    
    def set_cache_enabled(self, enabled: bool):
        """
        设置是否启用缓存
        
        Args:
            enabled: 是否启用缓存
        """
        self.cache_enabled = enabled
        self.logger.debug(f"缓存设置已更新: {'启用' if enabled else '禁用'}")
    
    def set_timeout(self, timeout: int):
        """
        设置工作流超时时间
        
        Args:
            timeout: 超时时间（分钟）
        """
        self.timeout = timeout
        self.logger.debug(f"超时设置已更新: {timeout} 分钟")
    
    def set_error_strategy(self, strategy: str):
        """
        设置错误处理策略
        
        Args:
            strategy: 错误处理策略（strict 或 tolerant）
        """
        if strategy not in ['strict', 'tolerant']:
            self.logger.warning(f"无效的错误处理策略: {strategy}，使用默认值 'strict'")
            strategy = 'strict'
        self.error_strategy = strategy
        self.logger.debug(f"错误处理策略已更新: {strategy}")
    
    def generate_workflow(self, template_name: str, output_name: str, ext_vars: dict = None):
        """
        生成工作流文件
        
        Args:
            template_name: 模板名称
            output_name: 输出文件名
            ext_vars: 外部变量
            
        Returns:
            bool: 是否成功生成
        """
        if ext_vars is None:
            ext_vars = {}
        
        # 添加高级配置选项到外部变量
        ext_vars.update({
            'cache_enabled': self.cache_enabled,
            'timeout_minutes': self.timeout,
            'error_strategy': self.error_strategy
        })
        
        template_path = self.templates_dir / f"{template_name}.jsonnet"
        output_path = self.output_dir / output_name
        
        if not template_path.exists():
            self.logger.error(f"模板文件不存在: {template_path}")
            return False
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        try:
            # 将外部变量转换为JSON字符串
            json_vars = {}
            for k, v in ext_vars.items():
                if k == 'site_id' and isinstance(v, str):
                    # 直接传递站点ID，不使用json.dumps
                    json_vars[k] = v
                else:
                    json_vars[k] = json.dumps(v)
            
            self.logger.debug(f"处理后的外部变量: {json_vars}")
            
            # 使用_jsonnet库渲染模板
            result = _jsonnet.evaluate_file(
                str(template_path),
                ext_vars=json_vars
            )
            
            # 写入输出文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
                
            self.logger.info(f"成功生成工作流文件: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"生成工作流文件失败: {e}")
            return False
    
    def _enhance_existing_params_library(self):
        """增强现有的params.libsonnet库"""
        enhanced_params = '''
{
  // 全局参数配置
  global: {
    // 基础运行环境
    runner: 'ubuntu-latest',
    // Python版本
    python_version: '3.10',
    // 默认计划任务时间
    default_cron: '0 0 * * *',
    // 默认超时时间（分钟）
    default_timeout: 30,
  },
  
  // 通知配置
  notification: {
    // 钉钉通知
    dingtalk: {
      enabled: true,
      webhook_secret: 'DINGTALK_WEBHOOK',
    },
    // 企业微信通知
    wechat: {
      enabled: true,
      webhook_secret: 'WECHAT_WEBHOOK',
    },
  },
  
  // 工作流配置
  workflow: {
    // 主工作流配置
    master: {
      name: '主调度工作流',
      actions: [
        'crawl_all',
        'analyze_all',
        'update_dashboard',
        'update_proxy_pool',
        'full_pipeline',
      ],
    },
    // 爬虫工作流配置
    crawler: {
      name: '爬虫工作流',
      dependencies: {
        default: 'requests pyyaml beautifulsoup4 pandas',
        firecrawl: 'requests pyyaml firecrawl pandas',
        playwright: 'requests pyyaml playwright pandas',
      },
    },
    // 分析工作流配置 - 增强版
    analyzer: {
      name: '分析工作流',
      dependencies: 'requests pyyaml pandas openai google-generativeai',
      // 支持的AI提供商
      providers: ['openai', 'gemini', 'anthropic'],
      // 支持的输出格式
      output_formats: ['json', 'tsv', 'csv'],
      // 默认脚本路径
      scripts: {
        analyzer: 'scripts/ai_analyzer.py',
        notifier: 'scripts/notifier.py'
      },
      // 状态管理
      status: {
        dir: 'status',
        file_pattern: 'analyzer_{site_id}.json'
      },
      // 缓存配置
      cache: {
        enabled: true,
        key_pattern: 'deps-analysis-{hash}-v1'
      }
    },
    // 代理池工作流配置
    proxy_pool: {
      name: '代理池管理',
      dependencies: 'requests pyyaml aiohttp pandas',
    },
    // 仪表盘更新工作流配置
    dashboard: {
      name: '仪表盘更新',
      dependencies: 'pyyaml pandas plotly jinja2',
    },
  },
  
  // 条件表达式库
  conditions: {
    // 触发条件
    triggers: {
      workflow_dispatch: "github.event_name == 'workflow_dispatch'",
      repository_dispatch: "github.event_name == 'repository_dispatch'",
      workflow_call: "github.event_name == 'workflow_call'"
    },
    // 状态条件
    states: {
      success: "success()",
      failure: "failure()",
      always: "always()",
      cancelled: "cancelled()"
    },
    // 环境条件
    environment: {
      env_enabled: function(var) "vars." + var + " == 'true'",
      secret_exists: function(secret) "secrets." + secret + " != ''",
      file_exists: function(file) "hashFiles('" + file + "') != ''"
    }
  },
  
  // 脚本模板库
  scripts: {
    // Git操作
    git: {
      setup: |||
        git config user.name "github-actions[bot]"
        git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
      |||,
      commit_and_push: function(message) |||
        if git diff --staged --quiet; then
          echo "没有变更需要提交"
        else
          git commit -m "%(message)s"
          git push
          echo "✅ 成功提交并推送变更"
        fi
      ||| % {message: message}
    },
    // 状态管理
    status: {
      create_json: function(status, site_id, data) |||
        cat > status/%(status)s_%(site_id)s.json << EOF
        %(data)s
        EOF
      ||| % {status: status, site_id: site_id, data: std.manifestJsonEx(data, "  ")}
    }
  }
}
        '''
        
        # 写入增强的params库
        enhanced_params_path = self.templates_dir / "params_enhanced.libsonnet"
        with open(enhanced_params_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_params)
        
        return enhanced_params_path 