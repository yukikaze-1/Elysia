"""
检查WAV流式播放所需依赖
"""

def check_dependencies():
    """检查所需依赖是否已安装"""
    print("🔍 检查WAV流式播放依赖...")
    
    missing_deps = []
    
    # 检查 pyaudio
    try:
        import pyaudio
        print("✅ pyaudio 已安装")
    except ImportError:
        print("❌ pyaudio 未安装")
        missing_deps.append("pyaudio")
    
    # 检查 requests
    try:
        import requests
        print("✅ requests 已安装")
    except ImportError:
        print("❌ requests 未安装") 
        missing_deps.append("requests")
    
    # 检查 numpy (可选，用于实时流播放)
    try:
        import numpy
        print("✅ numpy 已安装")
    except ImportError:
        print("⚠️ numpy 未安装 (可选依赖)")
    
    if missing_deps:
        print(f"\n❌ 缺少依赖: {', '.join(missing_deps)}")
        print("请运行以下命令安装:")
        for dep in missing_deps:
            if dep == "pyaudio":
                print(f"pip install {dep}")
                print("注意: Windows用户可能需要从 https://www.lfd.uci.edu/~gohlke/pythonlibs/ 下载预编译的wheel文件")
            else:
                print(f"pip install {dep}")
        return False
    else:
        print("\n✅ 所有必需依赖都已安装")
        return True

if __name__ == "__main__":
    check_dependencies()
