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
| `Reflector.py` | **Reflector** | 总控类。负责调度 Micro 和 Macro 反思任务，管理对话缓冲区，并与 `EventBus` 交互。 |
| `MicroReflector.py` | **MicroReflector** | 执行微观反思逻辑。调用 LLM 分析对话片段，生成微观记忆并存入 Milvus。 |
| `MacroReflector.py` | **MacroReflector** | 执行宏观反思逻辑。检索一段时间内的微观记忆，调用 LLM 生成宏观总结。 |
| `MemorySchema.py` | **MicroMemory**, **MacroMemory** | 定义了记忆的数据结构，包括 LLM 输出格式、存储格式等。 |

## 工作流程

1.  **数据收集**: `Reflector` 监听 `EventBus` 或由 `Dispatcher` 推送，收集用户的 `ChatMessage` 到内部缓冲区。
2.  **触发微观反思**: 当缓冲区达到阈值或满足时间条件时，`Reflector` 调用 `MicroReflector`。
3.  **微观处理**: `MicroReflector` 将对话片段发送给 LLM，提取出关键信息（Subject, Action, Object 等），生成向量嵌入，存入 Memory Layer (L2)。
4.  **触发宏观反思**: `Reflector` 定期（如每24小时）调用 `MacroReflector`。
5.  **宏观处理**: `MacroReflector` 从 Memory Layer 拉取过去一天的微观记忆，让 LLM 进行总结和反思，生成高层级的记忆（如“今天我认识了...，感觉...”），并再次存入 Memory Layer。

## 配置

Reflector 的行为可以通过 `Config` 模块进行配置，主要参数包括：
- `micro_threshold`: 触发微观反思的消息数量阈值。
- `macro_interval_seconds`: 触发宏观反思的时间间隔。
- `milvus_collection`: 向量数据库集合名称。
