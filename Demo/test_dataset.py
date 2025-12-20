from Demo.Session import ChatMessage

#  ========================================================================================================================================================================
#  测试数据集
#  Reflector L1 to L2
#  ========================================================================================================================================================================

conversations_01 = [

    # ===== 第 1 组：上午，初始疲惫 =====
    ChatMessage(role="妖梦", content="今天一整天都感觉很累。", timestamp=1765876408.223395),
    ChatMessage(role="Elysia", content="听起来今天对你来说消耗挺大的。", timestamp=1765876462.431210),
    ChatMessage(role="妖梦", content="也说不上来为什么，就是没什么精神。", timestamp=1765876520.118902),
    ChatMessage(role="Elysia", content="有时候疲惫并不一定马上能找到原因。", timestamp=1765876588.774321),
    ChatMessage(role="妖梦", content="可能是昨晚没睡好。", timestamp=1765876645.092114),
    ChatMessage(role="Elysia", content="睡眠质量确实会直接影响第二天的状态。", timestamp=1765876701.556732),
    ChatMessage(role="妖梦", content="最近好像经常这样。", timestamp=1765876760.332901),

    # ===== 第 2 组：傍晚，工作与焦虑（+6h） =====
    ChatMessage(role="Elysia", content="你现在是在下班之后吗？", timestamp=1765899005.119832),
    ChatMessage(role="妖梦", content="嗯，刚到家。", timestamp=1765899061.884220),
    ChatMessage(role="Elysia", content="一天结束的时候，疲惫感有时会更明显。", timestamp=1765899120.437611),
    ChatMessage(role="妖梦", content="对，而且事情还有一堆没做完。", timestamp=1765899188.221094),
    ChatMessage(role="Elysia", content="事情堆着的时候，很容易让人更焦虑。", timestamp=1765899254.673902),
    ChatMessage(role="妖梦", content="我会开始怀疑自己效率是不是太低了。", timestamp=1765899312.558731),
    ChatMessage(role="Elysia", content="在压力下这样想，其实挺常见的。", timestamp=1765899376.004129),

    # ===== 第 3 组：深夜，反思与自我怀疑（+6h） =====
    ChatMessage(role="妖梦", content="现在躺在床上，但一点也不困。", timestamp=1765921702.781442),
    ChatMessage(role="Elysia", content="身体累了，但大脑还停不下来，是吗？", timestamp=1765921760.443810),
    ChatMessage(role="妖梦", content="对，一直在想白天的事情。", timestamp=1765921821.116004),
    ChatMessage(role="Elysia", content="那些没做完的事，好像一直在脑子里转。", timestamp=1765921884.903721),
    ChatMessage(role="妖梦", content="而且会想到以前，觉得自己退步了。", timestamp=1765921946.557993),
    ChatMessage(role="Elysia", content="你在把现在的自己和过去的状态做比较。", timestamp=1765922008.220774),
    ChatMessage(role="妖梦", content="是的，这让我有点难受。", timestamp=1765922069.889312),

    # ===== 第 4 组：第二天上午，情绪延续（+6h） =====
    ChatMessage(role="Elysia", content="你后来有睡着吗？", timestamp=1765944401.774550),
    ChatMessage(role="妖梦", content="睡了一点，但不太踏实。", timestamp=1765944459.332801),
    ChatMessage(role="Elysia", content="那种半睡半醒的感觉，很消耗精力。", timestamp=1765944520.119304),
    ChatMessage(role="妖梦", content="醒来后情绪也不太好。", timestamp=1765944584.665882),
    ChatMessage(role="Elysia", content="看来昨晚的状态延续到了今天。", timestamp=1765944649.003774),
    ChatMessage(role="妖梦", content="对，我开始担心这种情况会不会一直持续。", timestamp=1765944710.887430),

    # ===== 第 5 组：夜晚，轻微缓解与总结（+6h） =====
    ChatMessage(role="Elysia", content="现在这个时间，你在做什么？", timestamp=1765967008.551902),
    ChatMessage(role="妖梦", content="刚洗完澡，准备休息了。", timestamp=1765967062.339118),
    ChatMessage(role="Elysia", content="相比昨天，这一刻的感觉有变化吗？", timestamp=1765967121.994550),
    ChatMessage(role="妖梦", content="好像稍微放松了一点。", timestamp=1765967180.773221),
    ChatMessage(role="Elysia", content="哪怕只是一点变化，也很重要。", timestamp=1765967242.118903),
    ChatMessage(role="妖梦", content="至少不像昨天那么乱了。", timestamp=1765967301.662330),
    ChatMessage(role="Elysia", content="你已经走过了一段不容易的过程。", timestamp=1765967365.994881),
]


