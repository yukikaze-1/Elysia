"""
Elysia Server 主程序入口 (FastAPI 版本)单机版本见 Demo/main.py
负责初始化各个组件并启动 FastAPI 服务
"""
from Server.App import ElysiaServer


def main():
    server = ElysiaServer()
    server.run()
    
    
if __name__ == "__main__":
    main()
    
    