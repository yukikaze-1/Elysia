import requests
import pyaudio

test_text_01 = "大概率是没有的，我也希望如此，毕竟自己的故事还是应当由自己来诉说。对我而言，那是在遥远的过去曾经发生的事，而对你来说，那是在不久的将来将要发生的事。"

url = "http://192.168.1.17:11100/tts/generate"

payload = {
    "text": test_text_01
}


# PyAudio 配置
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 32000


p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK)

import time
start_time = time.time()
resp = requests.post(url, json=payload, stream=True)

# 跳过WAV头部（前44字节）
header_skipped = False
audio_data = b""
flag = True
# time.sleep(0.1)  # 确保连接稳定
for chunk in resp.iter_content(chunk_size=1024):
    audio_data += chunk
    
    if not header_skipped and len(audio_data) >= 44:
        # 跳过WAV文件头
        audio_data = audio_data[44:]
        header_skipped = True
    
    if header_skipped and len(audio_data) >= CHUNK:
        # 播放音频数据
        if flag:
            end_time = time.time()
            flag = False
            print(f"Audio chunk played in {end_time - start_time:.2f} seconds")
        stream.write(audio_data[:CHUNK])
        audio_data = audio_data[CHUNK:]

# 播放剩余数据
if audio_data:
    stream.write(audio_data)

stream.stop_stream()
stream.close()
p.terminate()