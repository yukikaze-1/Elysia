"""
音频感知模块
"""

class AudioPerceptionModule:
    def __init__(self):
        self.microphone = None
        self.audio_model = None  # 音频分析模型
        self.noise_detector = None
        self.music_detector = None
        
    def is_available(self):
        """检查音频感知模块是否可用"""
        return self.microphone is not None and self.audio_model is not None

    async def perceive(self):
        """听觉感知主函数"""
        if not self.microphone or not self.microphone.is_available():
            return self._get_default_audio_data()
            
        # 获取音频数据
        audio_data = self.microphone.record(duration=3)
        
        analysis_results = {}
        
        # 1. 基础音频分析
        noise_level = self._analyze_noise_level(audio_data)
        analysis_results["noise"] = noise_level
        
        # 2. 背景音乐检测
        if self.music_detector:
            music_info = self.music_detector.analyze(audio_data)
            analysis_results["music"] = music_info
        
        # 3. 语音情绪分析（如果有人声）
        voice_info = self._analyze_voice_content(audio_data)
        if voice_info["has_voice"]:
            analysis_results["voice"] = voice_info
        
        # 4. 环境音效识别
        ambient_sounds = self._detect_ambient_sounds(audio_data)
        analysis_results["ambient"] = ambient_sounds
        
        return {
            "noise_level": noise_level["level"],
            "noise_type": noise_level["type"],
            "background_music": analysis_results.get("music", {}).get("genre"),
            "music_mood": analysis_results.get("music", {}).get("mood"),
            "voice_emotion": analysis_results.get("voice", {}).get("emotion"),
            "ambient_sounds": ambient_sounds["sounds"],
            "overall_audio_mood": self._assess_audio_mood(analysis_results)
        }