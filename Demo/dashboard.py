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
    
    /* 进度条容器优化 */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4caf50, #8bc34a);
    }
    
    /* 给不同状态定义颜色类 (需配合 st.markdown 使用 html 渲染，但 Streamlit 原生 progress 颜色受限，
       这里主要优化文字显示) */
    .stat-label { font-size: 0.8rem; color: #666; margin-bottom: -5px; }
    .stat-value { font-size: 1.5rem; font-weight: bold; }
    .warning { color: #ff9800; }
    .danger { color: #dc3545; }
    .success { color: #28a745; }
    
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
        return datetime.fromtimestamp(int(ts)).strftime("%H:%M:%S")
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

        # 获取各层数据
        sys = state.get("system", {})
        l3 = state.get("l3_persona", {})
        l0 = state.get("l0_sensor", {})
        actuator = state.get("actuator", {})
        psyche = state.get("psyche", {})     # <--- 获取新增的 Psyche 数据
        psyche_cfg = psyche.get("config", {}) # 获取配置

        # ==========================================
        # 1. 顶栏：系统健康度 & L3 人设状态
        # ==========================================
        dispatcher_status = "status-on" if sys.get("dispatcher_alive") else "status-off"
        
        # 定义 5 列布局
        cols = st.columns([1, 1, 1, 1, 2])
        
        with cols[0]:
            st.markdown(f'<div class="metric-card"><b>Dispatcher</b><br><span class="status-indicator {dispatcher_status}"></span>{"Alive" if sys.get("dispatcher_alive") else "Dead"}</div>', unsafe_allow_html=True)
            
        with cols[1]:
            st.markdown(f'<div class="metric-card"><b>Online Clients</b><br>🔌 {sys.get("online_clients", 0)}</div>', unsafe_allow_html=True)
            
        with cols[2]:
            st.markdown(f'<div class="metric-card"><b>Input Queue</b><br>📥 {l0.get("input_queue_size", 0)}</div>', unsafe_allow_html=True)

        with cols[3]:
            # === [展示 1] L3 Mood (人设表现出的心情 - String) ===
            l3_mood = l3.get("mood", "Neutral")
            mood_color = "orange" if l3_mood in ["Sad", "Angry"] else "green"
            st.markdown(f'<div class="metric-card"><b>L3 Persona Mood</b><br><span style="color:{mood_color}; font-weight:bold">{l3_mood}</span></div>', unsafe_allow_html=True)

        with cols[4]:
            channels = actuator.get("registered_channels", [])
            st.markdown(f'<div class="metric-card"><b>Actuator Channels</b><br>📢 {", ".join(channels)}</div>', unsafe_allow_html=True)

        st.divider()

        # ==========================================
        # 2. [新增] 生理与心理监控 (Psyche System)
        #    这里插入你的新模块，位于 Top Bar 和 Tabs 之间
        # ==========================================
        st.subheader("🧬 Physiological & Internal State")
        
        # 布局：4 列 (精力 | 社交 | 无聊 | 内在心情)
        p1, p2, p3, p4 = st.columns(4)
        
        # --- A. Energy (精力) ---
        with p1:
            energy = float(psyche.get("energy", 100))
            max_energy = float(psyche_cfg.get("max_energy", 100))
            energy_pct = max(0.0, min(1.0, energy / max_energy)) if max_energy > 0 else 0
            
            e_icon = "🔋" if energy > 50 else "🪫"
            if energy < 20: e_icon = "💤"
            
            st.markdown(f"<div class='stat-label'>Physical Energy {e_icon}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value'>{energy:.1f}</div>", unsafe_allow_html=True)
            st.progress(energy_pct)
            
            # 显示恢复/消耗速率
            drain = psyche_cfg.get("energy_drain_rate", 0)
            recover = psyche_cfg.get("energy_recover_rate", 0)
            st.caption(f"Drain: -{drain}/h | Sleep: +{recover}/h")

        # --- B. Social Battery (社交电量) ---
        with p2:
            social = float(psyche.get("social_battery", 100))
            max_social = float(psyche_cfg.get("max_social_battery", 100))
            social_pct = max(0.0, min(1.0, social / max_social)) if max_social > 0 else 0
            
            s_icon = "💬" if social > 30 else "😶"
            
            st.markdown(f"<div class='stat-label'>Social Battery {s_icon}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value'>{social:.1f}</div>", unsafe_allow_html=True)
            st.progress(social_pct)
            
            st.caption(f"Cost (Passive): -{psyche_cfg.get('cost_speak_passive', 0)}/msg")

        # --- C. Boredom (表达欲) ---
        with p3:
            boredom = float(psyche.get("boredom", 0))
            threshold = float(psyche_cfg.get("boredom_threshold", 80))
            
            # 计算无聊进度
            boredom_pct = max(0.0, min(1.0, boredom / threshold)) if threshold > 0 else 0
            
            b_icon = "🥱"
            b_val_color = "inherit"
            if boredom >= threshold:
                b_icon = "📢" # 触发阈值
                b_val_color = "#dc3545" # 变红
            
            st.markdown(f"<div class='stat-label'>Boredom / Drive {b_icon}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value' style='color:{b_val_color}'>{boredom:.1f} <span style='font-size:1rem;color:#999'>/ {threshold}</span></div>", unsafe_allow_html=True)
            st.progress(boredom_pct)
            
            growth = psyche_cfg.get("base_boredom_growth", 0)
            st.caption(f"Growth: +{growth}/h")

        # --- D. [展示 2] Psyche Mood (内在基调 - Numeric/String) ---
        with p4:
            # 获取 Psyche Mood
            psyche_mood = psyche.get("mood", "Stable") 
            
            # 渲染一个卡片或者大字显示
            st.markdown(f"<div class='stat-label'>Internal Psyche Mood 🧠</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='stat-value' style='color:#4e8cff'>{psyche_mood}</div>", unsafe_allow_html=True)
            st.caption("Base emotional substrate")

        # --- E. 配置详情 (折叠) ---
        with st.expander("🧬 View Psyche DNA Configuration", expanded=False):
            if psyche_cfg:
                c_df = pd.DataFrame([{"Parameter": k, "Value": v} for k, v in psyche_cfg.items()])
                st.dataframe(c_df, width='stretch', hide_index=True)
            else:
                st.info("No configuration data received.")
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

        # --- Tab 2: Memory & Session (已适配架构重构) ---
        with tab_memory:
            # === 变更点：分别获取独立的 Session 和 L2 Memory 数据 ===
            sess = state.get("session", {})      # 现在 Session 是顶级对象
            l2 = state.get("l2_memory", {})      # L2 Memory 只负责向量库信息
            
            # 1. 会话状态指标 (Session Metrics)
            m1, m2, m3, m4 = st.columns(4)
            
            # 获取基础信息
            role = sess.get("role", "AI")
            user = sess.get("user_name", "User")
            m1.metric("Session Role", role)
            m2.metric("User Name", user)
            
            # Context Window 进度条
            curr_msg = sess.get("total_messages", 0)
            max_msg = sess.get("max_messages_limit", 20)
            # 防止除零错误
            progress = 0.0
            if max_msg > 0:
                progress = min(curr_msg / max_msg, 1.0)
            
            m3.metric("Context Window", f"{curr_msg} / {max_msg}")
            m3.progress(progress)
            
            # 时间戳
            last_ts = sess.get("last_interaction_time", 0)
            # 简单的格式化函数，如果之前未定义，可以使用 datetime.fromtimestamp
            ts_str = "Never"
            if last_ts > 0:
                ts_str = datetime.fromtimestamp(last_ts).strftime("%H:%M:%S")
            m4.metric("Last Interaction", ts_str)
            
            st.divider()
            
            # 2. 聊天记录可视化 (Chat History)
            st.subheader("💬 Active Context (Session Buffer)")
            
            # 获取最近的消息列表
            # 注意：确保你的 SessionState.get_status 返回了 "last_few_messages"
            recent_msgs = sess.get("last_few_messages", [])
            
            if recent_msgs:
                chat_container = st.container(height=400) # 固定高度滚动容器
                with chat_container:
                    for msg in recent_msgs:
                        role_tag = msg.get("role", "user")
                        content = msg.get("content", "")
                        
                        # 设置头像
                        avatar = "👤" if role_tag == "user" else "🤖"
                        
                        # 渲染气泡
                        with st.chat_message(name=role_tag, avatar=avatar):
                            st.markdown(content)
                            # 如果有时间戳也可以显示
                            # st.caption(format_timestamp(msg.get("client_timestamp")))
            else:
                st.info("No active conversation in RAM.")

            st.divider()
            
            # 3. 向量数据库信息 (L2 Vector DB)
            # 这部分信息依然保留在 l2_memory 中
            st.subheader("📚 Long-term Memory (Vector DB)")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Micro Collection:** `{l2.get('micro_memory_collection', 'N/A')}`")
            with c2:
                st.markdown(f"**Macro Collection:** `{l2.get('macro_memory_collection', 'N/A')}`")
            
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
                    st.dataframe(clean_micro, width='stretch', hide_index=True)
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