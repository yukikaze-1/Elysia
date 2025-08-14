

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