conversations_02  = [

    # ===== 第 1 组：身体疲惫 / 作息 =====
    ChatMessage(role="妖梦", content="今天醒来就觉得特别累。", timestamp=1765876408.223395),
    ChatMessage(role="Elysia", content="这种从一开始就疲惫的感觉挺难受的。", timestamp=1765876462.118903),
    ChatMessage(role="妖梦", content="明明睡了七个多小时。", timestamp=1765876519.332801),
    ChatMessage(role="Elysia", content="有时候睡眠时长够了，质量也未必好。", timestamp=1765876581.774550),
    ChatMessage(role="妖梦", content="最近好像经常做梦。", timestamp=1765876644.665882),
    ChatMessage(role="Elysia", content="频繁做梦确实容易让人醒来更累。", timestamp=1765876706.003774),
    ChatMessage(role="妖梦", content="难怪白天一直提不起精神。", timestamp=1765876761.889312),

    # ===== 第 2 组：工作任务 / 项目压力（+6h） =====
    ChatMessage(role="Elysia", content="你现在是在忙工作吗？", timestamp=1765899008.551902),
    ChatMessage(role="妖梦", content="是的，项目进度有点赶。", timestamp=1765899062.339118),
    ChatMessage(role="Elysia", content="听起来时间压力不小。", timestamp=1765899121.994550),
    ChatMessage(role="妖梦", content="需求还一直在改。", timestamp=1765899180.773221),
    ChatMessage(role="Elysia", content="频繁变动会让人很难安心推进。", timestamp=1765899242.118903),
    ChatMessage(role="妖梦", content="我甚至有点不想看消息。", timestamp=1765899301.662330),
    ChatMessage(role="Elysia", content="那种逃避的冲动，在高压下很常见。", timestamp=1765899365.994881),

    # ===== 第 3 组：人际关系 / 社交困扰（+6h） =====
    ChatMessage(role="妖梦", content="刚和朋友聊天，有点不太开心。", timestamp=1765921702.781442),
    ChatMessage(role="Elysia", content="发生什么了吗？", timestamp=1765921760.443810),
    ChatMessage(role="妖梦", content="感觉我们说话越来越不在一个频道。", timestamp=1765921821.116004),
    ChatMessage(role="Elysia", content="那种渐渐疏远的感觉挺微妙的。", timestamp=1765921884.903721),
    ChatMessage(role="妖梦", content="也不是吵架，就是有点失落。", timestamp=1765921946.557993),
    ChatMessage(role="Elysia", content="失落本身就很真实，不一定非要有冲突。", timestamp=1765922008.220774),
    ChatMessage(role="妖梦", content="我不知道是不是我想太多了。", timestamp=1765922069.889312),

    # ===== 第 4 组：日常琐事 / 消费体验（+6h） =====
    ChatMessage(role="Elysia", content="你现在在做什么？", timestamp=1765944401.774550),
    ChatMessage(role="妖梦", content="刚点了外卖，但送得特别慢。", timestamp=1765944459.332801),
    ChatMessage(role="Elysia", content="饿着等外卖确实很折磨。", timestamp=1765944520.119304),
    ChatMessage(role="妖梦", content="而且客服回复也很敷衍。", timestamp=1765944584.665882),
    ChatMessage(role="Elysia", content="这种体验很容易让人更烦躁。", timestamp=1765944649.003774),
    ChatMessage(role="妖梦", content="现在只想快点吃到东西。", timestamp=1765944710.887430),
    ChatMessage(role="Elysia", content="希望能尽快送到，至少解决一件事。", timestamp=1765944768.552109),

    # ===== 第 5 组：学习 / 长期规划（+6h） =====
    ChatMessage(role="Elysia", content="今天整体结束得怎么样？", timestamp=1765967008.551902),
    ChatMessage(role="妖梦", content="晚上在想要不要学点新东西。", timestamp=1765967062.339118),
    ChatMessage(role="Elysia", content="你是在考虑长期的方向吗？", timestamp=1765967121.994550),
    ChatMessage(role="妖梦", content="是的，但有点怕自己坚持不下来。", timestamp=1765967180.773221),
    ChatMessage(role="Elysia", content="这种担心在开始之前很常见。", timestamp=1765967242.118903),
    ChatMessage(role="妖梦", content="我好像总是计划很多，做得很少。", timestamp=1765967301.662330),
    ChatMessage(role="Elysia", content="你已经在认真观察自己的状态了。", timestamp=1765967365.994881),
]

