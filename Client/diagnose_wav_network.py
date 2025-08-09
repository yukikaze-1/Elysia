"""
WAV流式播放网络诊断工具
帮助诊断和解决网络连接问题
"""

import requests
import time
import json
from typing import Dict, Any


def test_tts_server_connection(server_url: str = "http://192.168.1.17:11100"):
    """测试TTS服务器连接"""
    print("🔍 TTS服务器连接诊断")
    print("=" * 50)
    
    # 测试基本连接
    try:
        print(f"📡 测试基本连接到: {server_url}")
        resp = requests.get(f"{server_url}/", timeout=5)
        print(f"✅ 基本连接成功，状态码: {resp.status_code}")
    except Exception as e:
        print(f"❌ 基本连接失败: {e}")
        return False
    
    # 测试TTS端点
    tts_url = f"{server_url}/tts/generate"
    test_text = "测试文本"
    
    try:
        print(f"🎵 测试TTS端点: {tts_url}")
        payload = {"text": test_text}
        
        # 首先测试非流式请求
        print("📝 测试普通POST请求...")
        resp = requests.post(tts_url, json=payload, timeout=10)
        print(f"   状态码: {resp.status_code}")
        print(f"   响应头: {dict(resp.headers)}")
        print(f"   内容长度: {len(resp.content)} 字节")
        
        if resp.status_code == 200:
            print("✅ 普通TTS请求成功")
        else:
            print(f"❌ 普通TTS请求失败: {resp.status_code}")
            print(f"   响应内容: {resp.text}")
            return False
            
    except Exception as e:
        print(f"❌ TTS端点测试失败: {e}")
        return False
    
    # 测试流式请求
    try:
        print("🌊 测试流式请求...")
        resp = requests.post(tts_url, json=payload, stream=True, timeout=(5, 30))
        print(f"   流式响应状态码: {resp.status_code}")
        print(f"   流式响应头: {dict(resp.headers)}")
        
        if resp.status_code == 200:
            print("✅ 流式TTS请求成功")
            
            # 测试接收前几个数据块
            print("📥 测试接收数据块...")
            chunk_count = 0
            total_size = 0
            
            try:
                for chunk in resp.iter_content(chunk_size=1024):
                    if not chunk:
                        continue
                    
                    chunk_count += 1
                    total_size += len(chunk)
                    
                    print(f"   接收块 {chunk_count}: {len(chunk)} 字节")
                    
                    # 只测试前5个块
                    if chunk_count >= 5:
                        print("   测试前5个块完成，停止接收")
                        break
                
                print(f"✅ 流式数据接收测试成功: {chunk_count} 块, 总计 {total_size} 字节")
                
            except Exception as stream_error:
                print(f"❌ 流式数据接收失败: {stream_error}")
                return False
            finally:
                resp.close()
        else:
            print(f"❌ 流式TTS请求失败: {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 流式请求测试失败: {e}")
        return False
    
    print("✅ 所有网络测试通过")
    return True


def test_wav_format_analysis(server_url: str = "http://192.168.1.17:11100/tts/generate"):
    """分析WAV格式输出"""
    print("\n🎵 WAV格式分析")
    print("=" * 50)
    
    try:
        test_text = "简短测试"
        payload = {"text": test_text}
        
        print(f"📝 请求简短文本: '{test_text}'")
        resp = requests.post(server_url, json=payload, timeout=10)
        
        if resp.status_code != 200:
            print(f"❌ 请求失败: {resp.status_code}")
            return False
        
        audio_data = resp.content
        print(f"📊 接收到音频数据: {len(audio_data)} 字节")
        
        # 分析WAV头部
        if len(audio_data) >= 44:
            print("🔍 分析WAV头部...")
            
            # RIFF 标识
            riff = audio_data[0:4].decode('ascii', errors='ignore')
            print(f"   RIFF标识: '{riff}'")
            
            # 文件大小
            file_size = int.from_bytes(audio_data[4:8], byteorder='little')
            print(f"   文件大小: {file_size} 字节")
            
            # WAVE 标识
            wave = audio_data[8:12].decode('ascii', errors='ignore')
            print(f"   WAVE标识: '{wave}'")
            
            # fmt 标识
            fmt = audio_data[12:16].decode('ascii', errors='ignore')
            print(f"   fmt标识: '{fmt}'")
            
            # 音频格式
            audio_format = int.from_bytes(audio_data[20:22], byteorder='little')
            print(f"   音频格式: {audio_format} (1=PCM)")
            
            # 声道数
            channels = int.from_bytes(audio_data[22:24], byteorder='little')
            print(f"   声道数: {channels}")
            
            # 采样率
            sample_rate = int.from_bytes(audio_data[24:28], byteorder='little')
            print(f"   采样率: {sample_rate} Hz")
            
            # 位深
            bits_per_sample = int.from_bytes(audio_data[34:36], byteorder='little')
            print(f"   位深: {bits_per_sample} 位")
            
            # data 标识
            data_marker = audio_data[36:40].decode('ascii', errors='ignore')
            print(f"   data标识: '{data_marker}'")
            
            # 数据大小
            data_size = int.from_bytes(audio_data[40:44], byteorder='little')
            print(f"   数据大小: {data_size} 字节")
            
            # 验证格式
            if riff == 'RIFF' and wave == 'WAVE' and fmt == 'fmt ' and data_marker == 'data':
                print("✅ WAV格式验证通过")
                
                # 检查参数匹配
                if sample_rate == 32000 and channels == 1 and bits_per_sample == 16:
                    print("✅ 音频参数匹配预期 (32kHz, 单声道, 16位)")
                else:
                    print(f"⚠️ 音频参数不匹配预期:")
                    print(f"   预期: 32000Hz, 1声道, 16位")
                    print(f"   实际: {sample_rate}Hz, {channels}声道, {bits_per_sample}位")
                
                return True
            else:
                print("❌ WAV格式验证失败")
                return False
        else:
            print(f"❌ 数据太短，无法分析WAV头部: {len(audio_data)} 字节")
            return False
    
    except Exception as e:
        print(f"❌ WAV格式分析失败: {e}")
        return False


