import SocketServer, socket
import mimetools
import os
import imp
import urlparse
try:
    import CStringIO as StringIO
except:
    import StringIO

error_tpl = """
    <html>
        <head>
            <title>Error %d</title>
        </head>
        <body>
            <h1>%d</h1><hr>
            <h2>%s</h2>
        </body>
    </html>
"""

class WSGIFileNotFound(Exception):
    "Raised when wsgi file is not found in file system"
class WSGIInvalid(Exception):
    "Raised when wsgi file is not a valid python module, or application doesn't exist"
    
class WebServer(object):
    def __init__(self):
        self._address="127.0.0.1"
        self._port=80

    def start(self):
        address = (self.server_address, self.server_port)
        server = SocketServer.ThreadingTCPServer(address, HTTPServerHandler)
        host, port = server.socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        server.serve_forever()

class WSGIHandler(object):
    def __init__(self, virtual_path, app_path):
        self.virtual_path = virtual_path
        self.load_application(app_path)
        
    def load_application(self, app_path):
        if not os.path.exists(app_path):
            raise WSGIFileNotFound()
        filename = os.path.split(app_path)[-1]
        modulename, ext = os.path.splitext(filename)
        try:
            if ext.lower() == ".py":
                m = imp.load_source(modulename, app_path)
            else:
                m = imp.load_compiled(modulename, app_path)
        except Exception:
            raise WSGIInvalid()
        else:
            if not hasattr(m, "application"):
                raise WSGIInvalid()
            self.app = m.application
            if not callable(self.app):
                raise WSGIInvalid()
            
    def get_headers_environ(self, serv):
        headers_environ = {}
        for key in serv.headers:
            val = serv.headers[key]
            if "-" in key:
                key = key.replace("-", "_")
            key = "HTTP_" + key.upper()
            if key not in headers_environ:
                headers_environ[key] = val
            else:
                headers_environ[key] += "," + val
        return header_environ
    
    def prepare_environ(self, serv):
        parsed = urlparse.urlparse(serv.path)
        real_path = parsed.path[len(self.virtual_path):]
        if not real_path.startswith("/"):
            real_path= "/" + realpath
        environ = {
            "REQUEST_METHOD":   serv.verb,
            "SCRIPT_NAME":      self.virtual_path,
            "PATH_INFO":        realpath,
            "QUERY_STRING":     parsed.query,
            "CONTENT_TYPE":     serve.header.get("Content-Type", ""),
            "CONTENT_LENGTH":   serve.header.get("Content-Length", ""),
            "SERVER_NAME":      self.server.server_name,
            "SERVER_PORT":      self.server.server_port,
            "SERVER_PROTOCOL":  "HTTP/1.1",
            "wsgi.input":       serv.rfile,
            "wsgi.errors":      serv.error,
            "wsgi.version":     (1,0),
            "wsgi.run_once":    False,
            "wsgi.url_scheme":  "http", 
            "wsgi.multithread": True,
            "wsgi.multiprocess":False, 
        }
        environ.update(self.get_headers_environ(serv))
        return environ

    def handle_request(serv):
        # environ
        environ = self.prepare_environ(serv)
        # start_response
        def start_response(status, response_headers):
            serv.send_status_line(status)
            for k, v in response_headers:
                serv.send_header(k, v)
            serv.end_headers()
        # response lines
        response_chucks = self.app(environ, start_response)
        for chuck in response_chucks:
            serv.wfile.write(chuck)
        

class Mux(object):
    def register_handler(path, handler):
        # register a virutal path to a handler
        pass
    
    def get_handler(path):
        
        
class HTTPServerHandler(SocketServer.StreamRequestHandler):
    def __init__(self):
        self.mux =
        self.error = StringIO.StringIO()
    # handle should read the request from self.rfile
    # and write the response to self.wfile
    def handle_one_request():
        try:
            # read the first line from request
            request_line = self.rfile.readline()
            words = request_line.strip().split()
            if len(words) != 3:
                send_error_response(400, "Invalid HTTP request")
                return
            self.verb, self.path, _ = words
            # read the header lines
            self.headers = mimetools.Message(self.rfile, 0)
            connection_type = self.headers.get("Connection", "")
            if connection_type == "close":
                self.close_connection = True
            elif connection_type == "keep-alive":
                self.close_connection = False
            # delegate body handling to mux
            handler = self.mux.get_handler(self.path)
            handler.handle_request(self)
            self.wfile.flush()
        except Exception, e:
            self.close_connection = True
                        
    def handle():
        self.close_connection = True
        self.handle_one_request()
        while not self.close_connection:
            self.handle_one_request()

    def send_response_line(self, code, explanation):
        self.send_status_line("%d %s"%(code, explanation))

    def send_status_line(self, status):
        response_line = "HTTP/1.1 %s\r\n"%status
        self.wfile.write(response_line)
        self.send_header("Server", "Neo's HTTP Server")
        
    def send_header(self, name, value):
        self.wfile.write("%s: %r\r\n"%(name, value))
        if name.lower() == "connection":
            if value.lower() == "close":
                self.close_connection = True
            elif value.lower() == "keep-alive":
                self.close_connection = False

    def end_headers(self):
        self.wfile.write("\r\n")
        
    def send_error_response(code, explanation):
        self.send_response_line(code, explanation)
        self.send_header("Content-type", "text/html")
        self.send_header("Connection", "close")
        self.end_headers()
        message_body = error_tpl%(code, explanation)
        self.wfile.write(message_body)
        self.wfile.flush()
        
    
    
                 
