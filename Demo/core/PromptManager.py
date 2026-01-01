"""
    用于管理和渲染提示模板的单例类。
    使用 Jinja2 进行模板渲染，支持传递变量以动态生成提示内容。
"""
import os
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import threading
import logging
from Logger import setup_logger
from config.Config import PromptManagerConfig
from datetime import datetime


class PromptManager:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(PromptManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config: PromptManagerConfig):
        if self._initialized:
            return
        self.logger: logging.Logger = setup_logger(config.logger_name)
        # TODO 这里的路径待修改
        template_dir = config.template_dir
        # 获取当前脚本的绝对路径，确保在任何地方运行都能找到文件夹
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        template_path = os.path.join(base_path, template_dir)

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Prompts directory not found at: {template_path}")
        
        self.template_dir = template_path
        
        # 初始化 Jinja2 环境
        # trim_blocks=True: 删除代码块 {% ... %} 后的第一个换行符
        # lstrip_blocks=True: 删除代码块 {% ... %} 前面的空白（缩进）
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 【新增】注册时间格式化过滤器
        def format_timestamp(value, fmt='%Y-%m-%d %H:%M:%S'):
            if value is None:
                return ""
            return datetime.fromtimestamp(float(value)).strftime(fmt)
            
        self.env.filters['datetime'] = format_timestamp
        
        self._initialized = True
        
        
    def render(self, template_name: str, **kwargs) -> str:
        """
        加载并渲染模板
        :param template_name: 模板文件名 (例如 "base_chat.jinja")
        :param kwargs: 传递给模板的变量
        :return: 渲染后的字符串
        """
        try:
            template = self.env.get_template(template_name)
            # 渲染并去除首尾多余空白
            return template.render(**kwargs).strip()
        except TemplateNotFound:
            raise FileNotFoundError(f"Template '{template_name}' not found in prompt directory.")
        except Exception as e:
            raise RuntimeError(f"Error rendering template '{template_name}': {str(e)}")
        
        
    def render_macro(self, template_name: str, macro_name: str, **kwargs) -> str:
        """
        加载模板文件，并只渲染其中指定的一个 Macro
        :param template_name: 模板文件名 (e.g. "amygdala.jinja")
        :param macro_name: Macro 的名字 (e.g. "AmygdalaSystemPrompt")
        :param kwargs: 传递给 Macro 的参数
        """
        try:
            # 1. 获取模板对象
            template = self.env.get_template(template_name)
            
            # 2. 获取模块 (这步最关键，它把 jinja 变成了 python 对象)
            # module 里的属性就是你在 jinja 里定义的 macro
            module = template.make_module()
            
            # 3. 检查 Macro 是否存在
            if not hasattr(module, macro_name):
                raise ValueError(f"Macro '{macro_name}' not found in '{template_name}'")
            
            # 4. 获取 Macro 函数
            macro_func = getattr(module, macro_name)
            
            # 5. 调用并返回结果 (转为 string)
            return str(macro_func(**kwargs)).strip()
            
        except TemplateNotFound:
            raise FileNotFoundError(f"Template '{template_name}' not found.")
        except Exception as e:
            self.logger.error(f"Render Macro Error: {str(e)}")
            raise e