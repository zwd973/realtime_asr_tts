# a wraper of openai's api
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import queue
from threading import Thread
import queue
import json
from llm_agent import prompt
import requests
from logger import logger

class GPTProxy:
    def __init__(self, api_key) -> None:
        self.client = OpenAI(api_key = api_key)
        self.context = []

    def fix(self, req):
        # text = f'{{"zh":"{req[1]}", "en":"{req[0]}"}}'
        text = req['text']
        text = "context:\n" + "\n".join(self.context) + "input:\n" + text
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": prompt.system_prompt},
                # {"role": "user", "content": "Please to correct any spelling discrepancies in the transcribed text which took place in a technical interview related to computer and deep learning. So, you need to correct the relevant technical terms and company names, e.g. 编译器, 商汤科技, 阿里云, PETR, DETR, deep learning, 分布式, raft, 性能. Some English technical terms may be misrecognized as similar-sounding Chinese words, so you also need to correct them. Lastly, you need to translate the Chinese text into American English. Just provide the translated English, and do not add any additional descriptions. If you are unsure how to correct them, leave them as they are and just translate them into english. the input text is: \n" + text}
                {"role": "user", "content": text},
            ]
            # response_format={ "type": "json_object" },
        )
        result = None
        try:
            result = response.choices[0].message.content
            item = json.loads(result)
            en_text = item['en']
            zh_text = item['zh']
            self.context.append(zh_text)
            if len(self.context) > 5:
                self.context.pop(0)
            logger.info(f"Call GPT Success, ori = '{req['text']}', fixed = '{en_text}'")
        except:
            logger.info(f"Call GPT Failed", response)
            result = "Call GPT Failed"
        return result


class MyLLMProxy:
    def __init__(self, url) -> None:
        self.url = url
    
    def fix(self, req):
        return requests.post(
            url = self.url,
            data = {
                "text" : req['text']
            }
        ).json()['text']


class LLMPoolProxy:
    def __init__(self, cfg) -> None:
        # Use multi key
        self.llm_proxys = [llm_item['cls'](*llm_item['kwargs']) for llm_item in cfg.llms]
        self.k = 0
    
    def fix(self, req):
        res =  self.llm_proxys[self.k % len(self.llm_proxys)].fix(req)
        self.k += 1
        return res



class TextFixAgent():
    def __init__(self, input_text_queue, output_queue, cfg) -> None:
        self.input_text_queue = input_text_queue
        self.output_queue = output_queue
        self.mid_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=16)
        self.llm_proxy = LLMPoolProxy(cfg)

    def check(self, text : str):
        for ch in text.lower():
            if ch.islower():
                return True
        return False

    def loop(self):
        def run():
            while True:
                req = self.input_text_queue.get()
                if not self.check(req['text']):
                    continue
                promise =  self.executor.submit(self.llm_proxy.fix, req)
                self.mid_queue.put(promise)

        def receiver():
            while True:
                promise = self.mid_queue.get()
                res = promise.result()
                if "detection error" in res[0].lower():
                    continue
                self.output_queue.put(res)

        self.th1 = Thread(target=run, args=())
        self.th1.start()
        self.th2 = Thread(target=receiver, args=())
        self.th2.start()
