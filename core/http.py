import socket

def http_check(host):
    try:
        client = socket.socket()
        client.settimeout(3)
        client.connect((host, 80))

        request = f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        client.send(request.encode())

        response = client.recv(1024).decode(errors="ignore")
        client.close()

        return "200 OK" if "200" in response else "Responded"
    except:
        return "Failed"