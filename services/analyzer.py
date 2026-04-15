from core.dns import get_ip
from core.tcp import tcp_check
from core.http import http_check
from core.ssl_check import ssl_check
from core.udp import udp_test
from core.ntp import get_time

def analyze(domain, callback):
    domain = domain.strip()

    callback("dns", get_ip(domain))
    callback("tcp", tcp_check(domain))
    callback("http", http_check(domain))
    callback("ssl", ssl_check(domain))
    callback("udp", udp_test())
    callback("ntp", get_time())