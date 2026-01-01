# Core 核心架构模块

`Core` 目录包含了 Elysia 智能体系统的基础设施和核心运行时组件。这些组件共同构成了系统的骨架，负责事件流转、状态管理、任务调度以及与外部世界的交互。

## 架构概览

Elysia 的核心架构基于 **事件驱动 (Event-Driven)** 和 **组件化** 设计。

1.  **EventBus (事件总线)** 作为系统的神经中枢，负责所有模块间的通信。
2.  **Dispatcher (调度器)** 监听事件总线，根据事件类型将任务分发给具体的 **Handlers (处理器)**。
3.  **AgentContext (智能体上下文)** 作为一个全局容器，持有所有核心组件的引用，方便各层级访问。
4.  **SystemClock (系统时钟)** 提供心跳机制，驱动系统的周期性任务。

## 模块说明

### 基础组件

- **`AgentContext.py`**
  - 定义了 `AgentContext` 数据类。
  - 作用：作为依赖注入的容器，封装了系统所有核心层级（L0-L3, PsycheSystem 等）和管理器实例，确保各模块能方便地获取所需资源。

- **`EventBus.py`**
  - 实现了一个线程安全的事件总线。
  - 作用：解耦各个模块。支持异步事件队列（供 Dispatcher 消费）和同步订阅者模式（Observer Pattern）。

- **`Dispatcher.py`**
  - 系统的核心调度循环。
  - 作用：不断从 `EventBus` 获取事件，并根据 `EventType` 查找对应的策略（Handler）进行处理。
  - 采用了策略模式，将具体的事件处理逻辑委托给 `Handlers/` 下的处理器。

- **`Schema.py`**
  - 定义了系统通用的数据结构和枚举。
  - 包含：`Event` (事件对象), `EventType`, `EventSource`, `UserMessage` 等核心数据定义。

- **`SystemClock.py`**
  - 系统的心跳发生器。
  - 作用：在后台线程中运行，定期发布 `SYSTEM_TICK` 事件，用于驱动需要时间感知的模块（如情绪衰减、定时任务）。

### 状态与持久化

- **`SessionState.py`**
  - 会话状态管理器。
  - 作用：维护当前的对话历史（Context Window），管理短期记忆，确保发送给 LLM 的 Token 数量在控制范围内。

- **`CheckPointManager.py`**
  - 统一的存档管理器。
  - 作用：负责系统各模块状态的序列化与持久化（Save/Load）。
  - 机制：采用注册机制，各模块注册自己的 `getter` (获取状态) 和 `setter` (恢复状态) 函数，管理器统一进行原子化的文件读写。

### 执行与输出

- **`ActuatorLayer.py`**
  - 执行层 / 表达层。
  - 作用：将 AI 的决策转化为具体的外部行动。
  - 功能：支持多种动作类型（如 `SPEECH`, `COMMAND`），并将结果分发到注册的 `OutputChannel`。

- **`OutputChannel.py`**
  - 定义了输出通道的抽象基类及实现。
  - 包含：
    - `ConsoleChannel`: 输出到终端控制台（带颜色高亮）。
    - `WebSocketChannel`: 输出到 WebSocket 客户端（用于 Web 前端）。

### 事件处理器 (Handlers/)

位于 `Handlers/` 目录下，包含具体的事件处理逻辑：
- **`UserInputHandler`**: 处理用户输入事件，驱动认知层进行响应。
- **`SystemTickHandler`**: 处理系统心跳事件，驱动心理系统（PsycheSystem）的更新。

## 工作流程示例

1.  **用户输入**: 前端/终端产生输入 -> 封装为 `Event(USER_INPUT)` -> 推送至 `EventBus`。
2.  **调度**: `Dispatcher` 从 `EventBus` 取出事件 -> 识别为 `USER_INPUT` -> 交给 `UserInputHandler`。
3.  **处理**: `UserInputHandler` 调用 L0-L3 层级进行感知、记忆检索、决策和生成。
4.  **行动**: 生成的回复通过 `ActuatorLayer` -> `OutputChannel` -> 返回给用户。
