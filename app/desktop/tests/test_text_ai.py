from sweety_app.ai import build_messages


def test_text_prompt_preserves_order_roles_and_quote_separation():
    incoming=[{'id':'m1','text':'你好','relatedMessageId':'old'}, {'id':'m2','text':'下一句'}]
    messages=build_messages(system_prompt_template='人設：{persona_text}，數量：{total_messages}',
        persona_text='慢熟',incoming_messages=incoming,history=[{'role':'assistant','content':'old reply'}],total_messages=4)
    assert isinstance(messages[-1]['content'],str)
    assert '你好' in messages[-1]['content'] and messages[-1]['content'].index('你好')<messages[-1]['content'].index('下一句')
    assert 'relatedMessageId' in messages[-1]['content']
    assert messages[-2]=={'role':'assistant','content':'old reply'}
    assert '慢熟' not in messages[0]['content']
    assert '不得提供任何網址' in messages[0]['content']
    assert '綠色' not in messages[0]['content'] and 'image_url' not in str(messages)
