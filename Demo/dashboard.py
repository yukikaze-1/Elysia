import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# === 配置 ===
API_URL = "http://192.168.1.18:8000"
REFRESH_RATE = 1.0  # 刷新频率(秒)

st.set_page_config(
    page_title="Elysia Monitor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# === CSS 美化 ===
st.markdown("""
<style>
    /* 全局字体优化 */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    
    /* 卡片样式 */
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    
    /* 状态指示灯 */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 5px;
    }
    .status-on { background-color: #28a745; box-shadow: 0 0 5px #28a745; }
    .status-off { background-color: #dc3545; }
    
    /* 思维链气泡 */
    .thought-bubble {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 10px 15px;
        border-radius: 0 10px 10px 0;
        margin-bottom: 10px;
        font-style: italic;
        color: #0d47a1;
    }
    .reply-bubble {
        background-color: #ffffff;
        border: 1px solid #ddd;
        padding: 10px 15px;
        border-radius: 10px;
        color: #333;
    }
    
    /* 记忆日志表格优化 */
    .dataframe { font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)

def fetch_state():
    """从 FastAPI 获取全量状态"""
    try:
        resp = requests.get(f"{API_URL}/dashboard/snapshot", timeout=0.5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None
    return None

def format_timestamp(ts):
    """格式化时间戳"""
    if isinstance(ts, (int, float)) and ts > 0:
        return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    return "Never"

# === 主界面 ===
st.title("🧠 Elysia Neural Dashboard")

# 占位容器，用于自动刷新
main_container = st.empty()

while True:
    state = fetch_state()
    
    with main_container.container():
        if not state:
            st.error("⚠️ Connection Lost. Waiting for Elysia Server...")
            time.sleep(2)
            continue

        # ==========================================
        # 1. 顶栏：系统健康度 & 核心指标 (System & L3)
        # ==========================================
        sys = state.get("system", {})
        l3 = state.get("l3_persona", {})
        l0 = state.get("l0_sensor", {})
        actuator = state.get("actuator", {})
        
        # 使用 HTML 自定义状态栏
        dispatcher_status = "status-on" if sys.get("dispatcher_alive") else "status-off"
        
        cols = st.columns([1, 1, 1, 1, 2])
        
        with cols[0]:
            st.markdown(f'<div class="metric-card"><b>Dispatcher</b><br><span class="status-indicator {dispatcher_status}"></span>{"Alive" if sys.get("dispatcher_alive") else "Dead"}</div>', unsafe_allow_html=True)
            
        with cols[1]:
            st.markdown(f'<div class="metric-card"><b>Online Clients</b><br>🔌 {sys.get("online_clients", 0)}</div>', unsafe_allow_html=True)
            
        with cols[2]:
            st.markdown(f'<div class="metric-card"><b>Input Queue</b><br>📥 {l0.get("input_queue_size", 0)}</div>', unsafe_allow_html=True)

        with cols[3]:
            # Mood 显示
            mood = l3.get("mood", "Neutral")
            mood_color = "orange" if mood in ["Sad", "Angry"] else "green"
            st.markdown(f'<div class="metric-card"><b>Current Mood</b><br><span style="color:{mood_color}; font-weight:bold">{mood}</span></div>', unsafe_allow_html=True)

        with cols[4]:
            # Actuator Channels
            channels = actuator.get("registered_channels", [])
            st.markdown(f'<div class="metric-card"><b>Actuator Channels</b><br>📢 {", ".join(channels)}</div>', unsafe_allow_html=True)

        # ==========================================
        # 2. 核心功能区 (Tabs)
        # ==========================================
        tab_brain, tab_memory, tab_reflector, tab_raw = st.tabs(["🧠 Brain & Thought", "💾 Memory & Session", "🪞 Reflector Logs", "📝 Raw Data"])
        
        # --- Tab 1: Brain (L1) ---
        with tab_brain:
            l1 = state.get("l1_brain", {})
            col_b1, col_b2 = st.columns([1, 2])
            
            with col_b1:
                st.info("Configuration")
                st.text(f"Model: {l1.get('model_name')}")
                st.text(f"Temp:  {l1.get('temperature')}")
                
                # 显示 System Prompt (折叠)
                with st.expander("Show L3 System Prompt"):
                    st.code(l3.get("prompt", ""), language="text")

            with col_b2:
                st.subheader("Last Thinking Process")
                log = l1.get("last_thinking_log")
                
                if log:
                    # 区分主动回复 (Active) 和 被动回复 (Normal)
                    is_active = "should_speak" in log
                    
                    if is_active:
                        st.caption(f"Type: Active Decision | Should Speak: {log.get('should_speak')}")
                        inner = log.get("inner_voice", "")
                    else:
                        st.caption("Type: Response Generation")
                        inner = log.get("inner_thought", "")
                    
                    # 渲染思维气泡
                    if inner:
                        st.markdown(f"""
                        <div class="thought-bubble">
                            <b>💭 Inner Thought:</b><br>{inner}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # 渲染回复气泡
                    reply = log.get("public_reply")
                    if reply:
                        st.markdown(f"""
                        <div class="reply-bubble">
                            <b>🗣️ Elysia:</b> {reply}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("*No public reply generated.*")
                else:
                    st.warning("No thoughts recorded yet.")

        # --- Tab 2: Memory (L2) ---
        with tab_memory:
            l2 = state.get("l2_memory", {})
            sess = l2.get("session_status", {})
            
            # 顶部指标
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Session Role", sess.get("role", "AI"))
            m2.metric("User Name", sess.get("user_name", "User"))
            
            # 消息窗口进度条
            curr = sess.get("total_messages", 0)
            limit = sess.get("max_messages_limit", 20)
            # 防止除以0错误
            progress = min(curr / limit, 1.0) if limit > 0 else 0
            m3.metric("Context Window", f"{curr} / {limit}")
            m3.progress(progress)
            
            m4.metric("Last Interaction", format_timestamp(sess.get("last_interaction_time", 0)))
            
            st.divider()
            
            # === 新增：聊天记录可视化 ===
            st.subheader("💬 Recent Conversation (Context Window)")
            
            # 获取你新加的字段
            recent_msgs = sess.get("last_few_messages", [])
            
            if recent_msgs:
                # 创建一个聊天容器
                chat_container = st.container(height=400) # 固定高度，可滚动
                with chat_container:
                    for msg in recent_msgs:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        
                        # 映射头像
                        if role == "妖梦":
                            avatar = "👤"
                            # 也可以根据你的 UserMessage 结构显示时间戳
                            # ts = format_timestamp(msg.get("client_timestamp", 0))
                        else:
                            avatar = "🤖" # 或者用你的 Elysia 头像 URL
                            
                        # 使用 Streamlit 原生聊天组件
                        with st.chat_message(name=role, avatar=avatar):
                            st.markdown(content)
            else:
                st.info("No conversation history yet.")

            st.divider()
            
            # 底部显示向量库信息
            st.caption(f"📚 Vector DB: Micro='{l2.get('micro_memory_collection')}' | Macro='{l2.get('macro_memory_collection')}'")
            
        # --- Tab 3: Reflector ---
        with tab_reflector:
            ref = state.get("reflector", {})
            
            # ==================================================
            # 1. 暴力寻路 (Robust Data Finder)
            # ==================================================
            # 定义一个内部函数，专门用来在字典里找 "last_macro_reflection_log"
            def find_key_in_dict(source_dict, target_key):
                # A. 直接在当前层找
                if target_key in source_dict:
                    return source_dict[target_key]
                # B. 在子字典里找 (比如 macro_reflector_status)
                for key, value in source_dict.items():
                    if isinstance(value, dict) and target_key in value:
                        return value[target_key]
                return None

            # 查找 Macro 数据
            macro_logs = find_key_in_dict(ref, "last_macro_reflection_log") or []
            macro_time = find_key_in_dict(ref, "last_macro_reflection_time") or "Never"
            
            # 查找 Micro 数据
            micro_logs = find_key_in_dict(ref, "last_micro_reflection_log") or []
            micro_time = find_key_in_dict(ref, "last_micro_reflection_time") or "Never"
            
            # 缓冲池大小 (通常直接在 ref 层)
            buffer_size = ref.get("buffer_size", 0)

            # ==================================================
            # 2. 渲染界面
            # ==================================================
            
            # 概览指标
            r1, r2, r3 = st.columns(3)
            r1.metric("Buffer Size", buffer_size)
            r2.metric("Last Micro Run", str(micro_time))
            r3.metric("Last Macro Run", str(macro_time))
            
            st.divider()
            
            col_micro, col_macro = st.columns([1, 1.3])
            
            # --- Micro Logs ---
            with col_micro:
                st.subheader(f"Micro-Reflections ({len(micro_logs)})")
                if micro_logs and isinstance(micro_logs, list):
                    # 数据清洗：转字符串防止渲染错误
                    clean_micro = [{k: str(v) for k, v in item.items()} for item in micro_logs]
                    st.dataframe(clean_micro, use_container_width=True, hide_index=True)
                else:
                    st.info("No micro-memories yet.")

            # --- Macro Logs (修复重点) ---
            with col_macro:
                st.subheader(f"Macro-Reflections ({len(macro_logs)})")
                
                if macro_logs and isinstance(macro_logs, list):
                    for i, log in enumerate(macro_logs):
                        # 提取数据
                        ts = log.get("timestamp", 0)
                        # 如果 timestamp 是 float/int，尝试格式化，否则直接显示
                        if isinstance(ts, (int, float)):
                            time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                        else:
                            time_str = str(ts)
                            
                        emotion = log.get("dominant_emotion", "Unknown")
                        poignancy = log.get("poignancy", "?")
                        subject = log.get("subject", "General")
                        
                        label = f"📅 {time_str} | {subject} - {emotion} (Intensity: {poignancy})"
                        
                        with st.expander(label, expanded=(i==0)):
                            # 标签渲染
                            tags = log.get("keywords", [])
                            if isinstance(tags, list):
                                st.markdown(" ".join([f"`#{t}`" for t in tags]))
                            
                            st.divider()
                            
                            # 内容渲染
                            content = log.get("diary_content", "No content")
                            st.caption("Diary Content:")
                            st.markdown(f"> {content}")
                            
                            # 原始数据调试 (可选)
                            # st.json(log)
                else:
                    st.info("No macro-memories yet.")
                    
                    # === 终极调试面板 ===
                    # 如果还是显示不出来，展开这个看看到底 ref 长什么样
                    with st.expander("🕵️ Debug: Inspect Raw Reflector State", expanded=False):
                        st.write("Streamlit sees this data structure for 'reflector':")
                        st.json(ref)

        # --- Tab 4: Raw Data ---
        with tab_raw:
            st.json(state)

    time.sleep(REFRESH_RATE)