def diagnose_stream_issue(server_url: str = "http://192.168.1.17:11100/tts/generate"):
    """诊断流式播放问题"""
    print("\n🔧 流式播放问题诊断")
    print("=" * 50)
    
    test_text = "这是一个WAV流式音频播放诊断测试。"
    payload = {"text": test_text}
    
    try:
        print(f"🌊 开始流式请求诊断...")
        print(f"📝 测试文本: '{test_text}'")
        
        # 设置详细的请求参数
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Connection': 'keep-alive',
            'User-Agent': 'WAV-Stream-Player/1.0'
        })
        
        start_time = time.time()
        
        resp = session.post(
            server_url, 
            json=payload, 
            stream=True,
            timeout=(10, 60),
            headers={'Accept': 'audio/wav, */*'}
        )
        
        print(f"📡 响应状态: {resp.status_code}")
        print(f"📋 响应头:")
        for key, value in resp.headers.items():
            print(f"     {key}: {value}")
        
        if resp.status_code != 200:
            print(f"❌ 请求失败: {resp.status_code}")
            print(f"   错误内容: {resp.text}")
            return False
        
        # 详细的流式接收测试
        chunk_count = 0
        total_size = 0
        chunk_sizes = []
        
        print("\n📥 开始接收流式数据...")
        
        try:
            for chunk in resp.iter_content(chunk_size=1024):
                if not chunk:
                    print("   收到空块，继续...")
                    continue
                
                chunk_count += 1
                chunk_size = len(chunk)
                total_size += chunk_size
                chunk_sizes.append(chunk_size)
                
                # 详细记录前10个块
                if chunk_count <= 10:
                    print(f"   块 {chunk_count}: {chunk_size} 字节")
                elif chunk_count % 20 == 0:
                    print(f"   已接收 {chunk_count} 块, 总计 {total_size//1024}KB")
                
                # 检查前几个字节
                if chunk_count == 1 and chunk_size >= 4:
                    header_start = chunk[:4].decode('ascii', errors='ignore')
                    print(f"   首块前4字节: '{header_start}'")
                    if header_start == 'RIFF':
                        print("   ✅ 检测到WAV文件头")
                    else:
                        print(f"   ⚠️ 非标准WAV头部: '{header_start}'")
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n📊 接收完成统计:")
            print(f"   总块数: {chunk_count}")
            print(f"   总大小: {total_size} 字节 ({total_size//1024}KB)")
            print(f"   接收时间: {duration:.2f} 秒")
            print(f"   平均速度: {total_size/duration/1024:.1f} KB/s")
            
            if chunk_sizes:
                print(f"   平均块大小: {sum(chunk_sizes)/len(chunk_sizes):.1f} 字节")
                print(f"   最小块大小: {min(chunk_sizes)} 字节")
                print(f"   最大块大小: {max(chunk_sizes)} 字节")
            
            if total_size > 0:
                print("✅ 流式接收诊断成功")
                return True
            else:
                print("❌ 未接收到任何数据")
                return False
        
        except Exception as stream_error:
            print(f"❌ 流式接收过程出错: {stream_error}")
            print(f"   已接收: {chunk_count} 块, {total_size} 字节")
            return False
        
        finally:
            resp.close()
            session.close()
    
    except Exception as e:
        print(f"❌ 流式诊断失败: {e}")
        return False


def main():
    """主诊断函数"""
    print("🔍 WAV流式播放网络诊断工具")
    print("=" * 60)
    
    server_url = "http://192.168.1.17:11100"
    
    try:
        # 基本连接测试
        if not test_tts_server_connection(server_url):
            print("\n❌ 基本连接测试失败，无法继续")
            return
        
        # WAV格式分析
        if not test_wav_format_analysis(f"{server_url}/tts/generate"):
            print("\n❌ WAV格式分析失败")
            return
        
        # 流式问题诊断
        if not diagnose_stream_issue(f"{server_url}/tts/generate"):
            print("\n❌ 流式播放诊断失败")
            return
        
        print("\n✅ 所有诊断测试通过！")
        print("💡 建议:")
        print("   1. 服务器连接正常")
        print("   2. WAV格式输出正确")
        print("   3. 流式传输功能正常")
        print("   4. 可以尝试重新运行WAV流式播放测试")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断诊断")
    except Exception as e:
        print(f"\n❌ 诊断过程异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
