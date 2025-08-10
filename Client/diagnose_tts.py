"""
诊断TTS问题的脚本
"""

def test_tts_configuration():
    """检查TTS配置状态"""
    try:
        from core.audio_manager import AudioManager
        
        audio_manager = AudioManager()
        
        print("=== TTS配置诊断 ===")
        print(f"WAV流式播放可用: {audio_manager.use_wav_streaming}")
        
        if hasattr(audio_manager, 'wav_stream_manager'):
            print(f"WAV流管理器: {audio_manager.wav_stream_manager}")
        else:
            print("WAV流管理器: 未初始化")
        
        # 测试TTS功能
        if audio_manager.use_wav_streaming:
            print("✅ TTS功能应该可用")
            
            # 测试一下TTS
            test_text = "这是一个测试"
            print(f"测试TTS播放: '{test_text}'")
            
            try:
                success = audio_manager.play_wav_stream_direct(test_text)
                print(f"TTS测试结果: {success}")
            except Exception as e:
                print(f"TTS测试失败: {e}")
        else:
            print("❌ TTS功能不可用")
            print("可能原因:")
            print("- WAV流式播放模块未正确加载")
            print("- 依赖项缺失")
            print("- 配置问题")
        
        return True
        
    except Exception as e:
        print(f"诊断失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_tts_configuration()
