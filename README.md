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

## 与 supergateway 联调排错

如果你在把本服务通过 `supergateway` 暴露为 SSE 时看到如下报错：

- `Error: Already connected to a transport ...`

这通常表示：**同一个 MCP `Server` 实例被重复绑定到了新的 SSE 连接**（例如浏览器/客户端自动重连，或多标签页并发连接）。

可按下面方式规避：

1. 保证同一时刻只有一个 SSE 客户端连接到该网关。
2. 断开旧连接后再建立新连接（重启 supergateway 进程最直接）。
3. 检查客户端是否开启了激进的自动重连；必要时先关闭重连再验证。
4. 若你在自行实现网关代码：为每个新连接创建独立的 Protocol/Server 实例，或在重连前显式 `close()` 旧 transport。

> 说明：本仓库的 `calculator_mcp.py` 是 **stdio MCP 服务**，该错误来自 `supergateway` 的连接管理层，而不是计算器求值逻辑本身。
