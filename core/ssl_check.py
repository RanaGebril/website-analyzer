import ssl
import socket

def ssl_check(host):
    try:
        context = ssl.create_default_context()
        sock = socket.create_connection((host, 443), timeout=3)

        ssl_sock = context.wrap_socket(sock, server_hostname=host)
        ssl_sock.getpeercert()
        ssl_sock.close()

        return "Valid HTTPS"
    except:
        return "No SSL"