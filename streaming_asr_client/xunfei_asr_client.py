# -*- encoding:utf-8 -*-
import hashlib
import hmac
import base64
from socket import *
import json, time, threading
from websocket import create_connection
import websocket
from urllib.parse import quote
import logging
import pyaudio
p = pyaudio.PyAudio()
def getBlackHoleIndex(name = 'BlackHole 2ch'):
    device_count = p.get_device_count()
    for i in range(device_count):
        device_info = p.get_device_info_by_index(i)
        if device_info['name'] == name:
            return device_info['index']
    return 3

class Client():
    def __init__(   self, 
                    text_queue,   
                    app_id = None,
                    api_key = None):
        base_url = "ws://rtasr.xfyun.cn/v1/ws"
        ts = str(int(time.time()))
        tt = (app_id + ts).encode('utf-8')
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding='utf-8')
        self.text_queue = text_queue
        apiKey = api_key.encode('utf-8')
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        self.end_tag = "{\"end\": true}"

        self.ws = create_connection(base_url + "?appid=" + app_id + "&lang=cn&transType=normal&transStrategy=2&targetLang=en&pd=tech"+ "&ts=" + ts + "&signa=" + quote(signa))
        self.trecv = threading.Thread(target=self.recv)
        self.trecv.start()

    def start_listen(self):
        def run():
            frameSize = 1280 
            stream = p.open(format=pyaudio.paInt16,
                                    channels=1,
                                    rate=16000,
                                    input=True,
                                    input_device_index=getBlackHoleIndex("MacBook Pro麦克风"),
                                    frames_per_buffer=frameSize)
            index = 1
            while True:
                chunk = stream.read(frameSize)
                if not chunk:
                    break
                self.ws.send(chunk)
                index += 1
            self.ws.send(bytes(self.end_tag.encode('utf-8')))
        self.th = threading.Thread(target=run,args=())
        self.th.start()

    def recv(self):
        try:
            ss = ""
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    print("receive result end")
                    break
                result_dict = json.loads(result)
                # 解析结果
                if result_dict["action"] == "started":
                    print("handshake success, result: " + result)

                if result_dict["action"] == "result":
                    result_1 = result_dict
                    result_2 = json.loads(result_1["data"])
                    if 'biz' in result_2 and result_2['type'] == 0:
                        dst = result_2['dst']
                        src = result_2['src']
                        if len(dst) > 1 and dst[0] in ["?", ".", ",", "!"]:
                            dst = dst[1:]
                        if len(src) > 1 and src[0] in ["？", "。", "，", "！"]:
                            src = src[1:]
                        # print("put text to queue")
                        if self.text_queue is not None:
                            self.text_queue.put((dst, src))
                        else:
                            print(dst)

                if result_dict["action"] == "error":
                    print("rtasr error: " + result)
                    self.ws.close()
                    return
        except websocket.WebSocketConnectionClosedException:
            print("receive result end")

    def close(self):
        self.ws.close()
        print("connection closed")


if __name__ == '__main__':
    logging.basicConfig()
    client = Client(None)
    client.start_listen()
