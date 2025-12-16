from L1 import ChatMessage

test_data_conversations_single_theme_with_designed_timestamp = [

    # ===== 第 1 组：上午，初始疲惫 =====
    ChatMessage(role="user", content="今天一整天都感觉很累。", timestamp=1765876408.223395),
    ChatMessage(role="assistant", content="听起来今天对你来说消耗挺大的。", timestamp=1765876462.431210),
    ChatMessage(role="user", content="也说不上来为什么，就是没什么精神。", timestamp=1765876520.118902),
    ChatMessage(role="assistant", content="有时候疲惫并不一定马上能找到原因。", timestamp=1765876588.774321),
    ChatMessage(role="user", content="可能是昨晚没睡好。", timestamp=1765876645.092114),
    ChatMessage(role="assistant", content="睡眠质量确实会直接影响第二天的状态。", timestamp=1765876701.556732),
    ChatMessage(role="user", content="最近好像经常这样。", timestamp=1765876760.332901),

    # ===== 第 2 组：傍晚，工作与焦虑（+6h） =====
    ChatMessage(role="assistant", content="你现在是在下班之后吗？", timestamp=1765899005.119832),
    ChatMessage(role="user", content="嗯，刚到家。", timestamp=1765899061.884220),
    ChatMessage(role="assistant", content="一天结束的时候，疲惫感有时会更明显。", timestamp=1765899120.437611),
    ChatMessage(role="user", content="对，而且事情还有一堆没做完。", timestamp=1765899188.221094),
    ChatMessage(role="assistant", content="事情堆着的时候，很容易让人更焦虑。", timestamp=1765899254.673902),
    ChatMessage(role="user", content="我会开始怀疑自己效率是不是太低了。", timestamp=1765899312.558731),
    ChatMessage(role="assistant", content="在压力下这样想，其实挺常见的。", timestamp=1765899376.004129),

    # ===== 第 3 组：深夜，反思与自我怀疑（+6h） =====
    ChatMessage(role="user", content="现在躺在床上，但一点也不困。", timestamp=1765921702.781442),
    ChatMessage(role="assistant", content="身体累了，但大脑还停不下来，是吗？", timestamp=1765921760.443810),
    ChatMessage(role="user", content="对，一直在想白天的事情。", timestamp=1765921821.116004),
    ChatMessage(role="assistant", content="那些没做完的事，好像一直在脑子里转。", timestamp=1765921884.903721),
    ChatMessage(role="user", content="而且会想到以前，觉得自己退步了。", timestamp=1765921946.557993),
    ChatMessage(role="assistant", content="你在把现在的自己和过去的状态做比较。", timestamp=1765922008.220774),
    ChatMessage(role="user", content="是的，这让我有点难受。", timestamp=1765922069.889312),

    # ===== 第 4 组：第二天上午，情绪延续（+6h） =====
    ChatMessage(role="assistant", content="你后来有睡着吗？", timestamp=1765944401.774550),
    ChatMessage(role="user", content="睡了一点，但不太踏实。", timestamp=1765944459.332801),
    ChatMessage(role="assistant", content="那种半睡半醒的感觉，很消耗精力。", timestamp=1765944520.119304),
    ChatMessage(role="user", content="醒来后情绪也不太好。", timestamp=1765944584.665882),
    ChatMessage(role="assistant", content="看来昨晚的状态延续到了今天。", timestamp=1765944649.003774),
    ChatMessage(role="user", content="对，我开始担心这种情况会不会一直持续。", timestamp=1765944710.887430),

    # ===== 第 5 组：夜晚，轻微缓解与总结（+6h） =====
    ChatMessage(role="assistant", content="现在这个时间，你在做什么？", timestamp=1765967008.551902),
    ChatMessage(role="user", content="刚洗完澡，准备休息了。", timestamp=1765967062.339118),
    ChatMessage(role="assistant", content="相比昨天，这一刻的感觉有变化吗？", timestamp=1765967121.994550),
    ChatMessage(role="user", content="好像稍微放松了一点。", timestamp=1765967180.773221),
    ChatMessage(role="assistant", content="哪怕只是一点变化，也很重要。", timestamp=1765967242.118903),
    ChatMessage(role="user", content="至少不像昨天那么乱了。", timestamp=1765967301.662330),
    ChatMessage(role="assistant", content="你已经走过了一段不容易的过程。", timestamp=1765967365.994881),
]


