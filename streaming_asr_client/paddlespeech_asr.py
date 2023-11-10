from streaming_asr_client.asr_proxy import AsrProxyBase
import threading
from websocket import create_connection
import logging
from logger import logger
from paddlespeech.server.utils.audio_handler import TextHttpHandler
import time
import json


class PaddleASRClient(AsrProxyBase):
    def __init__(self,
                 audio_input_queue, 
                 text_output_queue,
                 url=None,
                 port=None,
                 endpoint="/paddlespeech/asr/streaming",
                 punc_server_ip = None, 
                 punc_server_port = None) -> None:
        super(PaddleASRClient, self).__init__(audio_input_queue, text_output_queue)
        self.buffer_text = ""
        self.pre_index = 0
        self.url = url
        self.port = port
        self.prev_send_timestamp = time.time()
        self.max_buffer_length = 64
        self.max_waiting_time = 3
        self.max_gap_time = 1
        self.old_text = "_"
        if url is None or port is None or endpoint is None:
            self.url = None
        else:
            self.url = "ws://" + self.url + ":" + str(self.port) + endpoint
        self.punc_server = TextHttpHandler(punc_server_ip, punc_server_port)
        logger.info(f"paddle speech endpoint: {self.url}")
        
    def loop(self):
        def run():
            logging.debug("send a message to the server")
            if self.url is None:
                logger.error("No asr server, please input valid ip and port")
                return ""
            # async with websockets.connect(self.url) as ws:
            ws = create_connection(self.url)
            audio_info = json.dumps(
                {
                    "name": "test.wav",
                    "signal": "start",
                    "nbest": 1
                },
                sort_keys=True,
                indent=4,
                separators=(',', ': '))
            ws.send(audio_info)
            msg = ws.recv()
            logger.info("client receive msg={}".format(msg))
            while True:
                chunk_data = self.audio_input_queue.get()
                ws.send(chunk_data)
                msg =  ws.recv()
                msg = json.loads(msg)
                self.process(msg)
        self.th = threading.Thread(target = run, args=())
        self.th.start()
    
    def process(self, msg):
        text = msg['result']
        if text == "":
            self.pre_index = 0
            return
        
        self.buffer_text += text[self.pre_index:]
        self.pre_index = len(text)
    
        sep_text = self.punc_server.run(self.buffer_text)
        
        idx = sep_text.find("。")
        if idx == -1:
            idx = sep_text.find("；")
        if idx == -1 and len(self.buffer_text) > self.max_buffer_length:
            idx = len(self.max_buffer_length)
        if idx != -1:
            text = self.buffer_text[:idx]
            logger.info(f"ASR text: {text}")
            self.text_output_queue.put(text)
            self.buffer_text = self.buffer_text[idx:]
            
    def reset_buffer(self):
        self.buffer_text = ""