# 处理文件写入的工具函数
def write_to_file(filename, data):
    import json
    with open(filename, 'a', encoding='utf-8') as f:
        if isinstance(data, dict):
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        else:
            f.write(str(data) + '\n')
