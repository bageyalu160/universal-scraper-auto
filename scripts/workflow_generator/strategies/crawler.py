#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 爬虫工作流策略
"""

from typing import Dict, Any, List

from .base import WorkflowStrategy
from ..models import (
    Workflow, Job, 
    CheckoutStep, SetupPythonStep, InstallDependenciesStep, 
    RunCommandStep, Step
)


class CrawlerWorkflowStrategy(WorkflowStrategy):
    """爬虫工作流策略"""
    
    def create_workflow(self, site_config: Dict[str, Any], global_config: Dict[str, Any]) -> Workflow:
        """创建爬虫工作流"""
        site_id = site_config['site_id']
        site_name = site_config.get('site_info', {}).get('name', site_id)
        
        # 基本设置
        python_version = global_config.get('python_version', '3.10')
        data_dir = global_config.get('data_dir', 'data')
        status_dir = global_config.get('status_dir', 'status')
        
        # 爬虫设置
        cron_schedule = site_config.get('scraping', {}).get('schedule', '0 0 * * *')
        scraper_script = site_config.get('scraping', {}).get('script_path', 'scripts/scraper.py')
        output_filename = site_config.get('output', {}).get('filename', f"{site_id}_data.json")
        scraper_dependencies = global_config.get('scraper_dependencies', 'requests beautifulsoup4 pandas pyyaml')
        
        # 创建工作流
        workflow = Workflow(
            name=f"{site_name} 爬虫任务",
            on={
                "workflow_dispatch": {},
                "schedule": [{"cron": cron_schedule}]
            },
            env={
                "PYTHON_VERSION": python_version,
                "RUN_DATE": "${{ github.event.inputs.date || '' }}"
            },
            permissions={
                "contents": "write",
                "actions": "write"
            },
            jobs={
                "scrape-website": self._create_scraper_job(
                    site_id=site_id,
                    site_name=site_name,
                    python_version=python_version,
                    data_dir=data_dir,
                    status_dir=status_dir,
                    scraper_script=scraper_script,
                    output_filename=output_filename,
                    scraper_dependencies=scraper_dependencies,
                    run_analysis=site_config.get('output', {}).get('run_analysis', True)
                )
            }
        )
        
        return workflow
    
    def _create_scraper_job(self, 
                           site_id: str,
                           site_name: str,
                           python_version: str,
                           data_dir: str,
                           status_dir: str,
                           scraper_script: str,
                           output_filename: str,
                           scraper_dependencies: str,
                           run_analysis: bool) -> Job:
        """创建爬虫作业"""
        steps = []
        
        # 步骤1: 检出代码
        steps.append(CheckoutStep(fetch_depth=0))
        
        # 步骤2: 设置日期环境变量
        steps.append(RunCommandStep(
            name="设置日期环境变量",
            commands=["echo \"RUN_DATE=$(date -u +\"%Y-%m-%d\")\" >> $GITHUB_ENV"]
        ))
        
        # 步骤3: 设置Python环境
        steps.append(SetupPythonStep(python_version="${{ env.PYTHON_VERSION }}"))
        
        # 步骤4: 安装依赖
        steps.append(InstallDependenciesStep(dependencies=scraper_dependencies))
        
        # 步骤5: 创建数据目录
        steps.append(RunCommandStep(
            name="创建数据目录",
            commands=[
                f"mkdir -p {data_dir}/daily",
                f"echo \"创建日期目录: {data_dir}/daily/${{{{ env.RUN_DATE }}}}\"",
                f"mkdir -p {data_dir}/daily/${{{{ env.RUN_DATE }}}}"
            ]
        ))
        
        # 步骤6: 运行爬虫脚本
        scraper_env = {
            "OPENAI_API_KEY": "${{ secrets.OPENAI_API_KEY }}",
            "GEMINI_API_KEY": "${{ secrets.GEMINI_API_KEY }}",
            "HEIMAO_COOKIE": "${{ secrets.HEIMAO_COOKIE }}",
            "HEIMAO_KEYWORDS": "${{ vars.HEIMAO_KEYWORDS || '' }}",
            "ENABLE_NOTIFICATION": "${{ vars.ENABLE_NOTIFICATION || 'false' }}",
            "NOTIFICATION_TYPE": "${{ vars.NOTIFICATION_TYPE || 'none' }}",
            "NOTIFICATION_WEBHOOK": "${{ vars.NOTIFICATION_WEBHOOK || '' }}"
        }
        
        scraper_commands = [
            "echo \"开始运行爬虫...\"",
            f"python {scraper_script} --site {site_id} --config config/sites/{site_id}.yaml",
            "",
            "# 检查生成的文件",
            f"if [ -f \"{output_filename}\" ]; then",
            "  echo \"爬虫成功完成，发现结果文件\"",
            "  echo \"file_exists=true\" >> $GITHUB_OUTPUT",
            f"  echo \"file_size=$(stat -c%s {output_filename})\" >> $GITHUB_OUTPUT",
            "  ",
            f"  # 复制到日期目录",
            f"  cp {output_filename} {data_dir}/daily/${{{{ env.RUN_DATE }}}}/",
            "  echo \"数据文件已复制到日期目录\"",
            "else",
            "  echo \"警告：未找到结果文件\"",
            "  echo \"file_exists=false\" >> $GITHUB_OUTPUT",
            "  echo \"file_size=0\" >> $GITHUB_OUTPUT",
            "fi"
        ]
        
        steps.append(RunCommandStep(
            name="运行爬虫脚本",
            commands=scraper_commands,
            env=scraper_env
        ).with_id("run-scraper").with_continue_on_error(True))
        
        # 步骤7: 创建状态文件
        status_commands = [
            f"mkdir -p {status_dir}",
            "# 创建状态文件",
            "if [ \"${{ steps.run-scraper.outcome }}\" == \"success\" ] && [ \"${{ steps.run-scraper.outputs.file_exists }}\" == \"true\" ]; then",
            "  echo '{",
            "    \"status\": \"success\",",
            "    \"date\": \"${{ env.RUN_DATE }}\",",
            "    \"timestamp\": \"'$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")'\",",
            f"    \"file_path\": \"{data_dir}/daily/${{{{ env.RUN_DATE }}}}/{output_filename}\",",
            "    \"file_size\": \"${{ steps.run-scraper.outputs.file_size }}\",",
            "    \"message\": \"爬虫运行成功，已生成数据文件\"",
            f"  }}' > {status_dir}/crawler_status.json",
            "else",
            "  echo '{",
            "    \"status\": \"failed\",",
            "    \"date\": \"${{ env.RUN_DATE }}\",",
            "    \"timestamp\": \"'$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")'\",",
            "    \"message\": \"爬虫运行失败或未生成文件\"",
            f"  }}' > {status_dir}/crawler_status.json",
            "fi",
            "echo \"已创建爬虫状态文件\""
        ]
        
        steps.append(RunCommandStep(
            name="创建爬虫状态文件",
            commands=status_commands
        ))
        
        # 步骤8: 提交结果和状态到仓库
        git_commands = [
            "echo \"正在提交爬虫结果和状态...\"",
            "# 设置git配置",
            "git config user.name \"github-actions[bot]\"",
            "git config user.email \"41898282+github-actions[bot]@users.noreply.github.com\"",
            "",
            "# 添加需要提交的文件",
            f"git add {data_dir}/daily/${{{{ env.RUN_DATE }}}}/ || echo \"没有数据目录变更\"",
            f"git add {output_filename} || echo \"没有主数据文件\"",
            f"git add {status_dir}/crawler_status.json",
            "",
            "# 检查是否有变更需要提交",
            "if git diff --staged --quiet; then",
            "  echo \"没有变更需要提交\"",
            "else",
            "  # 创建提交",
            f"  git commit -m \"自动更新：{site_name}爬虫数据 ${{{{ env.RUN_DATE }}}}\"",
            "  # 推送到仓库",
            "  git push",
            "  echo \"成功提交并推送爬虫结果和状态\"",
            "fi"
        ]
        
        steps.append(RunCommandStep(
            name="提交爬虫结果和状态",
            commands=git_commands
        ))
        
        # 步骤9: 触发分析工作流（如果需要）
        if run_analysis:
            steps.append(Step(
                name="触发分析工作流",
                if_condition="${{ steps.run-scraper.outputs.file_exists == 'true' }}",
                uses="benc-uk/workflow-dispatch@v1",
                with_params={
                    "workflow": f"analyzer_{site_id}.yml",
                    "token": "${{ secrets.GITHUB_TOKEN }}",
                    "inputs": (
                        '{"data_date": "${{ env.RUN_DATE }}", '
                        f'"data_file": "{data_dir}/daily/${{{{ env.RUN_DATE }}}}/{output_filename}", '
                        f'"site_id": "{site_id}"'
                        '}'
                    )
                }
            ))
        
        return Job(
            name="运行网站爬虫",
            runs_on="ubuntu-latest",
            steps=steps
        ) 