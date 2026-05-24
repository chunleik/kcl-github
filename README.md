# kcl-github

一个可直接运行的 **MCP 计算器服务**（stdio + JSON-RPC 2.0），提供高效且安全的表达式计算能力。

## 功能

- `calculate` 工具支持：
  - 四则运算：`+ - * /`
  - 高级运算：`// % **`
  - 括号与一元正负号
  - 常量：`pi`、`e`
  - 上次结果：`ans`
  - 函数：`sqrt sin cos tan log log10 exp abs round ceil floor factorial`
- 基于 Python `ast` 的安全求值，不执行任意代码。

## 运行

```bash
python3 calculator_mcp.py
```

## Docker 镜像

### 本地构建与运行

```bash
docker build -t calculator-mcp:local .
docker run --rm -i calculator-mcp:local
```

### 作为 GitHub Release 的发布内容

仓库新增了 `release-docker` 工作流：当你在 GitHub 发布一个 Release（`published`）时，会自动构建并推送镜像到 GHCR：

- `ghcr.io/<owner>/<repo>:<tag>`
- `ghcr.io/<owner>/<repo>:latest`

拉取示例：

```bash
docker pull ghcr.io/<owner>/<repo>:<tag>
```

## MCP 交互示例

### 1) 初始化

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
```

### 2) 获取工具列表

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
```

### 3) 调用计算

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"calculate","arguments":{"expression":"(2+3)*4+sqrt(16)"}}}
```

返回文本结果（例如 `24.0`）。
