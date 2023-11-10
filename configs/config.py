from llm_agent.fix_agent import GPTProxy
use_gpt = True

llms = [
    dict(
        cls = GPTProxy,
        kwargs=dict(
            api_key = "",
        )
    )
]

# out_device_name = 'BlackHole 2ch'
out_device_name = '外置耳机'
input_device_name = None

# temp secret key
xunfei_tts_cfg = dict(APPID='62eaac86', APISecret='', APIKey='')

# xunfei_asr_cfg = dict(app_id = "62eaac86", api_key = "4e0b3e87f8c6348f58fee0d9ce8a1d88")
paddle_asr_client_cfg = dict(   url="127.0.0.1",
                                port=8090,
                                endpoint="/paddlespeech/asr/streaming",
                                punc_server_ip = "127.0.0.1", 
                                punc_server_port = 8190)