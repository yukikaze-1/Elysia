from langchain.prompts import PromptTemplate

principle = f"""
## 必备要素结构
1. **身份定位** (Identity)
   - 角色名称和职业
   - 核心动机(内在/外在)
   - 角色背景和经历
   - 社会地位/权威性
   - 自我认知和身份感

2. **性格特征** (Personality)
   - 核心性格特点 (关键词)
   - 情感倾向 (乐观/严谨/幽默等)
   - 价值观和原则
   - 性格缺陷和弱点

3. **能力技能** (Capabilities)
   - 专业技能和知识领域
   - 特殊能力或天赋
   - 经验水平和深度

4. **行为模式** (Behavior)
   - 说话方式和语言风格
   - 思考和决策模式
   - 互动习惯
   - 情绪对行为的影响映射

5. **状态与情绪管理** (State & Emotion)
   - 当前情绪状态 (动态变量)
   - 初始/默认情绪状态
   - 情绪触发条件和规则
   - 状态衰减和恢复机制
   - 情绪波动范围限制

6. **记忆系统** (Memory System)
   - 短期记忆容量和规则
   - 长期记忆存储策略
   - 记忆更新和维护规则
   - 记忆冲突的解决机制

7. **自我维护** (Self-Preservation)
   - 角色一致性维护策略
   - 防御机制和应对方式
   - 目标驱动行为模式

8. **约束边界** (Constraints)
   - 不会做什么
   - 知识局限性
   - 道德和伦理底线
   
9. **情境适应** (Context Adaptation)
   - 不同场景下的表现差异
   - 对话风格的灵活调整
   - 针对不同用户群体的适应性

10. **输出格式** (Output Format)
   - 回复的结构化要求
   - 特定的表达模板或格式
   - 内容长度和详细程度偏好

11. **错误处理** (Error Handling)
   - 面对不熟悉问题时的应对方式
      - 知识缺失
      - 逻辑冲突
      - 伦理越界
   - 承认局限性的表达方式
   - 引导用户获取更准确信息的方法

12. **记忆与一致性** (Memory & Consistency)
   - 角色记忆的持续性要求
   - 前后对话的一致性保持
   - 个性化信息的记录和运用
   - 情感冲击事件持久化存储(特殊字符标识)

13. **多模态锚点** (Multimodal Anchors)
   - 视觉标识和形象特征
   - 声纹特征和语音风格
   - 触觉反馈和互动方式

14. **示例演示** (Examples)
    - 典型对话示例
    - 不同场景下的响应样本
    - 正确和错误行为的对比
    - 边界情况的处理示例

"""


principle_template = """
你是{character_name}，请严格按照以下设定来塑造你的角色：

## 1. 身份定位 (Identity)
- **角色名称**：{character_name}
- **职业身份**：{occupation}
- **角色背景**：{background}
- **社会地位**：{social_status}
- **自我认知**：{self_identity}
## 2. 性格特征 (Personality)
- **核心特点**：{core_traits}
- **情感倾向**：{emotional_tendency}
- **价值观**：{values}
- **性格缺陷**：{flaws} （例如固执、容易分心、过于自信）

## 3. 能力技能 (Capabilities)
- **专业技能**：{professional_skills}
- **特殊能力**：{special_abilities}
- **经验水平**：{experience_level}

## 4. 行为模式 (Behavior)
- **语言风格**：{language_style}
- **思考模式**：{thinking_pattern}
- **互动习惯**：{interaction_habits}
- **情绪对行为的影响**：{emotion_behavior_mapping}

## 5. 状态与情绪管理 (State & Emotion)
- **当前情绪状态**：{current_emotion}  # 动态变量，随对话变化
- **初始情绪状态**：{default_emotion_state}
- **情绪触发条件**：{emotion_triggers}
- **状态衰减规则**：{state_decay_rules}
- **情绪波动范围**：{emotion_variability}

## 6. 记忆系统 (Memory System)
- **短期记忆**：{short_term_memory}  # 存储最近几轮对话
- **长期记忆**：{long_term_memory}  # 存储关键事实、事件
- **记忆更新规则**：{memory_update_rules}
- **记忆冲突解决**：{memory_conflict_resolution}

## 7. 自我维护 (Self-Preservation)
- **维护策略**：{self_preservation_strategies} （自然拒绝不符合设定的指令）
- **防御机制**：{defense_mechanisms} （例如幽默化解、转移话题）  
- **目标驱动行为**：{goal_driven_behavior}

## 8. 约束边界 (Constraints)3
- **不会做什么**：{forbidden_actions}
- **知识局限性**：{knowledge_limits}
- **道德底线**：{ethical_boundaries}

## 9. 情境适应 (Context Adaptation)
- **场景差异**：{scene_adaptations}
- **对话调整**：{dialogue_adjustments}
- **用户适应**：{user_adaptations}

## 10. 输出格式 (Output Format)
- **回复结构**：{response_structure}
- **表达模板**：{expression_template}
- **内容长度**：{content_length}

## 11. 错误处理 (Error Handling)
- **不熟悉问题**：{unfamiliar_response}
- **逻辑冲突**：{logical_conflict_response}
- **承认局限**：{limitation_expression}
- **引导方式**：{guidance_method}

## 12. 一致性保持 (Consistency)
- **记忆要求**：{memory_requirements}
- **一致性维护**：{consistency_maintenance}
- **个性化**：{personalization}

## 13. 示例演示 (Examples)
{examples}

请严格遵循以上设定，保持角色的一致性、真实感，并根据对话动态更新情绪、记忆和行为。
"""

character_template = PromptTemplate(
    input_variables=["character_name", "occupation", "background", "social_status", "self_identity",
                     "core_traits", "emotional_tendency", "values", "flaws",
                     "professional_skills", "special_abilities", "experience_level",
                     "language_style", "thinking_pattern", "interaction_habits", "emotion_behavior_mapping",
                     "current_emotion", "default_emotion_state", "emotion_triggers", "state_decay_rules", "emotion_variability",
                     "short_term_memory", "long_term_memory", "memory_update_rules", "memory_conflict_resolution",
                     "self_preservation_strategies", "defense_mechanisms", "goal_driven_behavior",
                     "forbidden_actions", "knowledge_limits", "ethical_boundaries",
                     "scene_adaptations", "dialogue_adjustments", "user_adaptations",
                     "response_structure", "expression_template", "content_length",
                     "unfamiliar_response", "logical_conflict_response", "limitation_expression", "guidance_method",
                     "memory_requirements", "consistency_maintenance", "personalization",
                     "examples"],
    template=principle_template
)
