# 世界模型 × Agent 学习层——全面架构与实现蓝图

> 目标：给出一个可落地、可扩展的“世界模型（外部客观状态） + Agent 学习层（个体主观经验/技能）”的**端到端架构**，涵盖数据结构、模块边界、更新循环、训练与推理策略、多 Agent 协作、观测与安全。

---

## 0. 总览（一句话）

* **世界模型**：由**感知→实体→关系/环境→规则引擎→状态库**构成的**持续演化的数字孪生**；
* **Agent 学习层**：在共享世界之上，每个 Agent 拥有**记忆、人格/策略、技能/LoRA、RAG 检索**等私有能力；
* **交互模式**：**代码/算法维护世界**，**LLM 只查询/修改状态并进行高层决策**。

```
[传感器/事件] → 感知融合 → 实体/轨迹 → 世界状态库(时序/图) ←→ 规则引擎(物理/社交/任务)
                                                       ↑                       ↓
                                                  查询/补丁API            事件/约束生成
                                                       ↑                       ↓
                                                   Agent(记忆/LoRA/RAG/策略) → 行动计划 → 执行器
```

---

## 1. 分层模块与职责

### 1.1 感知与融合（Perception & Fusion）

* 输入：相机、LiDAR、麦克风、IMU、系统事件、外部API（天气/日程）。
* 处理：目标检测/跟踪（ID一致性）、语义分割、声源定位、SLAM、时钟同步。
* 输出：**观测帧**（Observation），提供实体候选与不确定性（置信度/协方差）。

### 1.2 实体与轨迹层（Entities & Tracks）

* 统一**实体模型**（人/物/区域/组织/抽象概念），维护：`state = {pose, vel, acc, attrs, last_seen, source}`。
* 轨迹估计：Kalman/UKF/粒子滤波；多源关联（JPDA/匈牙利算法）。

### 1.3 世界状态库（World State Store）

* **双表示**：

  * **时序列（Time-Series）**：实体随时间演化（便于预测与回放）。
  * **图结构（Graph/知识图谱）**：关系与语义（便于复杂查询）。
* 支持**版本与快照**（`t` 切片）、**Patch/Delta**、**事务**与**回滚**。

### 1.4 规则引擎（Rules Engine）

* 层级：

  1. **物理**（运动学/碰撞/约束/资源守恒）
  2. **Agent**（感知锥、反应延迟、能量/体力、行动上限）
  3. **社交/文化**（礼仪、权限、信任、组织结构）
  4. **环境/资源**（天气/昼夜/库存/衰减/刷新）
  5. **任务/叙事**（目标链、触发条件、胜负判断、一致性）
* 形式：**声明式规则（DSL）+ 程序化算子**；冲突解决：优先级/显式约束/成本最小化。

### 1.5 事件总线与调度（Event Bus & Scheduler）

* Tick（固定Δt）或事件驱动（Reactive）；
* 多模块订阅：感知更新、规则触发、Agent意图、执行完成、异常告警。

### 1.6 Agent（个体大脑）

* **私有组件**：

  * **人格/策略基线**（Prompt/Policy）
  * **短期记忆（STM）**：会话/最近观察摘要
  * **长期记忆（LTM）**：向量库 + 关键事实KV（如偏好、承诺）
  * **技能/工具**：函数/外部API/规划器
  * **LoRA/Adapter 插件**：人格风格、领域技能、近期经验固化
* **决策流程**：检索相关状态 → 规划（反思/自一致/树状思维）→ 生成意图/行动 → 调用执行器/提交Patch。

---

## 2. 数据结构（建议范式）

### 2.1 Entity（实体）

```json
{
  "id": "car_12",
  "type": "vehicle",
  "pose": {"x": 10.2, "y": -3.1, "theta": 1.57},
  "vel": {"vx": -2.0, "vy": 0.1},
  "acc": {"ax": 0.3, "ay": 0.0},
  "attrs": {"color": "red", "plate": "ABC-123"},
  "uncertainty": {"cov": [[0.1,0],[0,0.1]]},
  "last_seen": 1723690001,
  "sources": ["cam0","lidar1"]
}
```

### 2.2 Relation（关系）

