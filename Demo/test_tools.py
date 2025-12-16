from L1 import ChatMessage
from Reflector import ConversationSegment

def conversation_split(conversations: list[ChatMessage])->list[ConversationSegment]:
        """将对话按时间来进行切割"""
        if len(conversations) == 0:
            return []
             
        segments: list[ConversationSegment] = []
        gap_seconds = 1800.0
        
        # 目前采用简单粗暴的按时间间隔来分
        # TODO 后续考虑更新划分算法
        
        current: list[ChatMessage] = [conversations[0]]
        
        for prev, curr in zip(conversations, conversations[1:]):
            if curr.timestamp - prev.timestamp > gap_seconds:
                segments.append(ConversationSegment(current[0].timestamp, current[-1].timestamp, current.copy()))
                current.clear()
            current.append(curr)
            
        segments.append(ConversationSegment(current[0].timestamp, current[-1].timestamp, current.copy()))
        return segments
    
    
    
def test():
    from test_dataset import test_data_conversations_multi_theme_with_designed_timestamp
    results = conversation_split(test_data_conversations_multi_theme_with_designed_timestamp)
    for res in results:
        res.debug()


if __name__ == "__main__":
    test()
    
    
    