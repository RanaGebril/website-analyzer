import socket

def udp_test():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(2)
        client.sendto(b"ping", ("8.8.8.8", 53))
        return "Sent"
    except:
        return "Failed"