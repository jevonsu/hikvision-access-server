# 应用程序入口点，创建HTTP服务器
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from utils.file_writer import write_to_file
from typess.record import AccessRecord
import pymysql
import time
import json
import threading
from werkzeug.exceptions import BadRequest

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB，允许大体积推送

PASS_LOG = os.path.join(os.path.dirname(__file__), '../pass_log.txt')
RECORD_LOG = os.path.join(os.path.dirname(__file__), '../record_log.txt')
LOG_JSON_PATH = os.path.join(os.path.dirname(__file__), '../log/record_log.jsonl')

def find_datetime(obj):
    """递归查找所有嵌套AccessControllerEvent中的dateTime字段，找到第一个就返回"""
    if not isinstance(obj, dict):
        return None
    dt = obj.get('dateTime')
    if dt:
        return dt
    ace = obj.get('AccessControllerEvent')
    if ace:
        return find_datetime(ace)
    return None

def insert_to_mysql(event_log_json):
    # 递归获取最内层AccessControllerEvent
    ace = event_log_json.get('AccessControllerEvent', {})
    while isinstance(ace, dict) and 'AccessControllerEvent' in ace:
        ace = ace['AccessControllerEvent']
    # 递归查找dateTime，优先从ace及所有嵌套层级，找不到再从event_log_json外层
    dt = find_datetime(event_log_json)
    record_date, record_time = None, None
    if dt and 'T' in dt:
        try:
            record_date, record_time = dt.split('T')
            record_time = record_time.split('+')[0] if '+' in record_time else record_time
            record_time = record_time.split('Z')[0] if 'Z' in record_time else record_time
        except Exception as e:
            print('日期时间解析失败:', e)
    else:
        print('未获取到有效dateTime字段，record_date/record_time将为None')
    # event_type 优先从ace取，没有再从event_log_json外层取
    event_type = ace.get('eventType') or event_log_json.get('eventType')
    # 兼容所有字段优先从ace取，没有再从event_log_json外层取
    deviceName = ace.get('deviceName') or event_log_json.get('deviceName')
    name = ace.get('name') or event_log_json.get('name')
    cardNo = ace.get('cardNo') or event_log_json.get('cardNo')
    employeeNoString = ace.get('employeeNoString') or event_log_json.get('employeeNoString')
    # 不采集图片相关字段
    try:
        conn = pymysql.connect(
            host=os.environ.get('MYSQL_HOST', '10.20.0.8'),
            port=int(os.environ.get('MYSQL_PORT', 3306)),
            user=os.environ.get('MYSQL_USER', 'access_recordss'),
            password=os.environ.get('MYSQL_PASSWORD', 'your_password'),
            database=os.environ.get('MYSQL_DB', 'access_recordss'),
            charset='utf8mb4'
        )
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO access_recordss (deviceName, record_date, record_time, em_name, cardNo, employeeNoString, event_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                deviceName,
                record_date,
                record_time,
                name,
                cardNo,
                employeeNoString,
                event_type
            ))
            conn.commit()
        conn.close()
        print('数据已写入MySQL')
    except Exception as e:
        print('写入MySQL失败:', e)

@app.route('/pass', methods=['POST'])
def handle_pass():
    data = request.get_json(silent=True)
    print("收到/pass推送：", data)
    if data is None:
        # 兼容 form-data 或其它格式
        if request.form:
            data = request.form.to_dict()
            print("收到/pass form-data：", data)
        elif request.data:
            try:
                data = json.loads(request.data.decode('utf-8'))
                print("收到/pass raw-json：", data)
            except Exception as e:
                data = request.data.decode('utf-8', errors='ignore')
                print("收到/pass raw-str：", data)
    write_to_file(PASS_LOG, data)
    return jsonify({'status': 'pass record received'})

