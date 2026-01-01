import jinja2
import time

# ==========================================
# 1. 修正后的模板
# ==========================================
template_string = """
{# --- 宏定义 --- #}
{%- macro L2MemoryBlockPrompt(memory_ctx) -%}
<micro memory>
{%- if memory_ctx.micro %}
    {%- for mem in memory_ctx.micro %}

    - {{ mem.timestamp }} (Poignancy: {{ mem.poignancy }}) {{ mem.content }}
    {%- endfor %}
{%- else %}

    (No micro memories)
{%- endif %}
</micro memory>

<macro memory>
{%- if memory_ctx.macro %}
    {%- for mem in memory_ctx.macro %}

    - {{ mem.timestamp }} (Poignancy: {{ mem.poignancy }}){% if mem.dominant_emotion %} (Dominant Emotion: {{ mem.dominant_emotion }}){% endif %} {{ mem.content }}
    {%- endfor %}
{%- else %}

    (No macro memories)
{%- endif %}
</macro memory>
{#- 核心修复 2: 在宏结束前，强制加一个空行，防止和外部的 closing tag 粘连 -#}

{%- endmacro -%}

{# --- 调用部分 --- #}
<memory_bank>
{{ L2MemoryBlockPrompt(ctx) }}
</memory_bank>
"""

# ==========================================
# 2. 模拟数据 (保持不变)
# ==========================================
mock_data = {
    "micro": [
        {
            "content": "妖梦说遇见我是他一生中最大的幸运...",
            "subject": "Interaction",
            "memory_type": "conversation",
            "poignancy": 10,
            "timestamp": 1766868761
        },
        {
            "content": "我注意到妖梦总是能非常自然地说出...",
            "subject": "Observation",
            "memory_type": "observation",
            "poignancy": 8,
            "timestamp": 1767115509
        }
    ],
    "macro": [
        {
            "content": "Interaction with User",
            "subject": "Emotion",
            "memory_type": "summary",
            "poignancy": 88,
            "dominant_emotion": "幸福",
            "timestamp": 1766952991
        }
    ]
}

# ==========================================
# 3. 运行测试
# ==========================================
def test_template():
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    template = env.from_string(template_string)
    print(template.render(ctx=mock_data))

if __name__ == "__main__":
    test_template()