test_data_conversations_multi_theme_with_designed_timestamp  = [

    # ===== 第 1 组：身体疲惫 / 作息 =====
    ChatMessage(role="user", content="今天醒来就觉得特别累。", timestamp=1765876408.223395),
    ChatMessage(role="assistant", content="这种从一开始就疲惫的感觉挺难受的。", timestamp=1765876462.118903),
    ChatMessage(role="user", content="明明睡了七个多小时。", timestamp=1765876519.332801),
    ChatMessage(role="assistant", content="有时候睡眠时长够了，质量也未必好。", timestamp=1765876581.774550),
    ChatMessage(role="user", content="最近好像经常做梦。", timestamp=1765876644.665882),
    ChatMessage(role="assistant", content="频繁做梦确实容易让人醒来更累。", timestamp=1765876706.003774),
    ChatMessage(role="user", content="难怪白天一直提不起精神。", timestamp=1765876761.889312),

    # ===== 第 2 组：工作任务 / 项目压力（+6h） =====
    ChatMessage(role="assistant", content="你现在是在忙工作吗？", timestamp=1765899008.551902),
    ChatMessage(role="user", content="是的，项目进度有点赶。", timestamp=1765899062.339118),
    ChatMessage(role="assistant", content="听起来时间压力不小。", timestamp=1765899121.994550),
    ChatMessage(role="user", content="需求还一直在改。", timestamp=1765899180.773221),
    ChatMessage(role="assistant", content="频繁变动会让人很难安心推进。", timestamp=1765899242.118903),
    ChatMessage(role="user", content="我甚至有点不想看消息。", timestamp=1765899301.662330),
    ChatMessage(role="assistant", content="那种逃避的冲动，在高压下很常见。", timestamp=1765899365.994881),

    # ===== 第 3 组：人际关系 / 社交困扰（+6h） =====
    ChatMessage(role="user", content="刚和朋友聊天，有点不太开心。", timestamp=1765921702.781442),
    ChatMessage(role="assistant", content="发生什么了吗？", timestamp=1765921760.443810),
    ChatMessage(role="user", content="感觉我们说话越来越不在一个频道。", timestamp=1765921821.116004),
    ChatMessage(role="assistant", content="那种渐渐疏远的感觉挺微妙的。", timestamp=1765921884.903721),
    ChatMessage(role="user", content="也不是吵架，就是有点失落。", timestamp=1765921946.557993),
    ChatMessage(role="assistant", content="失落本身就很真实，不一定非要有冲突。", timestamp=1765922008.220774),
    ChatMessage(role="user", content="我不知道是不是我想太多了。", timestamp=1765922069.889312),

    # ===== 第 4 组：日常琐事 / 消费体验（+6h） =====
    ChatMessage(role="assistant", content="你现在在做什么？", timestamp=1765944401.774550),
    ChatMessage(role="user", content="刚点了外卖，但送得特别慢。", timestamp=1765944459.332801),
    ChatMessage(role="assistant", content="饿着等外卖确实很折磨。", timestamp=1765944520.119304),
    ChatMessage(role="user", content="而且客服回复也很敷衍。", timestamp=1765944584.665882),
    ChatMessage(role="assistant", content="这种体验很容易让人更烦躁。", timestamp=1765944649.003774),
    ChatMessage(role="user", content="现在只想快点吃到东西。", timestamp=1765944710.887430),
    ChatMessage(role="assistant", content="希望能尽快送到，至少解决一件事。", timestamp=1765944768.552109),

    # ===== 第 5 组：学习 / 长期规划（+6h） =====
    ChatMessage(role="assistant", content="今天整体结束得怎么样？", timestamp=1765967008.551902),
    ChatMessage(role="user", content="晚上在想要不要学点新东西。", timestamp=1765967062.339118),
    ChatMessage(role="assistant", content="你是在考虑长期的方向吗？", timestamp=1765967121.994550),
    ChatMessage(role="user", content="是的，但有点怕自己坚持不下来。", timestamp=1765967180.773221),
    ChatMessage(role="assistant", content="这种担心在开始之前很常见。", timestamp=1765967242.118903),
    ChatMessage(role="user", content="我好像总是计划很多，做得很少。", timestamp=1765967301.662330),
    ChatMessage(role="assistant", content="你已经在认真观察自己的状态了。", timestamp=1765967365.994881),
]



test_data_conversations_with_default_timestamp = [
        ChatMessage(role="user", content="今天一整天都感觉很累。"),
        ChatMessage(role="assistant", content="听起来今天对你来说消耗挺大的。"),
        ChatMessage(role="user", content="也说不上来为什么，就是提不起精神。"),
        ChatMessage(role="assistant", content="有时候疲惫并不一定有明确原因。"),
        ChatMessage(role="user", content="可能和昨晚没睡好有关系。"),
        ChatMessage(role="assistant", content="睡眠不好确实会影响第二天的状态。"),
        ChatMessage(role="user", content="我最近好像经常这样，睡得很浅。"),
        ChatMessage(role="assistant", content="这种情况持续一段时间的话，会让人更容易累。"),
        ChatMessage(role="user", content="是的，白天工作的时候注意力也很难集中。"),
        ChatMessage(role="assistant", content="注意力被影响，工作体验通常也会变差。"),
        ChatMessage(role="user", content="结果事情越拖越多，就更焦虑了。"),
        ChatMessage(role="assistant", content="听起来像是一个让人很难受的循环。"),
        ChatMessage(role="user", content="对，而且我还会开始怀疑自己是不是能力不行。"),
        ChatMessage(role="assistant", content="在状态不好的时候，人确实更容易否定自己。"),
        ChatMessage(role="user", content="明明以前不是这样的。"),
        ChatMessage(role="assistant", content="你注意到了自己和以前状态的差别。"),
        ChatMessage(role="user", content="是啊，这种变化让我有点不安。"),
        ChatMessage(role="assistant", content="这种不安本身也很真实，值得被认真对待。"),
        ChatMessage(role="user", content="但我又不知道该从哪里开始调整。"),
        ChatMessage(role="assistant", content="当事情看起来很乱的时候，不知道从哪开始是很常见的。"),
        ChatMessage(role="user", content="有时候甚至会想，算了，先放着吧。"),
        ChatMessage(role="assistant", content="那种想先逃开一下的感觉，我能理解。"),
        ChatMessage(role="user", content="不过放着又会更内疚。"),
        ChatMessage(role="assistant", content="一边想停下来，一边又责怪自己，这真的很折磨。"),
        ChatMessage(role="user", content="你这么说，我突然觉得好像有人懂我。"),
        ChatMessage(role="assistant", content="能让你有这种感觉，我很高兴。你不需要一个人扛着这些。"),
        ChatMessage(role="user", content="至少现在这样说出来，好像轻松了一点。"),
        ChatMessage(role="assistant", content="把这些说出来，本身就已经是一个不小的释放了。"),
]