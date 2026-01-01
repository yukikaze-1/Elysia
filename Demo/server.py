"""
Elysia Server 主程序入口 (FastAPI 版本)单机版本见 Demo/main.py
负责初始化各个组件并启动 FastAPI 服务
"""
from Server.App import ElysiaServer
from Config.Config import GlobalConfig, global_config

def main():
    # 加载配置
    config: GlobalConfig = global_config.load("/home/yomu/Elysia/Demo/config.yaml")
    # 初始化服务器
    server = ElysiaServer(config=config)
    # 运行服务器
    server.run()
    
    
if __name__ == "__main__":
    main()
    
    