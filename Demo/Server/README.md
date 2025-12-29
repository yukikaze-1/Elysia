# Server (Web 服务层)

`Server` 模块提供了基于 FastAPI 的 Web 接口和 WebSocket 实时通信能力，使 Elysia 能够作为后端服务运行，支持 Web 前端（如 `client.html`）的接入。

## 模块概览

| 文件 | 类名 | 描述 |
| --- | --- | --- |
| `App.py` | **ElysiaServer** | 服务器主程序。负责初始化系统核心组件（Layers, Dispatcher 等），配置 FastAPI 应用和路由，以及启动 uvicorn 服务。 |
| `ConnectionManager.py` | **ConnectionManager** | WebSocket 连接管理器。同时实现了 `OutputChannel` 接口，作为同步业务层与异步 Web 层之间的桥梁。 |

## 核心机制

### 1. 架构集成
`ElysiaServer` 类在初始化时会构建完整的认知架构（L0-L3, Dispatcher, EventBus），这与单机版 (`main.py`) 的初始化逻辑类似。不同之处在于，Server 版将输入输出通道替换为了网络接口：
- **输入**: 来自 WebSocket 的消息被封装为 `USER_INPUT` 事件。
- **输出**: `ActuatorLayer` 注册了 `ConnectionManager` 作为输出通道，将回复推送到 WebSocket。

### 2. 同步/异步桥接 (Sync-Async Bridge)
Elysia 的核心逻辑（如 `Dispatcher` 和各个 Layer）通常运行在同步线程中，而 FastAPI 是基于 `asyncio` 的异步框架。
- **ConnectionManager** 解决了这个问题：它在 `ActuatorLayer` 调用 `send_message`（同步方法）时，使用 `asyncio.run_coroutine_threadsafe` 将发送任务投递回 FastAPI 的主事件循环中执行。
- 这确保了后台线程生成的回复能够安全、及时地通过 WebSocket 发送给客户端，而不会阻塞服务器主循环。

### 3. WebSocket 通信流程
1.  **连接**: 客户端连接 `/ws/{client_id}` 端点。
2.  **接收**: 服务器收到消息，封装为 `Event`，通过 `EventBus.publish()` 发布。
3.  **处理**: `Dispatcher` 调度各层处理该事件（在后台线程中进行）。
4.  **响应**: 处理完成后，`ActuatorLayer` 调用 `ConnectionManager.send_message()`。
5.  **发送**: `ConnectionManager` 将消息异步推送回客户端。

## 使用方法

通常通过根目录下的 `server.py` 启动：

```bash
python server.py
```

启动后，默认在 `http://0.0.0.0:8000` 监听。
