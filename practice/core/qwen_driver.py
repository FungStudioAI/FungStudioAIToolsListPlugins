import os
import json
from openai import OpenAI

class Qwen():
    def __init__(self,console,lock):
        self.console = console
        self.lock = lock

    def get(self,url,key,model_type,question,callback):
        try:
            with self.lock:
                if question.strip() == "":
                    self.console.write(f"没有问题内容！", 1)
                    return
                client = OpenAI(
                    api_key=key,
                    base_url=url,
                )
                completion = client.chat.completions.create(
                    model=model_type,  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
                    messages=[
                        {'role': 'system', 'content': 'You are a helpful assistant.'},
                        {'role': 'user', 'content': question}
                        ]
                )
                json_data = json.loads(completion.choices[0].message.content)
                callback(json_data)
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)