```json
{"s": "person:me", "p": "talks_to", "o": "person:alice", "t": 1723690001, "weight": 0.8}
```

### 2.3 Event（事件）

```json
{
  "id": "evt_889",
  "type": "collision_risk",
  "at": 1723690003,
  "entities": ["car_12","person:me"],
  "score": 0.92,
  "predicted_at": 1723690005,
  "policy_hint": "yield"
}
```

### 2.4 Patch（状态变更）

```json
{
  "op": "update",
  "path": "/entities/car_12/vel",
  "value": {"vx": -2.3, "vy": 0.0},
  "agent": "me",
  "reason": "sensor_fusion_kf",
  "at": 1723690002
}
```

---

## 3. 核心更新循环（Pseudo-code）

```python
while True:
    dt = clock.tick()
    obs = sensors.read_all()                 # 1) 观测
    tracks = fuse_and_track(obs)             # 2) 目标关联/滤波
    world.apply_patches(from_tracks(tracks)) # 3) 写入世界状态（事务）
    inferred = rules.step(world, dt)         # 4) 规则推进（物理/社交/任务）
    world.apply_patches(inferred.patches)

    for agent in agents:
        ctx = query.world_slice(world, agent, radius=R, horizon=H)
        mem = agent.memory.retrieve(ctx)     # 5) 记忆检索（LTM/STM）
        plan = agent.reason(ctx, mem)        # 6) 规划/策略（LLM+工具）
        patches, actions = agent.act(plan)   # 7) 生成Patch与可执行动作
        world.apply_patches(patches)
        actuators.execute(actions)
```

---

## 4. 学习层：**世界** vs **Agent**

### 4.1 世界侧（通常**不**微调）

* **硬规则**：物理/社交/任务的确定性或半确定性逻辑；
* **统计/滤波**：Kalman/UKF/粒子；
* **预测器（可选）**：轨迹预测（LSTM/Transformer/GraphNet），但不改变“法则”，只给出**下一步估计**。

### 4.2 Agent 侧（**推荐使用 LoRA/Adapter/RAG**）

* **人格/风格**：LoRA（语气、口头禅、价值观边界）；
* **领域技能**：代码辅助、写作体裁、专业术语；
* **经验固化**：把近期高质量交互蒸馏为 SFT 小样本 → 周/日批量更新 LoRA；
* **RAG**：把稀疏、变化快的事实放入向量库/知识库，避免过度微调。

> 归纳：**世界共享、规则稳定；Agent 私有、持续进化。**

---

## 5. 查询与修改接口（API 轮廓）

### 5.1 查询（供 LLM/Agent 使用）

```
GET /world/slice?center=me&radius=5m&horizon=3s&fields=entities,events,relations
GET /world/entity/{id}
POST /world/query (Graph query/DSL)
```

### 5.2 修改（Patch）

```
POST /world/patches
Body: [Patch]
- 幂等ID、事务ID、冲突策略：last-write-wins | CRDT | 优先级
```

### 5.3 审计与回放

```
GET /world/timeline?from=t0&to=t1
GET /world/snapshot?t=t0
POST /world/replay?scenario=sc_001
```

---

## 6. 规则分层与冲突解决

* **优先级**：物理 > 安全 > 任务 > 社交 > 美学；
* **约束求解**：当多条规则冲突，用代价函数最小化（MPC/ILP/启发式）；
* **一致性检查**：实体唯一性、守恒律、边界条件（不允许瞬移/负库存）。

---

## 7. 多 Agent 协作与一致性

* **单真相源（SSOT）**：世界状态库是唯一权威；
* **乐观并发 + 版本戳**：Patch 带 `version`/`vector clock`；
* **视图裁剪**：每个 Agent 只见到与其相关的切片（权限/隐私/感知锥）；
* **通信**：事件总线（Kafka/Redis Streams/NATS）。

---

## 8. 记忆系统（Agent 私有）

* **STM**：当前会话 & 最近 N 次交互摘要（随对话窗口滚动）；
* **LTM**：向量库（Milvus/Weaviate/FAISS）；关键事实KV（承诺、偏好、禁忌）；
* **提炼器**：从世界事件与对话中抽取“可长期利用”的记忆卡片；
* **遗忘/衰减**：时间权重/使用频率/重要性（防膨胀与污染）。