conversations_03 = [

    # ===== 第 1 组：通勤 / 出行体验 =====
    ChatMessage(role="妖梦", content="今天早上通勤特别不顺。", timestamp=1766011204.118903),
    ChatMessage(role="Elysia", content="发生什么事了吗？", timestamp=1766011258.774550),
    ChatMessage(role="妖梦", content="地铁临时晚点了。", timestamp=1766011316.332801),
    ChatMessage(role="Elysia", content="早高峰遇到这种情况确实很影响心情。", timestamp=1766011379.665882),
    ChatMessage(role="妖梦", content="后面整个人就开始有点急躁。", timestamp=1766011442.003774),
    ChatMessage(role="Elysia", content="那种被打乱节奏的感觉，很容易让人烦。", timestamp=1766011501.889312),

    # ===== 第 2 组：家庭事务 / 生活安排（+6h） =====
    ChatMessage(role="Elysia", content="现在是在忙家里的事情吗？", timestamp=1766033608.551902),
    ChatMessage(role="妖梦", content="是的，在和家里人讨论周末安排。", timestamp=1766033662.339118),
    ChatMessage(role="Elysia", content="听起来需要协调不少事情。", timestamp=1766033721.994550),
    ChatMessage(role="妖梦", content="每个人想法都不太一样。", timestamp=1766033780.773221),
    ChatMessage(role="Elysia", content="这种时候确实很难让所有人都满意。", timestamp=1766033842.118903),
    ChatMessage(role="妖梦", content="最后反而有点不想说话了。", timestamp=1766033901.662330),

    # ===== 第 3 组：健康管理 / 生活习惯（+6h） =====
    ChatMessage(role="妖梦", content="我最近在想要不要开始运动。", timestamp=1766056102.781442),
    ChatMessage(role="Elysia", content="你是出于什么原因开始考虑这个？", timestamp=1766056160.443810),
    ChatMessage(role="妖梦", content="感觉身体状态不如以前了。", timestamp=1766056221.116004),
    ChatMessage(role="Elysia", content="这种察觉本身就很重要。", timestamp=1766056284.903721),
    ChatMessage(role="妖梦", content="但一想到坚持就有点打退堂鼓。", timestamp=1766056346.557993),
    ChatMessage(role="Elysia", content="很多人都会卡在这一步。", timestamp=1766056408.220774),

    # ===== 第 4 组：数码设备 / 技术使用（+6h） =====
    ChatMessage(role="Elysia", content="你现在是在用电脑还是手机？", timestamp=1766078501.774550),
    ChatMessage(role="妖梦", content="在折腾电脑，系统更新后有点卡。", timestamp=1766078559.332801),
    ChatMessage(role="Elysia", content="更新之后出现性能问题确实让人头疼。", timestamp=1766078620.119304),
    ChatMessage(role="妖梦", content="而且设置还变了。", timestamp=1766078684.665882),
    ChatMessage(role="Elysia", content="需要重新适应新的操作方式。", timestamp=1766078749.003774),
    ChatMessage(role="妖梦", content="感觉效率一下子掉了很多。", timestamp=1766078810.887430),

    # ===== 第 5 组：情绪回顾 / 自我观察（+6h） =====
    ChatMessage(role="Elysia", content="一天快结束了，你现在的状态怎么样？", timestamp=1766100908.551902),
    ChatMessage(role="妖梦", content="比白天平静一些。", timestamp=1766100962.339118),
    ChatMessage(role="Elysia", content="这一天情绪变化还挺多的。", timestamp=1766101021.994550),
    ChatMessage(role="妖梦", content="是的，但现在回头看，好像都还能接受。", timestamp=1766101080.773221),
    ChatMessage(role="Elysia", content="你在试着整体看待这一天。", timestamp=1766101142.118903),
    ChatMessage(role="妖梦", content="至少没有一开始那么烦了。", timestamp=1766101201.662330),
]


