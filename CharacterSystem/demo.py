from sympy import im
from Level0.EnvironmentPerception import EnvironmentPerception
from Level1.CharacterPromptManager import CharacterPromptManager
from Level2.VirtualCharacter import VirtualCharacter
from Level3.ConversationContext import ConversationContext
from Level4.ResponseProcessor import ResponseProcessor
from Level5.CharacterLearning import CharacterLearning

from Logger import setup_logger

from datetime import datetime

class CharacterSystemDemo:
    def __init__(self):
        self.logger = setup_logger("Demo")
        # 第0层：环境感知 (新增)
        self.environment = EnvironmentPerception()
        
        # 第1层：角色模板管理
        self.prompt_manager = CharacterPromptManager()
        
        # 第2层：角色实例
        self.character = VirtualCharacter(elysia_config)
        
        # 第3层：对话上下文
        self.context = ConversationContext()
        
        # 第4层：输出处理
        self.processor = ResponseProcessor(elysia_config)
        
        # 第5层：学习适应 (可选)
        self.learning = CharacterLearning()
        
        # 启动环境监控
        self._start_environment_monitoring()
        
    
    def _start_environment_monitoring(self):
        """启动后台环境监控"""
        import threading
        self.env_monitor_thread = threading.Thread(
            target=self.environment.continuous_monitor
        )
        self.env_monitor_thread.daemon = True
        self.env_monitor_thread.start()
        
    
    def chat(self, user_input, user_id=None):
        """完整的对话处理流程（增强版）"""
        
        # 第0层：获取当前环境状态
        env_changes = self.environment.detect_environment_changes()
        current_env = self.environment.current_environment
        
        # 如果环境有显著变化，可能触发主动回应
        if env_changes and self._should_respond_to_env_change(env_changes):
            proactive_response = self._generate_env_response(env_changes)
            if proactive_response:
                return proactive_response
        
        # 第2层：更新角色状态 (现在考虑环境因素)
        self.character.update_emotion(
            user_input, 
            env_context=current_env
        )
        self.character.update_memory("用户", user_input)
        
        # 第3层：更新对话上下文 (集成环境信息)
        env_context_data = self.environment.get_environment_for_layer("context")
        self.context.update_with_environment(env_context_data)
        self.context.detect_scene_change(user_input)
        self.context.update_user_profile({"last_input": user_input})
        
        # 构建完整prompt (现在包含环境感知)
        # 第1层：基础角色模板
        base_prompt = self.character.build_prompt(
            self.prompt_manager.get_character_by_name("爱莉希雅").prompt
        )
        
        # 第3层：对话上下文
        context_prompt = self.context.build_context_prompt()
        
        # 第0层：环境感知信息
        environment_prompt = self.environment.build_environment_prompt()
        
        # 组合完整prompt
        full_prompt = f"""
                {base_prompt}

                {context_prompt}

                {environment_prompt}

                用户输入：{user_input}
                请根据当前环境、上下文和你的角色设定自然地回复：
        """
        
        # 调用AI模型生成回复
        raw_response = self._call_ai_model(full_prompt, user_input)
        
        # 第4层：后处理 (考虑环境因素)
        env_processor_data = self.environment.get_environment_for_layer("processor")
        processed_result = self.processor.process_response(
            raw_response, 
            self.context,
            environment_context=env_processor_data
        )
        final_response = processed_result["response"]
        
        # 更新记忆和上下文
        self.character.update_memory("爱莉希雅", final_response)
        self.context.conversation_history.append({
            "user": user_input,
            "assistant": final_response,
            "environment": current_env.copy(),
            "timestamp": datetime.now()
        })
        
        # 第5层：学习适应 (包含环境学习)
        if user_id and hasattr(self, 'learning'):
            self.learning.learn_from_interaction(
                user_input, 
                final_response, 
                environment_context=current_env,
                feedback=None
            )
        
        return final_response
    
    def _should_respond_to_env_change(self, changes):
        """判断是否应该对环境变化主动回应"""
        for change in changes:
            if change.get("impact_level") in ["high", "very_high"]:
                return True
            if change.get("type") in ["user_emotion_change", "music_started"]:
                return True
        return False
    
    def _generate_env_response(self, changes):
        """基于环境变化生成主动回应"""
        # 让角色根据环境变化主动说话
        env_prompt = f"""
            环境发生了以下变化：{changes}
            请以爱莉希雅的身份，自然地对这些环境变化做出回应。
            保持她可爱、温暖的性格特点。
        """
        return self._call_ai_model(env_prompt, context="environment_change")
    
    def send_proactive_message(self, message, context=None):
        """发送主动消息给用户"""
        # 这里可以通过WebSocket、事件总线等方式主动推送消息
        print(f"[主动消息] {message}")
        
        # 记录主动消息到对话历史
        self.context.conversation_history.append({
            "type": "proactive",
            "assistant": message,
            "trigger": context,
            "timestamp": datetime.now()
        })
    
    def _call_ai_model(self, prompt, user_input=None, context=None):
        """调用AI模型接口"""
        # 这里接入你的AI模型API (OpenAI、Claude、本地模型等)
        # 示例实现
        try:
            response = your_ai_api.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.8
            )
            return response.content
        except Exception as e:
            self.logger.error(f"AI模型调用失败: {e}")
            return "抱歉，我刚才走神了呢～能再说一遍吗？♪"