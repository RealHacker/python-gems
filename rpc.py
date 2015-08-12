"""
This is a RPC server/client implementation using socket
* It authenticate the client with a secret shared by client/server
* It uses JSON to serialize the function call payload
"""
import socket
import random, string
import hmac
import json
import threading

secret = "SECRET"

class RPCHandler:
    def __init__(self, secret):
        self._secret = secret
        self._register = {}

    def register_func(self, func):
        self._register[func.__name__] = func
        
    def handle_call(self, sock):
        keymsg = ''.join([random.choice(string.lowercase) for i in range(8)])
        sock.sendall(keymsg)
        hash = hmac.new(self._secret, keymsg)
        digest = hash.digest()
        response = sock.recv(512)
        if response != digest:
            sock.sendall("Authentication Failed!")
            sock.close()
        else:
            sock.sendall("Authenticated!")
            try:
                while True:
                    req = sock.recv(512)
                    d = json.loads(req)
                    funcname = d["name"]
                    args = d["args"]
                    kwargs = d["kwargs"]
                    print "Client calling %s(%s, %s)"%(funcname, args, kwargs)
                    try:
                        ret = self._register[funcname](*args, **kwargs)
                        sock.sendall(json.dumps({"ret": ret}))
                    except Exception as e:
                        sock.sendall(json.dumps({"exception": str(e)}))
            except EOFError:
                print "Closing RPC Handler..."

handler = RPCHandler(secret)

class RPCServer:
    def __init__(self, address):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(address)

    def serve_forever(self):
        self._sock.listen(0)
        while True:
            client_sock,_ = self._sock.accept()
            thread = threading.Thread(target=handler.handle_call, args=(client_sock, ))
            thread.daemon = True
            thread.start()

class RPCProxy(object):
    def __init__(self, address, secret):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect(address)
        msg = self._sock.recv(512)
        h = hmac.new(secret, msg)
        self._sock.sendall(h.digest())
        print self._sock.recv(512)

    def __getattr__(self, name):
        def proxy_func(*args, **kwargs):
            payload = {
                "name": name,
                "args": args,
                "kwargs": kwargs
            }
            self._sock.sendall(json.dumps(payload))
            result = json.loads(self._sock.recv(512))
            if "exception" in result:
                raise Exception(result['exception'])
            else:
                return result['ret']
        if name.startswith("_"):
            return super(RPCProxy, self).__getattr__(name)
        else:
            return proxy_func
            
