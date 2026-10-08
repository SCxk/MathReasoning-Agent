# 首次上传 GitHub

目标仓库：[SCxk/MathReasoning-Agent](https://github.com/SCxk/MathReasoning-Agent)。
本文件夹是独立的源码发布副本，不含旧 Git 历史，尚未初始化、提交或推送。

## 发布内容

包含前后端、共享推理引擎、技能手册、词法策略资源、功能测试与部署配置。
不含密钥、聊天记录、题目数据、模型权重、嵌入数组、运行日志、旧交接记录、
依赖目录和前端构建产物。安装与启动步骤见 README.md。

原项目和本地记录仍保留在原目录，本副本不会自动同步之后的原项目修改。
仅在本文件夹中执行以下命令：

```powershell
git init -b main
git remote add origin https://github.com/SCxk/MathReasoning-Agent.git
git add -- .gitignore .dockerignore .github AGENTS.md CLAUDE.md README.md PUBLISHING.md THIRD_PARTY_NOTICES.md Dockerfile compose.yaml compose.rag.yaml deployment_bootstrap.py llm_client.py pyproject.toml requirements*.txt agent_platform client deploy docs reasoning_agent scripts skill2 skill2_en strategy_data strategyrag tests
git status --short
git diff --cached --stat
git diff --cached --name-only
```

确认列表中没有新加入的本地数据或凭据后，由你执行：

```powershell
git commit -m "feat: initialize math reasoning web app"
git push -u origin main
```

首次推送可能要求浏览器登录 GitHub。仓库当前为私有，上传不会自动改变可见性。
Python 导入路径、API 路径和存储键保持兼容，无需随仓库名称更改。
