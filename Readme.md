markdown
// filepath: /home/yomu/Elysia/Readme.md
# Elysia AI 对话与语音交互系统

一个整合本地大模型 (Ollama) 与云端 OpenAI 兼容接口，支持角色人格设定、全局记忆、流式对话、实时 Token 统计、语音合成(TTS)与语音识别(STT)的端到端示例工程。

## 1. 功能特性

- 双通道对话:
  - 本地模型：基于 [`ChatHandler._setup_local_conversation`](ChatHandler.py) 使用 LangChain + [`ChatOllama`](ChatHandler.py)
  - 云端模型：OpenAI 兼容接口流式输出 [`ChatHandler._process_cloud_stream`](ChatHandler.py)
- 人格化角色系统：集中封装于 [`CharacterPromptManager.get_Elysia_prompt`](CharacterPromptManager.py)
- 全局会话记忆：统一历史存储与读取 [`GlobalChatMessageHistory`](PersistentChatHistory.py)
- Token 管理与用量统计：[`TokenManager`](TokenManager.py) 负责输入/输出、云端实际用量校准
- 流式响应协议（NDJSON 行模式）：
  - type=text | stream_complete | timing | done | error
  - 本地流：[`ChatHandler.handle_local_chat_stream`](ChatHandler.py)
  - 云端流：[`ChatHandler.handle_cloud_chat_stream`](ChatHandler.py)
- 语音能力：
  - TTS：[`AudioGenerateHandler`](AudioGenerateHandler.py) + 客户端流式播放器 [`WavStreamPlayer`](Client/core/wav_stream_player.py)
  - STT：[`AudioRecognizeHandler`](AudioRecognizeHandler.py)
  - 语音聊天入口：[`ChatHandler.handle_chat_with_audio`](ChatHandler.py)
- UI 客户端：
  - 主入口：[`ElysiaClient`](Client/Elysia.py)
  - 网络层：[`NetworkHandler`](Client/handlers/network_handler.py)
  - 流式管理：[`StreamingResponseManager`](Client/handlers/streaming_manager.py) + 去重过滤 [`ContentFilter`](Client/utils/content_filter.py)
  - WAV 流播放：[`WavStreamClient`](Client/core/wav_stream_player.py)
- 性能与计时：
  - 分阶段耗时统计：[`TimeTracker`](Utils.py)
  - 综合性能报告：[`PerformanceOptimizer`](Client/utils/performance_optimizer.py)
- 记忆与日总结（可选 Milvus）：
  - 日记忆摘要：[`DailyMemory.summary_daily_memory`](Memory.py)
- ID 生成与持久化：[`SyncMessageIDGenerator`](Utils.py), [`MessageIDGenerator`](Utils.py)
  
## 2. 目录结构概览

```
service.py                # 服务入口(FASTAPI)
ChatHandler.py            # 核心对话调度器
CharacterPromptManager.py # 人格提示模板
TokenManager.py           # Token 统计与持久化
AudioGenerateHandler.py   # 文本转语音
AudioRecognizeHandler.py  # 语音识别
PersistentChatHistory.py  # 全局历史
Client/                   # 桌面客户端（Tk + 网络 + 播放）
Memory.py / RAG.py        # 记忆 & RAG（可选）
```

## 3. 运行前提

- Python 3.11+
- 已安装并运行 Ollama（如本地模型：qwen2.5 / mistral 等）
- 可选：Milvus (记忆/RAG)
- 安装依赖：
  ```
  pip install -r requirements.txt
  ```
- 复制环境变量模板：
  ```
  cp .env_example .env
  ```
  并填写云端 API KEY、Ollama base_url 等。

## 4. 启动

1. 启动服务端：
   ```
   python service.py
   ```
2. 启动客户端：
   ```
   python Client/Elysia.py
   ```
3. 测试本地流式对话（示例 POST 路径以实际路由为准）：
   - 本地流：`/chat/text/stream/local`
   - 云端流：`/chat/text/stream/cloud`
   - 语音 → 文本 → 对话：`/chat/audio/stream/cloud`
   - TTS：`/tts/generate`

## 5. 流式协议说明

服务端通过 `application/x-ndjson` 连续输出多行 JSON：

示例（本地）：
```json
{"type":"text","content":"你好"}
{"type":"text","content":"，很高兴见到你～♪"}
{"type":"stream_complete","full_content":"你好，很高兴见到你～♪","output_tokens":42}
{"type":"usage","role":"local", "...": "..."}
{"type":"timing","timing":{"llm_processing":123}}
{"type":"done"}
```

客户端处理见：
- 流读取：[`NetworkHandler.stream_chat_async`](Client/handlers/network_handler.py)
- 文本追加：[`StreamingResponseManager.append_streaming_text`](Client/handlers/streaming_manager.py)
- 早期 TTS 触发：[`StreamingMessageHandler._check_and_trigger_early_tts`](Client/handlers/streaming_message_handler.py)