---

## 9. LoRA/Adapter 策略（Agent）

* **插件化**：人格常驻、能力按需加载、近期经验批量固化；
* **并行合并**：非冲突 LoRA 可相加；冲突（两种人格）用**动态切换**；
* **离线合并**：经常共用的 LoRA → 统一蒸馏/合并为单适配器；
* **回滚**：每次训练生成新版本，支持 Canary 与 A/B。

---

## 10. 预测与模拟（可选增强）

* **短期物理预测**：恒速/恒加速度/KF外推；
* **社会行为预测**：基于历史交互的下一步意图（Graph-RNN/Transformer）；
* **蒙特卡洛预演**：对多候选行动在“虚拟未来”中评估风险与价值。

---

## 11. 观测性与安全

* **日志**：感知→融合→规则→Patch→Agent 决策全链路；
* **度量**：状态新鲜度、Patch 冲突率、预测误差、延迟/吞吐；
* **安全**：越权修改拦截、危险行动审计、红线规则（不可破坏的 Guardrails）；
* **沙箱**：Agent 先在模拟分区试跑，再提交真实 Patch。

---

## 12. 存储与部署参考

* **时序数据**：TimescaleDB/InfluxDB/Parquet（冷数据归档）；
* **图与关系**：Neo4j/RedisGraph/Postgres JSONB；
* **缓存**：Redis（状态热区/邻域切片）；
* **部署**：

  * 实时：感知/融合/规则/Agent 分离服务 + 事件总线；
  * 批处理：夜间训练 LoRA、重建索引、清理记忆；
  * 边缘：低时延模块下沉（融合/预测）。

---

## 13. 端到端示例（“我面前有车驶来”）

1. 感知：检测到 `car_12`，给出 `pose/vel`（置信度0.8）；
2. 融合：KF 更新速度为 `vx=-2.3`；
3. 规则：碰撞风险>0.9 → 触发 `collision_risk` 事件；
4. Agent 查询切片（半径5m，地平线3s）→ 检索LTM（我害怕迎面车辆的历史）；
5. 策略：礼让优先 + 安全红线 → 产出意图 `后退并语音提醒`；
6. 执行：提交 Patch（更新我位置规划）+ 调用执行器（移动/播报）。

---

## 14. 常见坑与缓解

* **Token 爆炸**：只给 LLM 切片摘要 + ID 可回指；
* **记忆污染**：记忆卡片需评分与去重，重要性门限；
* **LoRA 冲突**：人格/风格不可并挂；采用动态切换 + 版本治理；
* **状态漂移**：感知与预测差异大时强制重置/权重调整；
* **并发冲突**：使用事务+版本戳/CRDT；
* **调试困难**：全链路可视化（时间轴+图视图+事件热力图）。

---

## 15. 轻量落地 Checklist

* [ ] 定义 Entity/Relation/Event/Patch 四类结构
* [ ] 选一个世界状态库（JSONB/Graph + 时序）
* [ ] 写最小规则：运动学+安全红线
* [ ] 开事件总线，跑 Tick 循环
* [ ] 做 Agent 的查询切片 API
* [ ] 接入 LTM（向量库）与 LoRA 插件框架
* [ ] 打通端到端示例与回放工具

---

## 16. 最小可用接口（示例 DSL）

```
# 取邻域切片（含未来3s外推）
SLICE center=me radius=5m horizon=3s fields=entities,events,relations

# 写入速度更新（事务）
PATCH txn=tx_101 SET /entities/car_12/vel = {vx:-2.3, vy:0.0}
COMMIT tx_101

# 叙事规则：当 risk>0.8 时触发提醒
RULE when event.type=="collision_risk" and event.score>0.8 then emit "speak: 注意安全, 后退" priority=HIGH
```

---

> 有了这份蓝图，你可以从 **最小闭环** 开始（Sections 2/3/5/13/15），先让“世界自走 + Agent 决策”跑起来；随后再逐层加：社交规则、记忆提炼、LoRA 固化、蒙特卡洛预演与多 Agent 协作。
