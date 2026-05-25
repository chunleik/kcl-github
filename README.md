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
# SSE 模式（HTTP，供 Claude Code 等客户端远程连接）
uv run python calculator_mcp.py sse

# stdio 模式（本地管道，兼容 supergateway 等桥接工具）
uv run python calculator_mcp.py stdio
```

SSE 模式下，服务直接监听 `http://0.0.0.0:8000/sse`，无需 supergateway 桥接。
可通过环境变量配置：`FASTMCP_HOST`、`FASTMCP_PORT`。

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

## 接入 Claude Code

```bash
claude mcp add -t sse calculator http://localhost:8000/sse
```

## 与 supergateway 联调（旧方案）

> 注意：当前版本已内置 SSE 支持，无需 supergateway 桥接。以下内容仅作为参考保留。

如果你仍希望通过 `supergateway` 暴露为 SSE：

```bash
npx -y supergateway --stdio "python3 calculator_mcp.py stdio" --port 8000
```

supergateway 存在已知 bug：**同一 Server 实例被重复绑定时** 会抛出 `Error: Already connected to a transport ...`。原因是 `stdioToSse.js` 中 `sseTransport.onclose` 在 `server.connect()` 之后才赋值，覆盖了 SDK 内部包装的 `_onclose` 清理回调，导致 `server._transport` 不会被清空。
