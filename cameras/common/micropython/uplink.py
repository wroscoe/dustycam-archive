"""uplink: raw-socket HTTP to sensorhub through the blob gate.

Standard §4 (docs/camera_standard.md). Raw sockets because the frozen
MicroPython `requests` cannot parse the ingest's HTTP/1.0 reply. TLS (the
Funnel path) has no CA bundle on the board, so the server cert is not
verified; the shared BLOB_TOKEN is the authentication, the tunnel only
hides it.

Needs from secrets: DEVICE, SERVER_HOST, SERVER_PORT, SERVER_TLS, BLOB_TOKEN.

SERVER_HOST/SERVER_PORT/SERVER_TLS default from secrets.py but are plain
module globals, not secrets.* reads, so contact.py's set_server() can point
_connect/_head/http_get at the home LAN gate instead of the hotspot/public
path for the length of one contact (docs/camera_operation.md §5: two
networks in secrets, chosen by a pre-join scan).
"""
import socket

import secrets

SERVER_HOST = secrets.SERVER_HOST
SERVER_PORT = secrets.SERVER_PORT
SERVER_TLS = getattr(secrets, 'SERVER_TLS', False)
_DEFAULT_HOST, _DEFAULT_PORT, _DEFAULT_TLS = SERVER_HOST, SERVER_PORT, SERVER_TLS
BLOB_TOKEN = getattr(secrets, 'BLOB_TOKEN', '')
LAST_ERROR = ['']            # last socket error, for /status
LAST_DATE = ['']             # the reply's Date: header from the last http_get, for the clock (contact.py)


def set_server(host, port=None, tls=None):
    """Override SERVER_HOST/SERVER_PORT/SERVER_TLS for the rest of this
    contact (contact.py picks LAN vs. hotspot/public by scan before
    joining). set_server(None) restores the secrets.py defaults."""
    global SERVER_HOST, SERVER_PORT, SERVER_TLS
    if host is None:
        SERVER_HOST, SERVER_PORT, SERVER_TLS = _DEFAULT_HOST, _DEFAULT_PORT, _DEFAULT_TLS
    else:
        SERVER_HOST, SERVER_PORT, SERVER_TLS = host, port, tls


def _connect(timeout=15):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(SERVER_HOST, SERVER_PORT)[0][-1])
    if SERVER_TLS:
        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.verify_mode = ssl.CERT_NONE
        s = ctx.wrap_socket(s, server_hostname=SERVER_HOST)
    return s


def _head(method, path, ctype, length, extra=''):
    return ('%s %s HTTP/1.1\r\nHost: %s\r\n%s%sContent-Type: %s\r\n'
            'Content-Length: %d\r\nConnection: close\r\n\r\n'
            % (method, path, SERVER_HOST,
               ('X-Token: %s\r\n' % BLOB_TOKEN) if BLOB_TOKEN else '',
               extra, ctype, length)).encode()


def _write_body(s, data):
    """bytes-like, or an open file streamed in 4 kB chunks (a full-res frame
    from SD never lands in the heap)."""
    if hasattr(data, 'read'):
        while True:
            chunk = data.read(4096)
            if not chunk:
                break
            s.write(chunk)
    else:
        mv = memoryview(data)
        for i in range(0, len(data), 4096):
            s.write(mv[i:i + 4096])


def _ok(s):
    resp = s.read(15)
    return b' 2' in resp[:13]


def post_blob(kind, data, meta, length=None):
    """POST /blob/<device>/<kind> with X-Meta JSON. True on 2xx."""
    s = None
    try:
        s = _connect()
        s.write(_head('POST', '/blob/%s/%s' % (secrets.DEVICE, kind), 'image/jpeg',
                      len(data) if length is None else length, 'X-Meta: %s\r\n' % meta))
        _write_body(s, data)
        return _ok(s)
    except OSError as e:
        LAST_ERROR[0] = 'blob %r' % e
        print('post error:', repr(e))
        return False
    finally:
        if s:
            s.close()


def post_json(path, body):
    """POST a JSON string. True on 2xx."""
    if isinstance(body, str):
        body = body.encode()
    s = None
    try:
        s = _connect()
        s.write(_head('POST', path, 'application/json', len(body)))
        s.write(body)
        return _ok(s)
    except OSError as e:
        LAST_ERROR[0] = '%s %r' % (path, e)
        print('post error:', path, repr(e))
        return False
    finally:
        if s:
            s.close()


def http_get(path, max_len=131072, timeout=15):
    """GET -> (status, body bytes). (0, b'') on a socket error."""
    s = None
    try:
        s = _connect(timeout)
        s.write(('GET %s HTTP/1.1\r\nHost: %s\r\n%sConnection: close\r\n\r\n'
                 % (path, SERVER_HOST,
                    ('X-Token: %s\r\n' % BLOB_TOKEN) if BLOB_TOKEN else '')).encode())
        resp = b''
        while len(resp) < max_len:
            chunk = s.read(4096)
            if not chunk:
                break
            resp += chunk
        head, _, body = resp.partition(b'\r\n\r\n')
        for line in head.split(b'\r\n')[1:]:
            if line[:5].lower() == b'date:':
                LAST_DATE[0] = line[5:].strip().decode()
                break
        return int(head.split(b' ', 2)[1].decode()), body
    except (OSError, ValueError, IndexError) as e:
        print('get error:', path, repr(e))
        return 0, b''
    finally:
        if s:
            s.close()
