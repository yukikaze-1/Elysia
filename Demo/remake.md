# 项目重构说明与建议（Elysia Demo）

## 一、当前架构概述

Elysia Demo 是一个单体的拟人化虚拟角色系统，采用分层 + 事件驱动的设计，主要模块与职责如下：

- `server/`（FastAPI Server）
  - 提供 WebSocket / HTTP 接入，负责传输层逻辑（连接管理、消息收发）。
  - 在 `server/App.py` 中定义生命周期与路由。

- `main.py`（单机入口）
  - 单体阻塞式主循环版本，初始化所有核心组件并启动 `Dispatcher`。

- `core/`
  - `EventBus.py`：事件总线（单例），使用 `queue.Queue` 做消息缓冲，并支持同步订阅回调与队列投递。
  - `Dispatcher.py`：调度器，从 `EventBus` 取事件并分发到对应 Handler（策略模式 + `HandlerRegistry` 自动注册）。
  - `HandlerRegistry.py`：Handler 注册与发现机制，Handler 存放于 `core/handlers/`。
  - `ActuatorLayer.py`：执行层，负责把意图转成外部动作（发送文本、语音、表情等）。
  - `PromptManager.py`、`SessionState.py`、`CheckPointManager.py` 等负责提示、会话和检查点管理。
  - `ChatMessage.py` / `Schema.py`：消息与事件的数据结构（你已扩展以支持 STT/TTS 字段）。

- `layers/`（分层认知模块）
  - `L0`（Sensor）：感知层，包含 `Sensor.py`、`Amygdala.py`、`STT.py`（用于音频输入处理）。L0 负责监听输入线程并向 `EventBus` 发布 `USER_INPUT` 等事件。
  - `L1`（Brain）：大脑层，生成回复（调用 LLM 或模板）。
  - `L2`（Memory）：记忆层，管理短期/长期记忆并提供检索接口。
  - `L3`（Persona）：人格层，维护心情与人物设定。
  - `PsycheSystem.py`：模拟生理/心理驱动（Energy、Boredom、Social Battery）。

- `workers/reflector/`（后台工作线程）
  - 对话反思器（Reflector）异步整理对话、生成长期记忆摘要。

- 其它
  - `prompt/`：Jinja 模板与 Prompt 管理。
  - `client.html`：示例前端，具备 WebSocket 交互。

总体上，系统以事件（`Event`）为通信载体，通过 `EventBus` 解耦模块，`Dispatcher` 负责把事件路由到具体 Handler，再由 Handler 与 L0~L3、Actuator 等协作完成业务逻辑。


## 二、当前架构的优点

- 清晰的分层思想（感知、认知、记忆、人格、执行）。
- 基于事件的松耦合模块间通信，便于插入新 Handler 或事件类型。
- 使用 `HandlerRegistry` 自动发现 Handler，有利于扩展。
- 有独立的 Reflector 后台模块，考虑长期记忆整理。


## 三、主要问题与不足（需要重构的点）

1. EventBus 与并发模型不统一
   - 当前 `EventBus` 使用同步 `queue.Queue` 并在 `publish()` 中同步调用订阅回调，可能被耗时订阅阻塞，影响整体吞吐。
   - `Dispatcher` 是阻塞式循环（同步），服务器（FastAPI）使用异步模型，二者在并发模型上存在不一致，导致在 Server 模式下可能出现线程/协程混用问题。

2. 同步/异步混杂导致复杂度与潜在死锁
   - `main.py` 使用多线程（L0 子线程、Reflector 后台），而 `server/App.py` 使用 FastAPI 的异步生命周期。没有统一的异步任务调度与线程边界策略。

3. Actuator 与 Sensor 内部耦合过高
   - `ActuatorLayer.py` 与 `Sensor`、`Server` 存在直接交互，且 Actuator 逻辑集中，缺乏子模块化（TTS、文本、表情等应拆分）。

4. STT/TTS、耗时 I/O 缺少异步/队列处理
   - 音频转写与语音合成为耗时操作，应当以异步任务或独立 Worker 处理，并返回结果事件，而不是在主线程同步完成。

5. 缺乏接口与抽象层（可替换性差）
   - 例如 STT/TTS、LLM、VectorDB 的调用硬编码或分散在多个模块，替换第三方服务或做单元测试不便。

6. 事件 Schema 与版本控制不足
   - Event/ChatMessage 结构虽已扩展，但缺少明确的版本、兼容策略与序列化规范（例如 `audio` 字段是 bytes 还是 base64）。

7. 配置分散且缺少运行时热更能力
   - `config` 存放配置，但运行时切换 STT/TTS/LLM 配置缺乏统一管理接口。

8. 测试、CI 与文档不足
   - 缺少单元/集成测试、缺少清晰的模块接口文档与部署说明，增加重构与发布风险。


## 四、重构目标（高层次）

