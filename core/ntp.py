import socket
import struct
import time

def get_time():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(3)

        client.sendto(b'\x1b' + 47*b'\0', ("pool.ntp.org", 123))

        data, _ = client.recvfrom(1024)
        t = struct.unpack("!12I", data)[10] - 2208988800

        return time.ctime(t)
    except:
        return "Failed"