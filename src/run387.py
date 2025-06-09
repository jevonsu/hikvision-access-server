import sys
import os
import multiprocessing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import app as flask_app, worker
import threading

def run_on_port(port):
    print(f"服务器启动，监听 0.0.0.0:{port} ...")
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # 启动286和387端口的服务
    ports = [286, 387]
    processes = []
    for port in ports:
        p = multiprocessing.Process(target=run_on_port, args=(port,))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
