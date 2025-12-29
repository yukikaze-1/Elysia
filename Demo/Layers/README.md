# Layers (认知架构层)

`Layers` 目录构成了 Elysia 的核心认知架构。系统采用了分层设计，模拟人类的感知、认知、记忆和人格机制。每一层都有明确的职责，共同协作以产生连贯、逼真且具有个性的行为。

## 架构概览

Elysia 的认知架构主要分为以下几个层次：

| 层级 | 名称 | 描述 | 关键组件 |
| --- | --- | --- | --- |
| **L0** | **Sensor Layer (感知层)** | 系统的“感官”和“直觉”。负责接收外部输入，感知环境变化，并产生本能的情绪反应。 | `Sensor`, `Amygdala` |
| **L1** | **Brain Layer (大脑层)** | 系统的“理性大脑”。负责逻辑思考、决策制定、语言生成以及主动行为的规划。 | `L1.py` |
| **L2** | **Memory Layer (记忆层)** | 系统的“海马体”。负责管理短期工作记忆（Session）和长期情景记忆（Vector DB）。 | `L2.py`, `SessionState` |
| **L3** | **Persona Layer (人格层)** | 系统的“灵魂”。定义角色的静态设定、性格特征、价值观和社会属性。 | `L3.py`, `CoreIdentity` |
| **Psyche**| **Psyche System (心理系统)** | 系统的“生理/心理状态机”。模拟精力、社交能量、无聊度等动态指标。 | `PsycheSystem.py` |

## 详细说明

### 1. L0: Sensor Layer (感知层)
位于 `Layers/L0/`。
- **SensoryProcessor**: 处理来自不同来源（用户消息、系统事件、环境变化）的原始数据，将其转化为标准化的 `EnvironmentInformation`。
- **Amygdala (杏仁核)**: 模拟人类的杏仁核功能，对输入进行快速、直觉的情感评估，产生“本能反应” (Instinct)，直接影响后续的认知处理。
- **运行机制**: L0 通常在独立线程中运行，持续监听环境，一旦检测到重要变化即向系统发送信号。

### 2. L1: Brain Layer (大脑层)
位于 `Layers/L1.py`。
- **决策与生成**: 综合 L0 的感知信息、L2 的记忆上下文和 L3 的人格设定，生成最终的回复或行动。
- **两种模式**:
    - **NormalResponse**: 被动回复用户的消息。
    - **ActiveResponse**: 基于内部驱动力（如无聊、好奇）主动发起对话。
- **Prompt Engineering**: 包含核心的 Prompt 模板，指导 LLM 如何扮演角色。

### 3. L2: Memory Layer (记忆层)
位于 `Layers/L2/`。
- **统一接口**: `MemoryLayer` 类作为单例运行，统一管理所有记忆操作。
- **短期记忆**: `SessionState` 维护当前的对话上下文，确保对话的连贯性。
- **长期记忆**: 集成向量数据库 (Milvus)，存储历史对话的 Embedding，支持语义检索，让 AI 能够“回忆”起很久以前的事情。

### 4. L3: Persona Layer (人格层)
位于 `Layers/L3.py` 和 `Layers/CoreIdentity.py`。
- **CoreIdentity**: 定义了 Elysia 的核心设定，包括姓名、年龄、职业、MBTI、外貌描写等静态数据。
- **Profile Classes**: 定义了 `BasicProfile`, `SociologicalProfile` 等数据结构，用于结构化地描述角色。
- **作用**: 为 L1 提供一致的人格基准，确保 AI 的言行符合其设定。

### 5. Psyche System (心理系统)
位于 `Layers/PsycheSystem.py`。
- **动态状态**: 模拟生物节律和心理状态。
    - **Energy (精力)**: 随时间消耗，睡眠恢复。影响 AI 的活跃度。
    - **Social Battery (社交电量)**: 说话消耗，独处恢复。影响 AI 的回复意愿。
    - **Boredom (无聊度)**: 随时间增加。驱动 AI 主动发起话题。
- **System Clock**: 依赖系统的 Tick 事件进行状态更新。

## 数据流向

1.  **感知**: L0 接收输入 -> 生成 `EnvironmentInformation` 和 `AmygdalaOutput`。
2.  **检索**: L2 根据输入检索相关的长期记忆。
3.  **状态**: PsycheSystem 提供当前的心理状态（如“我累了”或“我很无聊”）。
4.  **认知**: L1 接收上述所有信息 + L3 的人格设定 -> 调用 LLM 生成响应。
5.  **记忆**: 新的交互被写入 L2 的短期和长期记忆中。