## 6. 人格提示

集中于：
- [`CharacterPromptManager.get_Elysia_prompt`](CharacterPromptManager.py)
- 附加符号语义结构（语气/动作/表情/心情）由模板字段控制：`response_structure`, `expression_template`

本地模型链路：
- 构建 Prompt：[`ChatHandler._setup_local_conversation`](ChatHandler.py)
- 使用 LangChain `MessagesPlaceholder` 注入历史。

## 7. Token 与计时

- 输入估算：[`TokenManager.count_tokens_approximate`](TokenManager.py)
- 云端实际用量对齐：[`TokenManager.adjust_cloud_tokens_with_actual_usage`](TokenManager.py)
- 阶段耗时：`TimeTracker.time_stage` 上下文包装（在 [`ChatHandler.handle_local_chat_stream`](ChatHandler.py) 等使用）

## 8. 音频流式播放

客户端边接收边播放：
- 播放核心：[`WavStreamPlayer.add_audio_chunk`](Client/core/wav_stream_player.py)
- 跳过 WAV 头部（前 44 字节）
- 状态统计：[`WavStreamPlayer.get_stats`](Client/core/wav_stream_player.py)

TTS 请求：
- 同步直连：[`WavStreamClient.stream_tts_audio`](Client/core/wav_stream_player.py)
- 异步 + 重试：[`WavStreamClient.stream_tts_audio_async`](Client/core/wav_stream_player.py)

## 9. 日志与错误

- 统一错误处理：[`ErrorHandler.handle_error`](Client/utils/error_handler.py)
- UI 安全更新：[`UIHelper`](Client/utils/ui_helpers.py)

## 10. 可选记忆 / RAG

- Milvus 连接：[`RAG`](RAG.py)
- 每日摘要：[`DailyMemory.summary_daily_memory`](Memory.py)

## 11. 事件类型汇总

| 类型 | 描述 | 产生位置 |
|------|------|----------|
| text | 增量内容 | `_process_local_stream` / `_process_cloud_stream` |
| stream_complete | 汇总内容/usage入口 | 同上 |
| timing | 阶段耗时 | `handle_local_chat_stream` |
| done | 完成标记 | 各主处理函数 |
| error | 错误信息 | 异常捕获块 |

## 12. 安全与测试数据说明

`test_dataset.py` 中包含内部压力/格式测试用的若干极端或不建议生产使用的指令片段，仅用于调试模型鲁棒性。请勿在生产环境直接暴露或继续传播不合规内容。部署请移除或替换该文件。

## 13. 常见问题

- 本地模型不输出：
  - 检查 Ollama 是否运行，模型名称与 [`ServiceConfig.local_model`](ServiceConfig.py) 一致
- 流式卡住：
  - 观察服务端是否正常 flush；检查网络/代理
- TTS 无声音：
  - 确认采样率与客户端播放器参数一致（32000Hz / mono / paInt16）
- Token 统计不更新：
  - 查看 `token_stats.json` 是否有写权限

## 14. 快速扩展指引

| 目标 | 修改位置 |
|------|----------|
| 新增角色人格 | 添加方法于 [`CharacterPromptManager`](CharacterPromptManager.py) 并在 [`ChatHandler._setup_local_conversation`](ChatHandler.py) 替换 system prompt |
| 支持多 Session 历史 | 扩展 `get_session_history`（当前返回全局单例） |
| 引入 RAG 检索 | 在 `_prepare_cloud_request` 加入检索结果上下文 |
| 增加响应后处理 | 扩展客户端 `ContentFilter` 或服务端在发送前包装 |

## 15. 运行示例（本地流）

```bash
curl -N -X POST http://127.0.0.1:8000/chat/text/stream/local \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'
```

客户端实时显示增量文本，并在结尾出现 Token / Timing / Done。

## 16. 状态统计

计时信息展示：[`MainUI.show_timing_info`](Client/ui/main_window.py)  
音频流状态：调用 `WavStreamClient.get_stats()` 获取实时 buffer / 已播字节。

---

如需最小整合调用，只需实例化并调用：
```python
from ServiceConfig import ServiceConfig
from ChatHandler import ChatHandler
handler = ChatHandler(ServiceConfig())
# await handler.handle_local_chat_stream("测试")
```

## 17. 免责声明
本项目示例代码仅供学习研究。请确保遵守所在司法辖区与服务平台的合规与内容政策。测试数据中的敏感/不当提示不代表项目立场，生产环境请清理。

---
简要核心文件：[`ChatHandler`](ChatHandler.py) · [`CharacterPromptManager`](CharacterPromptManager.py) · [`TokenManager`](TokenManager.py) · [`WavStreamPlayer`](Client/core/wav_stream_player.py) ·