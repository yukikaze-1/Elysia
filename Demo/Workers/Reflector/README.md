# Reflector Worker (反思者)

`Reflector` 是 Elysia 系统的后台工作进程，负责模拟人类的“反思”机制。它在后台异步运行，不阻塞主对话流程，负责将短期的对话历史转化为长期的记忆，并对记忆进行整合与精炼。

## 核心概念

Reflector 实现了两级反思机制：

1.  **Micro Reflection (微观反思)**:
    *   **频率**: 较高（例如：每隔一段时间或对话缓冲区满时触发）。
    *   **输入**: 近期的原始对话记录 (`ChatMessage`)。
    *   **输出**: `MicroMemory` (微观记忆)。
    *   **作用**: 从流水账式的对话中提取关键信息、事实和情感片段，存入向量数据库。

2.  **Macro Reflection (宏观反思)**:
    *   **频率**: 较低（例如：每天一次）。
    *   **输入**: 一段时间内的 `MicroMemory`。
    *   **输出**: `MacroMemory` (宏观记忆/日记)。
    *   **作用**: 对碎片化的微观记忆进行回顾、总结和升华，形成更高级别的认知和长期记忆（类似于写日记）。

## 模块结构

| 文件 | 类名 | 描述 |
| --- | --- | --- |
| `Reflector.py` | **Reflector** | **Worker 包装器**。负责后台线程管理、任务调度、对话缓冲 (`buffer`) 以及与 `EventBus` 的交互。它不直接处理反思逻辑，而是委托给 `MemoryReflector`。 |
| `Reflector.py` | **MemoryReflector** | **业务逻辑外观模式 (Facade)**。负责初始化和协调 `MicroReflector` 与 `MacroReflector`，统一管理 LLM 客户端和 MemoryLayer 的连接。 |
| `MicroReflector.py` | **MicroReflector** | **微观反思执行者**。调用 LLM 分析对话片段，生成微观记忆并存入 Milvus。 |
| `MacroReflector.py` | **MacroReflector** | **宏观反思执行者**。检索一段时间内的微观记忆，调用 LLM 生成宏观总结。 |
| `MemorySchema.py` | **MicroMemory**, **MacroMemory** | 定义了记忆的数据结构，包括 LLM 输出格式、存储格式等。 |

## 详细工作流程

### 1. 数据收集 (Data Collection)
*   **来源**: 当 `Dispatcher` 处理完一轮对话后，会调用 `Reflector.on_new_message(msg)`。
*   **缓冲**: 消息被放入 `Reflector` 内部的线程安全列表 `buffer` 中暂存。此时不会立即触发 LLM 调用，以避免频繁消耗资源。

### 2. 微观反思 (Micro Reflection)
*   **触发**: 后台线程定期检查 `buffer`。当积压的消息数量达到阈值 (`micro_threshold`，如 10 条) 时，触发微观反思。
*   **执行**:
    1.  **锁定与提取**: 锁定 `buffer`，取出所有待处理消息，清空 `buffer`。
    2.  **LLM 分析**: 调用 `MicroReflector`，将对话历史发送给 LLM。Prompt 要求 LLM 提取对话中的关键事实（Who, Did What, When）、情感变化和重要信息。
    3.  **结构化**: 解析 LLM 返回的 JSON，生成多个 `MicroMemory` 对象。
    4.  **向量化与存储**: 为每个 `MicroMemory` 生成 Embedding 向量，并将其存入 L2 Memory Layer (Milvus)。
    5.  **通知**: 通过 `EventBus` 发布 `REFLECTION_DONE` 事件，通知系统反思完成。

### 3. 宏观反思 (Macro Reflection)
*   **触发**: 后台线程检查上次宏观反思的时间。如果距离现在超过了设定间隔 (`macro_interval_seconds`，通常为 24 小时)，则触发宏观反思。
*   **执行**:
    1.  **异步启动**: 为了不阻塞微观反思的检查，宏观反思通常在新的子线程中运行。
    2.  **记忆检索**: `MacroReflector` 从 L2 Memory Layer 中检索过去一个周期（如过去 24 小时）内生成的所有 `MicroMemory`。
    3.  **深度思考**: 将这些碎片化的微观记忆汇总，发送给 LLM。Prompt 要求 LLM 像写日记一样，对这一天的经历进行总结、反思，提炼出更深层次的感悟、人际关系变化或自我认知。
    4.  **生成宏观记忆**: LLM 生成 `MacroMemory` (包含日记内容、情感基调、关键词等)。
    5.  **存储**: 将 `MacroMemory` 存入 L2 Memory Layer。这成为了 AI 的“长期情节记忆”。
    6.  **通知**: 发布 `REFLECTION_DONE` 事件。

## 状态管理 (Checkpoint)

Reflector 支持状态的持久化与恢复，以便在系统重启后不丢失进度：
- **dump_state()**: 导出当前状态（包括缓冲区中的未处理消息、上次宏观反思时间等）。
- **load_state()**: 从字典恢复状态。
- **force_save()**: 强制处理缓冲区中的剩余消息（通常在系统关闭时调用）。

## 配置

Reflector 的行为可以通过 `Config` 模块进行配置，主要参数包括：
- `micro_threshold`: 触发微观反思的消息数量阈值。
- `macro_interval_seconds`: 触发宏观反思的时间间隔。
- `worker_sleep_interval`: 后台线程的轮询间隔。
