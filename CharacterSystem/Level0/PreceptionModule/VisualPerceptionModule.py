"""
视觉感知模块
"""
class VisualPerceptionModule:
    def __init__(self):
        self.camera = None
        self.vision_model = None  # 视觉大模型（如GPT-4V、Claude Vision等）
        self.face_detector = None
        self.emotion_detector = None

    def is_available(self):
        """检查视觉感知模块是否可用"""
        return self.camera is not None and self.vision_model is not None

    def perceive(self):
        """视觉感知主函数"""
        if not self.camera or not self.camera.is_available():
            return self._get_default_visual_data()
            
        # 获取图像
        image = self.camera.capture()
        
        # 多维度分析
        analysis_results = {}
        
        # 1. 基础场景理解
        scene_analysis = self.vision_model.analyze(image, prompt=
            "描述这个场景的：1)光照条件 2)室内/室外类型 3)整体氛围 4)可见物品"
        )
        analysis_results["scene"] = scene_analysis
        
        # 2. 人物检测和情绪分析
        if self.face_detector:
            faces = self.face_detector.detect(image)
            if faces:
                emotions = self.emotion_detector.analyze(faces[0])  # 分析主要人物
                analysis_results["person"] = {
                    "count": len(faces),
                    "primary_emotion": emotions["dominant_emotion"],
                    "emotion_confidence": emotions["confidence"]
                }
        
        # 3. 环境细节提取
        environment_details = self._extract_environment_details(image)
        analysis_results["environment"] = environment_details
        
        return {
            "raw_image": image,
            "lighting": scene_analysis.get("lighting", "适中"),
            "location_type": scene_analysis.get("location", "室内"),
            "people_count": analysis_results.get("person", {}).get("count", 0),
            "user_emotion": analysis_results.get("person", {}).get("primary_emotion", "中性"),
            "atmosphere": scene_analysis.get("atmosphere", "平静"),
            "visible_objects": environment_details.get("objects", []),
            "colors_dominant": environment_details.get("colors", [])
        }
    
    def _extract_environment_details(self, image):
        """提取环境细节"""
        # 使用视觉模型分析图像中的物品、颜色等
        details = self.vision_model.analyze(image, prompt=
            "列出图像中的主要物品，主导色彩，以及任何值得注意的环境特征"
        )
        return details