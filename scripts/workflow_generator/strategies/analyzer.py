#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 分析工作流策略
"""

from typing import Dict, Any, List

from .base import WorkflowStrategy
from ..models import (
    Workflow, Job, 
    CheckoutStep, SetupPythonStep, InstallDependenciesStep, 
    RunCommandStep, Step, NotificationStep
)


class AnalyzerWorkflowStrategy(WorkflowStrategy):
    """分析工作流策略"""
    
    def create_workflow(self, site_config: Dict[str, Any], global_config: Dict[str, Any]) -> Workflow:
        """创建分析工作流"""
        site_id = site_config['site_id']
        site_name = site_config.get('site_info', {}).get('name', site_id)
        
        # 基本设置
        python_version = global_config.get('python_version', '3.10')
        analysis_dir = global_config.get('analysis_dir', 'analysis')
        status_dir = global_config.get('status_dir', 'status')
        
        # 分析设置
        analyzer_script = global_config.get('ai_analysis', {}).get('script_path', 'scripts/ai_analyzer.py')
        output_file = global_config.get('ai_analysis', {}).get('output_file', 'analysis_result.tsv')
        output_extension = global_config.get('ai_analysis', {}).get('output_format', 'tsv')
        analysis_dependencies = global_config.get('analysis_dependencies', 'requests pandas pyyaml google-generativeai openai')
        
        # 通知设置
        notification_script = global_config.get('notification', {}).get('script_path', 'scripts/notify.py')
        send_notification = global_config.get('notification', {}).get('enabled', False)
        
        # 创建工作流
        workflow = Workflow(
            name=f"{site_name} AI分析任务",
            on={
                "workflow_dispatch": {
                    "inputs": {
                        "data_date": {
                            "description": "数据日期 (YYYY-MM-DD格式)",
                            "required": True,
                            "type": "string"
                        },
                        "data_file": {
                            "description": "要分析的数据文件路径",
                            "required": True,
                            "type": "string"
                        },
                        "site_id": {
                            "description": "网站ID",
                            "required": True,
                            "type": "string",
                            "default": site_id
                        }
                    }
                },
                "repository_dispatch": {
                    "types": ["crawler_completed"]
                }
            },
            env={
                "PYTHON_VERSION": python_version,
                "ANALYSIS_DIR": f"{analysis_dir}/daily"
            },
            permissions={
                "contents": "write",
                "actions": "write"
            },
            jobs={
                "analyze-data": self._create_analyzer_job(
                    site_id=site_id,
                    site_name=site_name,
                    python_version=python_version,
                    analysis_dir=analysis_dir,
                    status_dir=status_dir,
                    analyzer_script=analyzer_script,
                    output_file=output_file,
                    output_extension=output_extension,
                    analysis_dependencies=analysis_dependencies,
                    notification_script=notification_script,
                    send_notification=send_notification
                )
            }
        )
        
        return workflow
    
    def _create_analyzer_job(self, 
                            site_id: str, 
                            site_name: str,
                            python_version: str,
                            analysis_dir: str,
                            status_dir: str,
                            analyzer_script: str,
                            output_file: str,
                            output_extension: str,
                            analysis_dependencies: str,
                            notification_script: str,
                            send_notification: bool) -> Job:
        """创建分析作业"""
        steps = []
        
        # 步骤1: 检出代码
        steps.append(CheckoutStep(fetch_depth=0))
        
        # 步骤2: 设置Python环境
        steps.append(SetupPythonStep(python_version="${{ env.PYTHON_VERSION }}"))
        
        # 步骤3: 安装依赖
        steps.append(InstallDependenciesStep(dependencies=analysis_dependencies))
        
        # 步骤4: 确定分析参数
        params_commands = [
            "# 从参数中获取数据日期和文件路径",
            "if [ \"${{ github.event_name }}\" == \"workflow_dispatch\" ]; then",
            "  DATA_DATE=\"${{ github.event.inputs.data_date }}\"",
            "  DATA_FILE=\"${{ github.event.inputs.data_file }}\"",
            "  SITE_ID=\"${{ github.event.inputs.site_id }}\"",
            "elif [ \"${{ github.event_name }}\" == \"repository_dispatch\" ]; then",
            "  DATA_DATE=\"${{ github.event.client_payload.data_date }}\"",
            "  DATA_FILE=\"${{ github.event.client_payload.data_file }}\"",
            "  SITE_ID=\"${{ github.event.client_payload.site_id }}\"",
            "else",
            "  # 如果没有参数，尝试从状态文件获取最新数据",
            f"  if [ -f \"{status_dir}/crawler_status.json\" ]; then",
            f"    DATA_DATE=$(jq -r '.date' {status_dir}/crawler_status.json)",
            f"    DATA_FILE=$(jq -r '.file_path' {status_dir}/crawler_status.json)",
            f"    SITE_ID=\"{site_id}\"",
            "  else",
            "    echo \"错误: 无法确定数据日期和文件路径\"",
            "    exit 1",
            "  fi",
            "fi",
            "",
            "# 确保日期目录存在",
            "mkdir -p \"${ANALYSIS_DIR}/${DATA_DATE}\"",
            "",
            "# 检查数据文件是否存在",
            "if [ ! -f \"${DATA_FILE}\" ]; then",
            "  echo \"错误: 数据文件 ${DATA_FILE} 不存在\"",
            "  exit 1",
            "fi",
            "",
            "# 设置输出参数",
            "echo \"data_date=${DATA_DATE}\" >> $GITHUB_OUTPUT",
            "echo \"data_file=${DATA_FILE}\" >> $GITHUB_OUTPUT",
            "echo \"site_id=${SITE_ID}\" >> $GITHUB_OUTPUT",
            "echo \"analysis_dir=${ANALYSIS_DIR}/${DATA_DATE}\" >> $GITHUB_OUTPUT",
            "echo \"设置分析参数: 日期=${DATA_DATE}, 文件=${DATA_FILE}, 站点=${SITE_ID}\""
        ]
        
        steps.append(RunCommandStep(
            name="确定分析参数",
            commands=params_commands
        ).with_id("params"))
        
        # 步骤5: 运行AI分析
        analyzer_env = {
            "OPENAI_API_KEY": "${{ secrets.OPENAI_API_KEY }}",
            "GEMINI_API_KEY": "${{ secrets.GEMINI_API_KEY }}",
            "GITHUB_REPOSITORY": "${{ github.repository }}"
        }
        
        analyzer_commands = [
            "echo \"开始分析数据文件: ${{ steps.params.outputs.data_file }}\"",
            "",
            "# 运行AI分析脚本",
            f"python {analyzer_script} --file \"${{{{ steps.params.outputs.data_file }}}}\" --site \"${{{{ steps.params.outputs.site_id }}}}\" --output \"{output_file}\"",
            "",
            "# 检查分析结果文件",
            f"if [ -f \"{output_file}\" ]; then",
            "  echo \"分析成功完成，发现结果文件\"",
            "  echo \"analysis_exists=true\" >> $GITHUB_OUTPUT",
            "  ",
            "  # 复制到日期目录",
            f"  cp {output_file} \"${{{{ steps.params.outputs.analysis_dir }}}}/analysis_${{{{ steps.params.outputs.data_date }}}}.{output_extension}\"",
            "  echo \"分析结果已保存到日期目录\"",
            "else",
            "  echo \"警告：未找到分析结果文件\"",
            "  echo \"analysis_exists=false\" >> $GITHUB_OUTPUT",
            "fi"
        ]
        
        steps.append(RunCommandStep(
            name="运行AI分析",
            commands=analyzer_commands,
            env=analyzer_env
        ).with_id("run-analysis").with_continue_on_error(True))
        
        # 步骤6: 创建分析状态文件
        status_commands = [
            f"mkdir -p {status_dir}",
            "# 创建状态文件",
            "if [ \"${{ steps.run-analysis.outcome }}\" == \"success\" ] && [ \"${{ steps.run-analysis.outputs.analysis_exists }}\" == \"true\" ]; then",
            "  echo '{",
            "    \"status\": \"success\",",
            "    \"site_id\": \"${{ steps.params.outputs.site_id }}\",",
            "    \"date\": \"${{ steps.params.outputs.data_date }}\",",
            "    \"timestamp\": \"'$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")'\",",
            "    \"data_file\": \"${{ steps.params.outputs.data_file }}\",",
            f"    \"analysis_file\": \"${{{{ steps.params.outputs.analysis_dir }}}}/analysis_${{{{ steps.params.outputs.data_date }}}}.{output_extension}\",",
            "    \"message\": \"数据分析成功完成\"",
            f"  }}' > {status_dir}/analyzer_status.json",
            "else",
            "  echo '{",
            "    \"status\": \"failed\",",
            "    \"site_id\": \"${{ steps.params.outputs.site_id }}\",",
            "    \"date\": \"${{ steps.params.outputs.data_date }}\",",
            "    \"timestamp\": \"'$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")'\",",
            "    \"data_file\": \"${{ steps.params.outputs.data_file }}\",",
            "    \"message\": \"数据分析失败或无结果\"",
            f"  }}' > {status_dir}/analyzer_status.json",
            "fi",
            "echo \"已创建分析状态文件\""
        ]
        
        steps.append(RunCommandStep(
            name="创建分析状态文件",
            commands=status_commands
        ))
        
        # 步骤7: 提交分析结果和状态到仓库
        git_commands = [
            "echo \"正在提交分析结果和状态...\"",
            "# 设置git配置",
            "git config user.name \"github-actions[bot]\"",
            "git config user.email \"41898282+github-actions[bot]@users.noreply.github.com\"",
            "",
            "# 添加需要提交的文件",
            f"if [ -f \"{output_file}\" ]; then",
            f"  git add {output_file}",
            "fi",
            "git add \"${{ steps.params.outputs.analysis_dir }}/\" || echo \"没有分析目录变更\"",
            f"git add {status_dir}/analyzer_status.json",
            "",
            "# 检查是否有变更需要提交",
            "if git diff --staged --quiet; then",
            "  echo \"没有变更需要提交\"",
            "else",
            "  # 创建提交",
            f"  git commit -m \"自动更新：{site_name}分析结果 ${{{{ steps.params.outputs.data_date }}}}\"",
            "  # 推送到仓库",
            "  git push",
            "  echo \"成功提交并推送分析结果和状态\"",
            "fi"
        ]
        
        steps.append(RunCommandStep(
            name="提交分析结果和状态",
            commands=git_commands
        ))
        
        # 步骤8: 发送通知（如果启用）
        if send_notification:
            steps.append(NotificationStep(
                notification_script=notification_script,
                analysis_dir="${{ steps.params.outputs.analysis_dir }}",
                data_date="${{ steps.params.outputs.data_date }}",
                site_id="${{ steps.params.outputs.site_id }}",
                output_extension=output_extension
            ))
        
        return Job(
            name="分析爬虫数据",
            runs_on="ubuntu-latest",
            steps=steps
        ) 