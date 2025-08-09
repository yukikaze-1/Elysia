"""
Elysia 客户端配置文件
"""

class Config:
    """应用配置类"""
    
    # API配置
    API_BASE_URL = "http://192.168.1.17:11100"
    
    # 音频配置
    AUDIO_CHUNK_SIZE = 16384  # 16KB
    MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    SUPPORTED_AUDIO_FORMATS = [
        ("音频文件", "*.wav *.mp3 *.m4a *.flac *.aac"),
        ("WAV文件", "*.wav"),
        ("MP3文件", "*.mp3"),
        ("所有文件", "*.*")
    ]
    
    # 服务端音频配置 - 严格匹配服务端参数
    SERVER_AUDIO_CONFIG = {
        'sample_rate': 32000,     # 服务端固定采样率
        'channels': 1,            # 服务端固定单声道
        'bit_depth': 16,          # 服务端固定16位
        'format': 'wav',          # 服务端输出格式
        'chunk_size': 8192        # 服务端固定块大小
    }
    
    # pygame音频初始化参数 - 匹配服务端配置 (32000Hz, 1声道, 16位)
    PYGAME_AUDIO_CONFIG = {
        'frequency': 32000,       # 匹配服务端采样率
        'size': -16,              # 16位采样位宽 (负数表示有符号)
        'channels': 1,            # 单声道，匹配服务端
        'buffer': 1024
    }
    
    # 实时音频流配置 - 匹配服务端配置
    REALTIME_AUDIO_CONFIG = {
        'sample_rate': 32000,     # 采样率 - 匹配服务端32000Hz
        'channels': 1,            # 声道数 - 匹配服务端单声道
        'chunk_size': 1024,       # 每次播放的块大小
        'min_buffer_size': 4096,  # 最小缓冲区大小
        'max_buffer_size': 32768, # 最大缓冲区大小
        'latency': 'low'          # 延迟设置
    }
    
    # WAV流式处理配置
    WAV_STREAMING_CONFIG = {
        'accumulation_threshold': 32768,    # WAV数据积累阈值 (32KB)
        'initial_chunks_wait': 4,           # 初始等待的块数
        'chunk_processing_batch': 5,        # 每次处理的块数
        'playback_retry_delay': 0.5,        # 播放重试延迟(秒)
        'enable_partial_playback': True,    # 启用部分数据播放
        'buffer_safety_margin': 0.8         # 缓冲区安全边界
    }
    
    # 流式音频缓冲区配置（类似 MediaSource API）
    STREAM_BUFFER_CONFIG = {
        'max_buffer_size': 1024 * 1024,    # 1MB最大缓冲区
        'auto_play_threshold': 32768,       # 32KB自动播放阈值(适合WAV)
        'max_chunks_per_cycle': 5,          # 每次最多处理的块数
        'buffer_utilization_target': 0.7,   # 目标缓冲区利用率
        'status_update_interval': 5,        # 状态更新间隔（块数，降低频率）
        'wav_minimum_data': 16384           # WAV最小数据要求
    }
    
    # 网络配置
    REQUEST_TIMEOUT = 120
    CONNECTION_TIMEOUT = 60
    STREAM_BUFFER_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_LINE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FIELD_SIZE = 10 * 1024 * 1024  # 10MB
    
    # UI配置
    WINDOW_SIZE = "800x600"
    FONT_FAMILY = "Microsoft YaHei"
    FONT_SIZE = 10
    TITLE_FONT_SIZE = 16
    
    # 显示配置
    SHOW_TIMING_INFO = True  # 是否显示计时信息
    TIMING_PRECISION = 1     # 计时显示精度（小数位数）
    SHOW_REQUEST_TIME = True # 是否显示请求响应时间
    REQUEST_TIME_PRECISION = 2  # 请求时间显示精度
    SHOW_CHAT_AUDIO_TIME = True   # 是否显示聊天音频响应时间
    CHAT_AUDIO_TIME_PRECISION = 2 # 聊天音频时间显示精度
    SHOW_AUDIO_TIME = True   # 是否显示普通音频响应时间（向后兼容）
    AUDIO_TIME_PRECISION = 2 # 普通音频时间显示精度（向后兼容）
    SHOW_TOTAL_AUDIO_TIME = True   # 是否显示从请求到开始播放的总耗时
    TOTAL_AUDIO_TIME_PRECISION = 2 # 总音频耗时显示精度
    
    # 内容过滤配置
    SIMILARITY_THRESHOLD = 0.95
    DUPLICATE_CHECK_LENGTH = 50
    LINE_SIGNATURE_LENGTH = 30
    
    # 流式更新配置
    STREAMING_UPDATE_INTERVAL = 0.1  # 流式更新最小间隔（秒）
    MAX_CONSECUTIVE_UPDATES = 10     # 最大连续更新次数
    ENABLE_UPDATE_THROTTLING = True  # 是否启用更新频率控制
    
    # 清理配置
    TEMP_FILE_CLEANUP_DELAY = 60000  # 60秒
    STREAMING_FILE_CLEANUP_DELAY = 30000  # 30秒