@app.route('/record', methods=['POST'])
def handle_record():
    data = None
    src_ip = request.remote_addr
    try:
        ct = request.content_type or ''
        print(f"[{src_ip}] headers: {dict(request.headers)}")
        print(f"[{src_ip}] raw data: {request.data}")
        print(f"[{src_ip}] form: {request.form}")
        # 优先用 silent=True，避免抛异常
        if 'application/json' in ct:
            data = request.get_json(silent=True)
            print(f"[{src_ip}] 收到JSON推送: {data}")
        elif 'multipart/form-data' in ct or 'application/x-www-form-urlencoded' in ct:
            data = request.form.to_dict()
            print(f"[{src_ip}] 收到form-data推送: {data}")
            for k, v in data.items():
                if isinstance(v, str) and v.strip().startswith('{'):
                    try:
                        data[k] = json.loads(v)
                        print(f"[{src_ip}] 字段{k}解析为JSON: {data[k]}")
                    except Exception as e:
                        print(f"[{src_ip}] 字段{k}解析JSON失败: {e}")
        else:
            try:
                data = request.get_json(silent=True)
                if data is not None:
                    print(f"[{src_ip}] 收到JSON推送: {data}")
                else:
                    data = json.loads(request.data.decode('utf-8'))
                    print(f"[{src_ip}] 收到raw-json推送: {data}")
            except Exception as e2:
                print(f"[{src_ip}] 解析JSON失败: {e2}")
                data = request.data.decode('utf-8', errors='ignore')
                print(f"[{src_ip}] 收到raw-str推送: {data}")
    except Exception as e:
        print(f"[{src_ip}] 解析数据异常: {e}")
        print(f"[{src_ip}] request.headers: {dict(request.headers)}")
        print(f"[{src_ip}] request.form: {request.form}")
        print(f"[{src_ip}] request.data: {request.data}")
        return jsonify({'error': '数据解析异常', 'detail': str(e)}), 200

    record = None
    event_log_json = None
    if isinstance(data, dict):
        if 'event_log' in data:
            try:
                if isinstance(data['event_log'], str):
                    event_log_json = json.loads(data['event_log'])
                elif isinstance(data['event_log'], dict):
                    event_log_json = data['event_log']
                else:
                    print(f"[{src_ip}] event_log字段类型异常: {type(data['event_log'])}")
                    event_log_json = None
                print(f"[{src_ip}] 解析event_log为JSON: {event_log_json}")
            except Exception as e:
                print(f"[{src_ip}] event_log字段解析失败: {e}")
                return jsonify({'error': 'event_log parse error'}), 200
        elif 'AccessControllerEvent' in data:
            ace_raw = data['AccessControllerEvent']
            if isinstance(ace_raw, str):
                try:
                    ace = json.loads(ace_raw)
                    data['AccessControllerEvent'] = ace
                    print(f"[{src_ip}] 解析AccessControllerEvent为JSON: {ace}")
                except Exception as e:
                    print(f"[{src_ip}] AccessControllerEvent字段解析失败: {e}")
                    return jsonify({'error': 'AccessControllerEvent parse error'}), 200
            event_log_json = data
    if not event_log_json:
        print(f"[{src_ip}] 未检测到event_log或AccessControllerEvent字段，已跳过")
        return jsonify({'status': 'skipped, no event_log or AccessControllerEvent', 'detail': '未检测到event_log或AccessControllerEvent字段', 'data': data}), 200

    ace = event_log_json.get('AccessControllerEvent', {})
    while isinstance(ace, dict) and 'AccessControllerEvent' in ace:
        ace = ace['AccessControllerEvent']
    device = ace.get('deviceName') or event_log_json.get('deviceName', '-')
    name = ace.get('name') or event_log_json.get('name', '-')
    event_type = ace.get('eventType') or event_log_json.get('eventType', '-')
    print(f"[{src_ip}] 解析后device: {device}, name: {name}, ace: {ace}")
    if event_type == 'heartBeat':
        print(f"[{src_ip}] 心跳包已忽略，不记录数据库和日志")
        return jsonify({'status': 'skipped, heartBeat event ignored'}), 200
    if not name or name == '-' or str(name).strip() == '':
        print(f"[{src_ip}] 姓名为空，已跳过日志和入库")
        return jsonify({'status': 'skipped, name empty'}), 200
    if isinstance(ace, dict):
        record = AccessRecord(event_log_json)
        try:
            insert_to_mysql(event_log_json)
        except Exception as e:
            print(f"[{src_ip}] 数据入库异常: {e}")
        # 日志写入log/record_log.jsonl
        write_to_file_json(LOG_JSON_PATH, event_log_json)
        print(f"[{src_ip}] 设备:{device} 姓名:{name} 已记录到日志与数据库")
        return jsonify({'status': 'access record received'})
    else:
        print(f"[{src_ip}] 设备:{device} ace不是dict，未记录")
        return jsonify({'status': 'skipped, ace not dict'}), 200

@app.route('/access-record', methods=['POST'])
def handle_access_record():
    # 兼容外网推送，直接复用/record的处理逻辑
    return handle_record()

def worker():
    pass  # 兼容run387的导入，不再做任何事

def write_to_file_json(filepath, data):
    # 过滤掉图片相关字段
    if isinstance(data, dict):
        def remove_pictures(obj):
            if isinstance(obj, dict):
                obj = {k: remove_pictures(v) for k, v in obj.items() if k not in ['picturesNumber', 'FaceRect', 'picture', 'pictures', 'image', 'img']}
            elif isinstance(obj, list):
                obj = [remove_pictures(i) for i in obj]
            return obj
        data = remove_pictures(data)
    try:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception as e:
        print('写入JSON日志失败:', e)

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    src_ip = request.remote_addr
    print(f"[{src_ip}] BadRequest捕获: {e}")
    try:
        raw = request.get_data()
        print(f"[{src_ip}] 原始body长度: {len(raw)}，内容前500字节: {raw[:500]}")
    except Exception as ex:
        print(f"[{src_ip}] 读取body异常: {ex}")
    return "Bad Request", 400

if __name__ == "__main__":
    print("服务器启动，监听 0.0.0.0:387 ...")
    app.run(host="0.0.0.0", port=387)