- 统一并发模型：在 Server 模式下优先使用 `asyncio`，将 EventBus 支持异步队列；在单机 CLI 模式提供兼容层。
- 明确边界与接口：为 STT、TTS、LLM、VectorDB、Actuator 等外部能力定义适配器接口（Adapter），便于替换和单测。
- 模块化 Actuator 与 Sensor：把 TTS、Text、Expression、Media 输出拆分为独立子模块并由 Actuator 管理编排。
- 引入任务队列或 Worker：耗时操作（STT/TTS/Reflector/LLM 调用）通过后台 Worker 或线程池/进程池异步执行，并通过事件回调结果。
- 改进 EventBus：支持异步 `publish()` / `subscribe()`，并避免在 publish 过程中执行耗时回调；支持优先级或主题过滤。
- 增加配置与运行时管理：统一 `config` 中加入服务适配配置，提供热重载或通过 Admin 接口动态切换。
- 建立测试与 CI：添加单元测试、集成测试与 lint、类型检查（mypy）等。


## 五、具体重构建议与步骤（分阶段）

### 阶段 A — 基础整理（最小侵入）
1. 明确 `Event`、`ChatMessage` 序列化格式与字段（定义版本字段 `schema_version`）。
2. 在 `core/` 下添加 `interfaces/`，声明：
   - `ISttEngine`, `ITtsEngine`, `IModelService`, `IMemoryStore`, `IActuator` 等抽象接口（Python 抽象基类）。
3. 将 `ActuatorLayer` 重构为包：
   - `core/actuator/__init__.py`（对外统一接口）
   - `core/actuator/text.py`, `speech.py`, `expression.py`
4. 在 `layers/L0/` 内把音频处理抽离为 `layers/L0/audio.py` 或 `STTAdapter`，实现 `ISttEngine`。
5. 增加 `utils/task_worker.py`（基于 `concurrent.futures.ThreadPoolExecutor` 或 `asyncio` 的任务封装），用于运行耗时阻塞任务。

优点：快速把代码组织好，便于下一步大改。


### 阶段 B — 并发模型与 EventBus 升级
1. 设计并实现 `AsyncEventBus`（基于 `asyncio.Queue`）：
   - 提供 `publish(event)`（非阻塞）和 `subscribe(event_type, coro)`（异步回调）。
   - 保持向后兼容：为现有同步 `Dispatcher` 提供适配器层（bridge）。
2. 将 `Dispatcher` 改为异步版本 `AsyncDispatcher`（或在内部用 `asyncio.to_thread` 调用现有 Handler），并逐步把 Handler 改为 `async def handle()`。
3. 在 Server 模式下，优先使用 `AsyncEventBus`；在单机 CLI 模式保留兼容性适配器。

优点：消除了线程/协程混用带来的许多难以追踪的 bug，并提高吞吐与响应性。


### 阶段 C — 抽象外部依赖并接入 Worker
1. 将 STT/TTS/LLM 调用改为通过适配器接口调用，并把具体实现注册到依赖注入容器（或简单工厂）。
2. 对耗时任务（STT/TTS/LLM/Reflector）走后台队列：任务提交 -> worker 处理 -> 完成后 publish 结果事件（如 `STT_DONE`、`TTS_DONE`）。
3. 优化 `Actuator`：当 Handler 需要输出音频时，只发布 `SPEAK_INTENT` 事件，Actuator 接收后触发 `TTS` Worker，再将带音频的 `ChatMessage` 发送回 `ConnectionManager`。

优点：系统在高负载下更稳健，且能做更细粒度的重试与限流。


### 阶段 D — 工程化、测试与文档
1. 增加 `requirements.txt`、`pyproject.toml`（如需），并固定关键依赖版本。
2. 添加单元测试目录 `tests/`，对 `EventBus`、`Dispatcher`、`Actuator` 抽象接口做测试。
3. 增加静态类型检查（mypy）、代码风格（black/flake8）与 GitHub Actions CI 流水线。
4. 完善 `README.md` 与 `docs/`，写清部署、运行、扩展与接入说明。


## 六、优先级与估算（建议实施顺序）

1. 阶段 A（基础整理）：1-3 天（取决于代码量）
2. 阶段 B（并发模型）：3-7 天
3. 阶段 C（外部依赖抽象 + Worker）：3-7 天
4. 阶段 D（测试与文档）：2-4 天

（以上为单人开发粗略估计，团队与并行工作能加速交付）


## 七、兼容与回退策略

- 每次大改动（尤其是 EventBus/Dispatcher）都应保持与旧实现的适配器，至少一段时间内两套机制并行运行，确保可以回滚。
- 对于关键 I/O（STT/TTS/LLM），先实现 Mock/本地实现用于测试，再切换到云服务。


## 八、结论（简短建议）

当前代码架构理念良好（分层 + 事件驱动），但实现上混合了同步/异步与线程模型，且对耗时 I/O 缺少异步化与任务隔离。建议分阶段重构：先整理边界与抽象，再统一并发模型，最后把耗时任务迁移到 Worker。按阶段推进并保持向后兼容与充足测试，可以在降低风险的同时大幅提升系统稳定性与可维护性。

---

如果你同意这个方向，我可以：

- 立即把 `core/` 下的接口骨架（`interfaces`）和 `core/actuator/` 包结构先搭好；
- 或者先把 `EventBus` 升级为 `AsyncEventBus` 的草案并写测试用例；

你希望我从哪个子任务开始？
