import socket
import time

def tcp_check(host):
    try:
        start = time.time()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((host, 80))

        end = time.time()
        sock.close()

        return f"OK - {(end-start)*1000:.2f} ms"
    except:
        return "Failed"