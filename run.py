
import fire
import pyaudio
import queue
from streaming_tts.xunfei_tts_api import XunFeiTTSClient
import builder 
from llm_agent.fix_agent import TextFixAgent
from streaming_asr_client.paddlespeech_asr import PaddleASRClient
from logger import logger
# import openai_gpt
p = pyaudio.PyAudio()

def display_device():
    device_count = p.get_device_count()
    logger.info(f"Device count: {device_count}")
    for i in range(device_count):
        device_info = p.get_device_info_by_index(i)
        print(device_info)

display_device()

# 获取设备数量
def getBlackHoleIndex(name = 'BlackHole 2ch'):
    device_count = p.get_device_count()
    for i in range(device_count):
        device_info = p.get_device_info_by_index(i)
        logger.info(device_info)
        if device_info['name'] == name:
            return device_info['index']
    raise "device name not found"

def get_output_stream(device_name, sample_rate = 16000, channels = 1):
    input_device_index = getBlackHoleIndex(device_name)
    stream = p.open(format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                output=True,
                output_device_index=input_device_index,
                frames_per_buffer=32)
    return stream

def get_input_stream(device_name = None, sample_rate = 16000, channels = 1):
    if device_name is not None:
        input_device_index = getBlackHoleIndex(device_name)
        stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    input_device_index=input_device_index,
                    frames_per_buffer=32)
    else:
        stream = p.open(format=pyaudio.paInt16,
                        channels=channels,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=32)
    return stream

class Runner():
    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.rt_asr_client = PaddleASRClient(audio_input_queue=self.audio_queue, text_output_queue=self.text_queue, **cfg.paddle_asr_client_cfg)
        if cfg.use_gpt:
            fixed_text_queue =  queue.Queue()
            self.text_fix_client = TextFixAgent(self.text_queue, fixed_text_queue, cfg)
            self.text_queue = fixed_text_queue
        
        self.tts_client = XunFeiTTSClient(get_output_stream(cfg.out_device_name), text_queue=self.text_queue, audio_queue=self.audio_queue, **cfg.xunfei_tts_cfg)
    
    def loop(self):
        self.rt_asr_client.loop()
        if self.cfg.use_gpt:
            self.text_fix_client.loop()
        self.tts_client.loop()
        stream = get_input_stream(cfg.input_device_name)
        while True:
            data = stream.read(64)
            self.audio_queue.put(data)

def run(cfg):
    runner = Runner(cfg)
    runner.loop()

if __name__=='__main__':
    from configs import config as cfg
    run(cfg)
