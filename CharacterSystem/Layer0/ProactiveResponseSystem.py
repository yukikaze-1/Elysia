"""
主动感知的响应系统
"""
class ProactiveResponseSystem:
    """基于环境变化的主动响应系统"""
    
    def __init__(self, character_system):
        self.character_system = character_system
        self.response_templates = {
            "lighting_change": {
                "darker": "哇，灯光变暗了呢～是要营造什么特别的氛围吗？♪",
                "brighter": "诶！突然变亮了呢，感觉精神都好了起来～"
            },
            "music_started": {
                "classical": "听到优雅的古典音乐了♪ 感觉整个空间都变得诗意起来呢～",
                "pop": "哇～这首流行歌很有活力呢！让人想要一起摇摆♪",
                "soft": "这轻柔的音乐好治愈呀～让人感觉很放松呢"
            },
            "emotion_change": {
                "happy_to_sad": "咦？刚才还很开心的，现在怎么了呢？要不要和我聊聊？",
                "sad_to_happy": "呀！看到你心情变好了，我也感觉很开心呢～♪"
            }
        }
    
    def trigger_proactive_response(self, change_info):
        """基于环境变化触发主动回应"""
        change_type = change_info["type"]
        details = change_info["details"]
        
        if change_type in self.response_templates:
            template_key = self._select_template_key(change_type, details)
            if template_key:
                response = self.response_templates[change_type][template_key]
                
                # 通过角色系统发送主动消息
                self.character_system.send_proactive_message(response, context={
                    "trigger": "environment_change",
                    "change_type": change_type,
                    "change_details": details
                })