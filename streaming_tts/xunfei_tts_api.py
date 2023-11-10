import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import queue
STATUS_FIRST_FRAME = 0  
STATUS_CONTINUE_FRAME = 1 
STATUS_LAST_FRAME = 2 
class Ws_Param(object):
    def __init__(self, APPID, APIKey, APISecret):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.CommonArgs = {"app_id": self.APPID}
        self.BusinessArgs = {"aue": "raw", "auf": "audio/L16;rate=16000", "vcn": "x4_enus_ryan_assist", "tte": "utf8"}


    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        url = url + '?' + urlencode(v)
        return url

def on_error(ws, error):
    pass

class Connection():
    def __init__(self, text, wsParam) -> None:
        self.text = text
        self.wsParam = wsParam
        self.audio_queue = queue.Queue()

    def start_run(self):
        def run():
            websocket.enableTrace(False)
            wsUrl = self.wsParam.create_url()
            ws = websocket.WebSocketApp(wsUrl, on_message=self.on_message(), on_error=on_error, on_close=self.on_close())
            ws.on_open = self.on_open()
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        thread.start_new_thread(run, ())
    
    def on_open(self):
        def on_open_(ws):
            def run(*args):
                d = {"common": self.wsParam.CommonArgs,
                    "business": self.wsParam.BusinessArgs,
                    "data":{"status": 2, "text": str(base64.b64encode(self.text.encode('utf-8')), "UTF8")},
                    }
                d = json.dumps(d)
                ws.send(d)
            thread.start_new_thread(run, ())
        return on_open_

    def on_message(self):
        def on_message_(ws, message):
            try:
                message =json.loads(message)
                code = message["code"]
                sid = message["sid"]
                audio = message["data"]["audio"]
                audio = base64.b64decode(audio)
                status = message["data"]["status"]
                if status == 2:
                    # print("ws is closed")
                    ws.close()
                if code != 0:
                    errMsg = message["message"]
                    print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
                elif len(audio) > 0:
                    if self.audio_queue is not None:
                        self.audio_queue.put(audio)
            except Exception as e:
                print("receive msg,but parse exception:", e)
        return on_message_
    
    def on_close(self):
        def on_close_(ws):
            if self.audio_queue is not None:
                self.audio_queue.put(None)
        return on_close_
    
    def __iter__(self):
        while True:
            data_slice = self.audio_queue.get()
            if data_slice is None:
                return
            yield data_slice

class XunFeiTTSClient():
    def __init__(self, stream = None, audio_queue = None, text_queue = None, APPID = None, APIKey = None, APISecret = None) -> None:
        self.audio_queue = audio_queue
        self.closed = False
        self.stream = stream
        self.text_queue = text_queue
        self.wsParam = Ws_Param(APPID, APIKey, APISecret)
        def run():
            while not self.closed:
                cone = self.audio_queue.get()
                for data in cone:
                    self.stream.write(data)
        self.run = run

    def send_text(self, text):
        print("Zengwangding: ", text)
        cone = Connection(text, self.wsParam)
        cone.start_run()
        if self.audio_queue is not None:
            self.audio_queue.put(cone)

    def loop_playback(self):
        thread.start_new_thread(self.run, ())
    
    def check(self, text : str):
        for ch in text.lower():
            if ch.islower():
                return True
        return False
    
    def loop(self):
        self.loop_playback()
        def run():
            while True:
                text, _ = self.text_queue.get()
                if not self.check(text):
                    print("skip text: ", text)
                    continue
                self.send_text(text)
        thread.start_new_thread(run, ())

    def close(self):
        self.closed = True

if __name__ == "__main__":
    client = TTSClient(queue.Queue())
    client.send_text("this is my name")
    client.send_text("this is not my name")
    client.loop()
    