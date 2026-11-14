# Cầu nối: nhận code Python qua 127.0.0.1:9877 và chạy trong Blender đang mở.
# Mở:  /Applications/Blender.app/Contents/MacOS/Blender blender/floor7.blend --python blender/bridge.py
# Gửi: python3 blender/send.py <<< 'print(len(bpy.data.objects))'
# shortcut: không xác thực, chỉ nghe localhost — mọi tiến trình trên máy này đều chạy được code; đóng Blender là tắt.
import bpy, socket, threading, queue, io, contextlib, traceback

jobs = queue.Queue()

def serve():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 9877))
    s.listen()
    while True:
        conn, _ = s.accept()
        data = b""
        while chunk := conn.recv(65536):  # client đóng chiều ghi khi gửi xong
            data += chunk
        jobs.put((conn, data.decode()))

def pump():  # bpy chỉ an toàn trên main thread nên chạy code qua timer
    while not jobs.empty():
        conn, code = jobs.get()
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                exec(code, {"bpy": bpy})
        except Exception:
            out.write(traceback.format_exc())
        try:
            conn.sendall(out.getvalue().encode() or b"ok\n")
        finally:
            conn.close()
    return 0.1

threading.Thread(target=serve, daemon=True).start()
bpy.app.timers.register(pump, persistent=True)