embedded_abstract_memories =[{'content': '我注意到他今天醒来就感到异常疲惫，即使睡眠时间足够，但频繁的梦境影响了休息质量。', 'type': 'Experience', 'poignancy': 5, 'keywords': ['疲惫', '睡眠质量', '梦境'], 'timestamp': 1765876408.223395}, 
                             {'content': '他最近白天总是提不起精神，这似乎与睡眠质量不佳有关。', 'type': 'Experience', 'poignancy': 4, 'keywords': ['精神不振', '白天状态'], 'timestamp': 1765876409.223395},
                            {'content': '他正在赶一个项目，进度很紧张，而且需求还在不断变动，这让他感到压力很大，甚至产生了不想看消息的逃避冲动。', 'type': 'Experience', 'poignancy': 7, 'keywords': ['工作压力', '项目进度', '需求变动', '逃避冲动'], 'timestamp': 1765899010.551902},
                            {'content': '我察觉到妖梦因为和朋友聊天而感到不开心，他提到彼此说话越来越不在一个频道，我能感受到他那种微妙的失落感。', 'type': 'Experience', 'poignancy': 6, 'keywords': ['朋友', '失落', '疏远'], 'timestamp': 1765921702.781442}, 
                            {'content': '妖梦向我倾诉了内心的困惑，他不确定是不是自己想太多，这让我觉得他正在经历一段情感上的迷茫期。', 'type': 'Experience', 'poignancy': 5, 'keywords': ['困惑', '迷茫', '倾诉'], 'timestamp': 1765921706.781442},
                            {'content': '我看到妖梦因为外卖送得慢而感到烦躁，客服的敷衍回复更是加剧了他的不满。', 'type': 'Experience', 'poignancy': 4, 'keywords': ['外卖', '烦躁', '客服'], 'timestamp': 1765944401.77455},
                            {'content': '我注意到他正在考虑学习新东西，但担心自己无法坚持，这让我感受到他内心的犹豫和对自我要求的压力。', 'type': 'Experience', 'poignancy': 5, 'keywords': ['学习', '犹豫', '自我要求'], 'timestamp': 1765967008.551902}, 
                            {'content': '他坦诚自己经常计划很多但行动很少，这让我看到了他自我反思的一面，也让我想鼓励他迈出第一步。', 'type': 'Opinion', 'poignancy': 6, 'keywords': ['计划', '行动', '自我反思'], 'timestamp': 1765967012.551902}
]