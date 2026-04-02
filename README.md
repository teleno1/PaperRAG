# PaperRAG

`PaperRAG` 是一个论文综述生成流水线项目。它会在统一的 `app/` 包下完成论文语料准备、FAISS 索引构建、大纲生成，以及最终综述写作。

## 配置说明

非敏感配置放在 `configs/settings.yaml` 中。

- `settings.yaml` 用于配置路径、模型名称、检索数量、写作温度、嵌入维度和 MinerU 轮询参数。
- API Key 不要写进 YAML，请通过环境变量设置 `DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY`、`MINERU_API_KEY`。
- 如果环境变量和 `settings.yaml` 同时配置了同一项，环境变量优先。

## 快速开始

安装依赖：

```bash
pip install -e .
```

设置必需环境变量。

PowerShell：

```powershell
$env:DEEPSEEK_API_KEY="..."
$env:DASHSCOPE_API_KEY="..."

# 仅在解析 PDF 时需要
$env:MINERU_API_KEY="..."
```

Bash：

```bash
export DEEPSEEK_API_KEY="..."
export DASHSCOPE_API_KEY="..."

# 仅在解析 PDF 时需要
export MINERU_API_KEY="..."
```

不要把 API Key 写进 `configs/settings.yaml`。

把 PDF 论文放到 `data/papers/` 目录下。

## CLI 用法

常用命令：

```bash
python -m app.cli.main corpus prepare
python -m app.cli.main index build
python -m app.cli.main outline generate --topic "..."
python -m app.cli.main review run --topic "..."
python -m app.cli.main review run-from-outline --outline data/outlines/.../outline.json
python -m app.cli.main state
python -m app.cli.main health
```

综述输出目录：

```text
data/review_outputs/<run_id>/
```

单次运行通常包含以下阶段目录：

```text
00_outline/
02_retrieval/
03_chapter_bundles/
04_chapter_drafts/
05_final_pass/
06_validation/
07_export/
```

## API 用法

启动 API：

```bash
uvicorn app.api.main:app --reload
```

主要路由：

- `POST /corpus/prepare`
- `POST /index/build`
- `POST /outline/generate`
- `POST /review/run`
- `POST /review/run-from-outline`
- `GET /state`
- `GET /health`

## 项目结构

```text
app/
  api/
  cli/
  core/
  use_cases/
  domain/
  infrastructure/
  schemas/
```
