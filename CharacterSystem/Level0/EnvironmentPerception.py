
"""
第0层：环境感知层 (EnvironmentPerception) 
职责:
    - 主动环境感知：通过各种传感器获取实时环境数据
    - 多模态数据融合：整合视觉、听觉、时间等多维度信息
    - 环境状态管理：维护完整的环境状态模型和变化历史
    - 环境变化检测：识别环境的动态变化并主动通知上层
"""
import time
from datetime import datetime

from CharacterSystem.Level0.AudioPerceptionModule import AudioPerceptionModule
from CharacterSystem.Level0.SpatialPerceptionModule import SpatialPerceptionModule
from CharacterSystem.Level0.TemporalPerceptionModule import TemporalPerceptionModule
from CharacterSystem.Level0.VisualPerceptionModule import VisualPerceptionModule

from CharacterSystem.Level0.SocialEnvironment import SocialEnvironment
from CharacterSystem.Level0.PhysicalEnvironment import PhysicalEnvironment

from Logger import setup_logger



class TemporalEnvironment:
    """时间环境"""
    def __init__(self):
        self.current_time: datetime = datetime.now()
        self.time_period: str = "下午"
        self.season: str = "春天"
        
    def get_current_time(self)->datetime:
        return datetime.now()

    def get_current_time_period(self):
        pass
    
    def get_current_season(self):
        pass

    def get_current_state(self):
        """获取当前时间环境状态"""
        return {
            "current_time": self.current_time,
            "time_period": self.time_period,
            "season": self.season
        }


class DigitalEnvironment:
    """数字环境"""
    def __init__(self):
        self.background_music: str = ""
        self.screen_content: str = ""
        self.notification_status: str = "无打扰"

    def get_current_state(self):
        """获取当前数字环境状态"""
        return {
            "background_music": self.background_music,
            "screen_content": self.screen_content,
            "notification_status": self.notification_status
        }


class EnvironmentPerception:
    def __init__(self):
        self.logger = setup_logger("EnvironmentPerception")
        # 感知模块管理
        self.perception_modules = {
            "visual": VisualPerceptionModule(),      # 视觉感知
            "audio": AudioPerceptionModule(),        # 听觉感知
            "temporal": TemporalPerceptionModule(),  # 时间感知
            "spatial": SpatialPerceptionModule(),    # 空间感知
            # 未来可扩展：触觉、嗅觉、IoT传感器等
        }
        
        # 环境状态模型
        self.current_environment = {
            "physical": PhysicalEnvironment(), # 物理环境
            "social": SocialEnvironment(),  # 社交环境
            "temporal": TemporalEnvironment(),  # 时间环境
            "digital": DigitalEnvironment()  # 数字环境
        }
        
        # 感知历史和变化追踪
        self.environment_history = []
        self.significant_changes = []
        self.continuous_sensing = True
        
    def perceive_environment(self):
        """主动感知当前环境"""
        perception_data = {}
        
        for module_name, module in self.perception_modules.items():
            if module.is_available():
                try:
                    # 主动感知
                    data = module.perceive()
                    perception_data[module_name] = data
                except Exception as e:
                    self.logger.warning(f"感知模块 {module_name} 出错: {e}")
        
        return self._fuse_perception_data(perception_data)
    
    def _fuse_perception_data(self, raw_data):
        """多模态数据融合"""
        # 视觉数据分析
        visual_data = raw_data.get("visual", {})
        lighting = self._analyze_lighting(visual_data)
        people_count = self._detect_people_count(visual_data)
        user_emotion = self._detect_user_emotion(visual_data)
        
        # 听觉数据分析
        audio_data = raw_data.get("audio", {})
        noise_level = self._analyze_noise_level(audio_data)
        background_music = self._detect_background_music(audio_data)
        voice_emotion = self._analyze_voice_emotion(audio_data)
        
        # 时间上下文分析
        temporal_data = self._get_temporal_context()
        
        # 跨模态融合判断
        fused_emotion = self._fuse_emotion_signals(user_emotion, voice_emotion)
        overall_atmosphere = self._assess_atmosphere(lighting, noise_level, background_music)
        
        return {
            "lighting": lighting,
            "noise_level": noise_level,
            "people_present": people_count,
            "user_emotion": fused_emotion,
            "background_music": background_music,
            "atmosphere": overall_atmosphere,
            "time_context": temporal_data,
            "location_type": self._classify_location(visual_data)
        }
    
    def detect_environment_changes(self):
        """检测环境变化"""
        current = self.perceive_environment()
        changes = self._compare_environments(self.current_environment, current)
        
        if changes:
            self.significant_changes.append({
                "timestamp": datetime.now(),
                "changes": changes,
                "previous": self.current_environment.copy(),
                "current": current,
                "impact_level": self._assess_change_impact(changes)
            })
            
            # 主动通知上层系统
            self._notify_upper_layers(changes)
        
        self.current_environment = current
        return changes
    
    def _notify_upper_layers(self, changes):
        """主动通知上层有环境变化"""
        for change in changes:
            if change["impact_level"] >= "medium":
                # 触发角色主动回应
                self.system.trigger_proactive_response(change)
    
    def continuous_monitor(self):
        """后台持续监控环境变化"""
        while self.continuous_sensing:
            try:
                self.detect_environment_changes()
                time.sleep(1)  # 每秒检查一次
            except Exception as e:
                self.logger.error(f"环境监控出错: {e}")
                time.sleep(5)  # 出错后等待5秒再重试
    
    def build_environment_prompt(self):
        """为其他层生成环境描述"""
        env = self.current_environment
        
        prompt = f"""
                ## 当前环境感知
                ### 物理环境
                - 光照条件：{env['physical']['lighting']}
                - 噪音水平：{env['physical']['noise_level']}
                - 空间类型：{env['physical']['location_type']}
                - 整体氛围：{env.get('atmosphere', '温馨')}

                ### 社交环境  
                - 在场人数：{env['social']['people_present']}
                - 用户情绪：{env['social']['user_emotion']}
                - 互动类型：{env['social']['interaction_type']}

                ### 时间环境
                - 当前时间：{env['temporal']['current_time'].strftime('%H:%M')}
                - 时段特征：{env['temporal']['time_period']}
                - 季节背景：{env['temporal']['season']}

                ### 数字环境
                - 背景音乐：{env['digital']['background_music'] or '无'}
                - 通知状态：{env['digital']['notification_status']}

                ### 近期环境变化
                {self._format_recent_changes()}
        """
        return prompt
    
    def get_environment_for_layer(self, layer_name):
        """为不同层提供定制化的环境信息"""
        base_env = self.current_environment
        
        if layer_name == "character":
            # 角色层需要情绪和氛围相关信息
            return {
                "user_emotion": base_env['social']['user_emotion'],
                "atmosphere": base_env.get('atmosphere'),
                "time_mood": self._get_time_mood(),
                "environmental_triggers": self._get_emotion_triggers()
            }
        elif layer_name == "context":
            # 上下文层需要场景和社交信息
            return {
                "scene_type": base_env['physical']['location_type'],
                "social_context": base_env['social'],
                "temporal_context": base_env['temporal'],
                "topic_suggestions": self._get_topic_suggestions()
            }
        elif layer_name == "processor":
            # 处理层需要输出调整相关信息
            return {
                "noise_level": base_env['physical']['noise_level'],
                "formality_level": self._assess_formality_need(),
                "attention_level": self._assess_user_attention()
            }
        
        return base_env