# Gửi code từ stdin vào Blender (xem bridge.py), in kết quả.
import socket, sys

s = socket.create_connection(("127.0.0.1", 9877), timeout=60)
s.sendall(sys.stdin.read().encode())
s.shutdown(socket.SHUT_WR)
out = b""
while chunk := s.recv(65536):
    out += chunk
print(out.decode(), end="")
