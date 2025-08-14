"""
职责
    - 定义角色的基础架构和静态属性
    - 提供可复用的角色配置模板
    - 管理角色的核心设定和约束边界
"""

from typing import Dict, Any, List

from CharacterSystem.Layer1.Principle import principle, principle_template, character_template
from CharacterSystem.Layer1.DefaultPrompt import default_values, Elysia_values


class Character:
    """角色类，用于存储角色的基本信息和prompt"""
    def __init__(self, id: int, name: str, prompt: str) -> None:
        self.id: int = id
        self.name: str = name  # 支持中英文名
        self.prompt: str = prompt
    
    def __repr__(self) -> str:
        return f"Character(id={self.id}, name='{self.name}')"
    
    def get_prompt_preview(self, max_length: int = 200) -> str:
        """获取prompt的预览（截断显示）"""
        if len(self.prompt) <= max_length:
            return self.prompt
        return self.prompt[:max_length] + "..."


class CharacterPromptManager():
    """角色prompt管理器，用于创建、管理和维护角色配置"""
    
    def __init__(self) -> None:
        self.template = character_template
        self.principle = principle
        self.principle_template = principle_template
        self.characters: List[Character] = [Character(1, "爱莉希雅 (Elysia)", self.get_Elysia_prompt())]
    
    def create_character_prompt(self, **kwargs):
        """根据参数创建角色prompt"""
        # 检查必要参数
        required_params = ["character_name", "occupation", "background", "core_traits", "language_style"]
        missing_params = [param for param in required_params if param not in kwargs]
        if missing_params:
            raise ValueError(f"缺少必要参数: {missing_params}")
        
        # 填充默认值
        for key, default_value in default_values.items():
            if key not in kwargs:
                kwargs[key] = default_value
        
        return self.template.format(**kwargs)
    
    def add_character(self, character_id: int, name: str, **config) -> Character:
        """添加新角色"""
        # 确保character_name参数正确设置
        config['character_name'] = name
        prompt = self.create_character_prompt(**config)
        character = Character(character_id, name, prompt)
        self.characters.append(character)
        return character
    
    def get_character_by_id(self, character_id: int) -> Character:
        """根据ID获取角色"""
        for character in self.characters:
            if character.id == character_id:
                return character
        raise ValueError(f"未找到ID为 {character_id} 的角色")
    
    def get_character_by_name(self, name: str) -> Character:
        """根据名称获取角色"""
        for character in self.characters:
            if character.name == name:
                return character
        raise ValueError(f"未找到名为 {name} 的角色")
    
    def list_characters(self) -> List[Dict[str, Any]]:
        """列出所有角色信息"""
        return [{"id": char.id, "name": char.name} for char in self.characters]
    
    def validate_character_config(self, **config) -> List[str]:
        """验证角色配置的完整性"""
        warnings = []
        important_fields = [
            "character_name", "occupation", "background", "core_traits", 
            "language_style", "values", "forbidden_actions"
        ]
        
        for field in important_fields:
            if field not in config or not config[field]:
                warnings.append(f"重要字段 '{field}' 缺失或为空")
        
        return warnings
    
    def get_Elysia_prompt(self):
        """获取爱莉希雅的角色设定"""
        return self.create_character_prompt(**Elysia_values)


if __name__ == "__main__":
    manager = CharacterPromptManager()
    
    # 测试爱莉希雅角色
    print("=== 爱莉希雅角色测试 ===")
    elysia_prompt = manager.get_Elysia_prompt()
    print("角色prompt生成成功，长度:", len(elysia_prompt))
    
    print("\n=== 爱莉希雅完整Prompt ===")
    print(elysia_prompt)

