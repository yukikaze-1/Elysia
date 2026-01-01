# Handlers 事件处理器模块

`Handlers` 模块包含了 Elysia 系统中具体的事件处理逻辑。每个 Handler 负责处理特定类型的事件（`EventType`），实现了具体的业务流程。

## 模块结构

所有 Handler 均继承自 `BaseHandler`，并通过 `HandlerRegistry` 注册到系统中，供 `Dispatcher` 调用。

### 1. BaseHandler (`BaseHandler.py`)
- **角色**: 抽象基类。
- **功能**: 
  - 定义了所有 Handler 必须实现的接口 `handle(event: Event)`。
  - 持有 `AgentContext` 引用，方便子类访问系统的核心组件（如 L0-L3 层级、Actuator 等）。

### 2. UserInputHandler (`UserInputHandler.py`)
- **处理事件**: `EventType.USER_INPUT`
- **功能**: 处理用户输入，驱动认知层进行响应。
- **核心流程**:
  1.  **感知**: 接收用户消息 (`UserMessage`)。
  2.  **心理反应**: 通知 `PsycheSystem` 用户已交互（重置无聊度等状态）。
  3.  **决策**: 调用大脑层 (`BrainLayer/L1`) 生成回复 (`NormalResponse`)。
  4.  **表达**: 通过 `ActuatorLayer` 输出语音/文字。
  5.  **记忆**: 将对话内容存入 `MemoryLayer` 和 `SessionState`。
  6.  **状态更新**: 更新 `PersonaLayer` 的情绪状态。

### 3. SystemTickHandler (`SystemTickHandler.py`)
- **处理事件**: `EventType.SYSTEM_TICK`
- **功能**: 处理系统心跳事件，维护系统状态和主动性。
- **核心流程**:
  1.  **状态持久化**: 调用 `CheckPointManager` 保存当前系统状态（Checkpoint）。
  2.  **主动交互检测**: 
      - 计算与用户的沉默时长。
      - 根据当前环境和心理状态，判断是否需要主动发起对话（Active Speak）。
      - *注：主动发起的逻辑包含检查冷却时间、用户是否在场等条件。*

## 扩展指南

若需添加新的事件处理逻辑：
1. 创建一个新的 Handler 类，继承自 `BaseHandler`。
2. 使用 `@HandlerRegistry.register(EventType.NEW_TYPE)` 装饰器进行注册。
3. 实现 `handle` 方法。
