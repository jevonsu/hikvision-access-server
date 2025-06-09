# 定义门禁通行记录的类
import json

class AccessRecord:
    def __init__(self, record_json):
        self.data = record_json

    def to_json(self):
        return json.dumps(self.data, ensure_ascii=False)
