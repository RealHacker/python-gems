import SocketServer, socket
import mimetools, mimetypes
import os
import imp
import urlparse
import time
import shutil
import json
import sys
import urllib
import requests
import copy
try:
    import cStringIO as StringIO
except:
    import StringIO

# templates
error_tpl = u"""
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

listing_tpl = u"""
    <html>
        <head>
            <title>%s</title>
        </head>
        <body>
            <h1>%s</h1><hr>
            %s
        </body>
    </html>
"""
# Exceptions
class WSGIFileNotFound(Exception):
    "Raised when wsgi file is not found in file system"
class WSGIInvalid(Exception):
    "Raised when wsgi file is not a valid python module, or application doesn't exist"
class StaticDirNotValid(Exception):
    "Raised when static dir is not found or is not a directory"
class DuplicatePath(Exception):
    "Raised when defining duplicate path in configuration file"

# A mux to route HTTP path to correct handler
class Mux(object):
    def __init__(self):
        self.dict = {}
        self.sortedkeys = []

    def register_handler(self, path, handler):
        # register a virutal path to a handler
        if path in self.dict:
            raise DuplicatePath()
        self.dict[path] = handler
        idx = -1
        for i, key in enumerate(self.sortedkeys):
            if path.startswith(key):
                idx = i
                break
        if idx < 0:
            self.sortedkeys.append(path)
        else:
            self.sortedkeys.insert(idx, path)

    def get_handler(self, path):
        for key in self.sortedkeys:
            if path.startswith(key):
                return self.dict[key]
        return None

# global mux object
mux = Mux()

# the main server
class WebServer(object):
    # configuration is a json file
    def _read_config(self):
        try:
            f = open("config.json", 'r')
        except:
            add_error_log("Fail to read config file, exiting now ...")
            raise SystemExit()
        try:
            config = json.load(f)       
        except ValueError:
            add_error_log("Fail to parse config file, exiting now...")
            raise SystemExit()
        try:
            self._address = config['server']['ip']
            self._port = config['server']["port"]
            self._mode = config['server']['mode']
        except KeyError:
            add_error_log("Missing server basic configuration, using defaults...")
        self._routes = config['routes']

    def __init__(self):
        # defaults
        self._address = "127.0.0.1"
        self._port = 80
        self._mode = "thread"
        # load from config
        self._read_config()
        # initialize the mux
        for path in self._routes:
            d = self._routes[path]
            if d['type'] == "static":
                try:
                    handler = StaticHandler(path, d['dir'])
                except StaticDirNotValid:
                    add_error_log("Static directory in config file not valid, exiting...")
                    raise SystemExit()
            elif d['type'] == "wsgi":
                try:
                    handler = WSGIHandler(path, d['application'])
                except WSGIInvalid, WSGIFileNotFound:
                    handler = None
                    add_error_log("WSGI file invalid, ignoring path %s"%path)
            elif d['type'] =="proxy":
                handler = ProxyHandler(path, d['proxyurl'])
            else:
                add_error_log("Unsupported path definition: %s"%path)
            # link the handler and self
            handler.server = self
            try:
                mux.register_handler(path, handler)
            except DuplicatePath:
                add_error_log("Config file contains duplicate path definition, exiting...")
                raise SystemExit()

    def start(self):
        address = (self._address, self._port)
        if self._mode == "thread":
            server = SocketServer.ThreadingTCPServer(address, HTTPServerHandler)
        else:
            server = SocketServer.ForkingTCPServer(address, HTTPServerHandler)
        host, port = server.socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        server.serve_forever()

# implementation of handlers, each handler class should implement a handle_request(serv) method
# For now, static handler only accept GET requests
class StaticHandler(object):
    def __init__(self, virtual_path, static_dir):
        self.virtual_path = virtual_path
        self.static_dir = static_dir
        if not os.path.exists(static_dir) or not os.path.isdir(static_dir):
            raise StaticDirNotValid

    def handle_request(self, serv):
        if serv.verb.lower() != "get":
            serv.send_error_response(400, "Unsupported HTTP Method")
        # get the file system real path for the file/dir
        parsed = urlparse.urlparse(serv.path)
        relative_path = parsed.path[len(self.virtual_path):]
        unquoted_path = urllib.unquote(relative_path)
        real_path = self.static_dir + unquoted_path.decode(sys.getfilesystemencoding())
       
        if not os.path.exists(real_path):
            serv.send_error_response(404, "File/directory not found.")
            return
        # handle differently for dir and file
        if os.path.isdir(real_path):                      
            # get the file listing
            listing = os.listdir(real_path)
            if not relative_path.endswith("/"):
                relative_path = relative_path + "/" 

            # first try index.html if exists
            index_files = ["index.html", "index.htm"]
            for index in index_files:
                if index in listing:
                    serv.send_response_line(302, "Redirected")
                    index_path = os.path.join(self.virtual_path + relative_path, index)
                    serv.send_header("Location", index_path)
                    serv.end_headers()
                    return

            # index.html not present, generate the listing html
            # Send the response line and headers
            serv.send_response_line(200, "OK") 
            serv.send_header("Content-Type", "text/html;charset=%s"%sys.getfilesystemencoding())
            serv.send_header("Connection", "close")
            # Construct HTML
            listing_str = ""
            if relative_path != "/":
                # if not root, add parent directory link
                parent_path = "/".join(relative_path.split("/")[:-2])
                href = self.virtual_path + parent_path
                line = u"<a href='%s'>..</a><br>"%href
                listing_str += line
            # construct the file list
            for item in listing:
                if isinstance(item, unicode):
                    # decode to unicode
                    stritem = item.encode(sys.getfilesystemencoding())
                    unicodeitem = item
                else:
                    stritem = item
                    unicodeitem = item.decode(sys.getfilesystemencoding())
                # urllib.quote must be given str, not unicode
                quoted_item = urllib.quote(stritem)
                # construct url with quoted file name
                href = os.path.join(self.virtual_path+relative_path, quoted_item)
                snippet = u"<a href='%s'>%s</a><br>"%(href, unicodeitem)
                listing_str += snippet

            display_path = self.virtual_path+relative_path
            listing_html = listing_tpl%(display_path, display_path, listing_str)
            listing_html = listing_html.encode(sys.getfilesystemencoding())
            serv.send_header("Content-Length", len(listing_html))
            serv.end_headers() 
            serv.wfile.write(listing_html)
        else:
            try:
                f = open(real_path, "rb")
            except:
                serv.send_error_response(404, "File not found")
                return
            serv.send_response_line(200, "OK") 
            _, ext = os.path.splitext(real_path)
            # ignore case of extension
            ext = ext.lower() 
            # make a guess based on mimetypes
            content_type = mimetypes.types_map.get(ext, '')
            if not content_type:
                # default to text/html
                content_type = "text/html"
            serv.send_header("Content-Type", content_type)
            # content-length and last-modified
            stat = os.fstat(f.fileno())            
            serv.send_header("Content-Length", str(stat.st_size))
            serv.send_header("Last-Modified", timestamp_to_string(stat.st_mtime))
            serv.send_header("Connection", "close")
            serv.end_headers()
            # now copy the file over
            shutil.copyfileobj(f, serv.wfile)

class ProxyHandler(object):
    def __init__(self, virtual_path, proxyurl):
        self.virtual_path = virtual_path
        if proxyurl.endswith("/"):
            self.proxyurl = proxyurl[:-1]
        else:
            self.proxyurl = proxyurl

    def handle_request(self, serv):
        parsed = urlparse.urlparse(serv.path)
        real_path = parsed.path[len(self.virtual_path):]
        if not real_path.startswith("/"):
            real_path= "/" + real_path
        real_url = self.proxyurl + real_path

        headers = copy.copy(serv.headers)
        del headers["Cookie"]
        headers['Host'] = urlparse.urlparse(self.proxyurl).netloc

        # Read the body of request
        body = ""
        if 'Content-Length' in headers and headers["Content-Length"]:
            body = serv.rfile.read(int(headers["Content-Length"]))
        print body
        # use requests to do the dirty work
        try:
            response = requests.request(serv.verb.upper(), real_url, 
                params=parsed.query, headers=headers, data=body,
                allow_redirects=False)
        except Exception, e:
            add_error_log("Error when sending request to proxyurl:"+ str(e))
            import traceback
            print traceback.format_exc()
            raise e
        # just translate
        serv.send_response_line(response.status_code, response.reason)
        for header in response.headers:
            # encoding has been handled by requests
            if header.lower()=="content-encoding" or header.lower()=="transfer-encoding":
                continue
            serv.send_header(header, response.headers[header])
        serv.send_header("Content-Length", len(response.content))

        serv.end_headers()
        
        serv.wfile.write(response.content)


class WSGIHandler(object):
    def __init__(self, virtual_path, app_path):
        self.virtual_path = virtual_path
        self.load_application(app_path)
        
    def load_application(self, app_path):
        if not os.path.exists(app_path):
            raise WSGIFileNotFound()
        path, filename = os.path.split(app_path)
        modulename, ext = os.path.splitext(filename)
        # Add the path to sys.path
        sys.path.append(path)
        try:
            if ext.lower() == ".py" or ext.lower() == ".wsgi":
                m = imp.load_source(modulename, app_path)
            else:
                m = imp.load_compiled(modulename, app_path)
        except Exception as e:
            add_error_log(str(e))
            raise WSGIInvalid()
        else:
            if not hasattr(m, "application"):
                add_error_log("Wsgi application not found")
                raise WSGIInvalid()
            self.app = m.application
            if not callable(self.app):
                add_error_log("Wsgi application not callable")
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
        return headers_environ
    
    def prepare_environ(self, serv):
        parsed = urlparse.urlparse(serv.path)
        real_path = parsed.path[len(self.virtual_path):]
        if not real_path.startswith("/"):
            real_path= "/" + real_path
        environ = {
            "REQUEST_METHOD":   serv.verb,
            "SCRIPT_NAME":      self.virtual_path,
            "PATH_INFO":        real_path,
            "QUERY_STRING":     parsed.query,
            "CONTENT_TYPE":     serv.headers.get("Content-Type", ""),
            "CONTENT_LENGTH":   serv.headers.get("Content-Length", ""),
            "SERVER_NAME":      self.server.server_name,
            "SERVER_PORT":      self.server.server_port,
            "SERVER_PROTOCOL":  "HTTP/1.1",
            "wsgi.input":       serv.rfile,
            "wsgi.errors":      serv.error,
            "wsgi.version":     (1,0),
            "wsgi.run_once":    False,
            "wsgi.url_scheme":  "http", 
            "wsgi.multithread":     self.server._mode=="thread",
            "wsgi.multiprocess":    self.server._mode=="process", 
        }
        environ.update(self.get_headers_environ(serv))
        return environ

    def handle_request(self, serv):
        # environ
        environ = self.prepare_environ(serv)
        # start_response
        def start_response(status, response_headers):
            serv.send_status_line(status)
            for k, v in response_headers:
                serv.send_header(k, v)
            serv.end_headers()
        # Get response lines
        try:
            response_chucks = self.app(environ, start_response)
        except Exception as e:
            add_error_log("* ERROR IN WSGI APP *" + str(e))
            raise e
        else:
            for chuck in response_chucks:
                serv.wfile.write(chuck)

# This is the handler entry point, dispatching requests to different handlers with the help of mux
class HTTPServerHandler(SocketServer.StreamRequestHandler):
    def __init__(self, request, client_addr, server):
        self.error = StringIO.StringIO()
        SocketServer.StreamRequestHandler.__init__(self, request, client_addr, server)
        
    # Should read the request from self.rfile
    # and write the response to self.wfile
    def handle_one_request(self):
        try:
            # read the first line from request
            request_line = self.rfile.readline()
            words = request_line.strip().split()
            if len(words) != 3:
                self.send_error_response(400, "Invalid HTTP request")
                return
            self.verb, self.path, _ = words
            add_access_log(self.verb+" "+self.path)
            # read the header lines
            self.headers = mimetools.Message(self.rfile, 0)
            connection_type = self.headers.get("Connection", "")
            if connection_type == "close":
                self.close_connection = True
            elif connection_type == "keep-alive":
                self.close_connection = False

            # delegate body handling to mux
            handler = mux.get_handler(self.path)
            if not handler:
                self.send_error_response(404, "File Not Found")
                return
            handler.handle_request(self)
            if not self.wfile.closed:
                self.wfile.flush()
                self.wfile.close()

            # If the request handler write some error messages, record them in log
            if self.error.tell():
                self.error.seek(0)
                add_error_log(self.error.read())
        except Exception, e:
            add_error_log(str(e))
            self.close_connection = True
                        
    def handle(self):
        self.close_connection = True
        self.handle_one_request()
        # supporting keep-alive
        while not self.close_connection:
            self.handle_one_request()

    def send_response_line(self, code, explanation):
        self.send_status_line("%d %s"%(code, explanation))

    def send_status_line(self, status):
        response_line = "HTTP/1.1 %s\r\n"%status
        self.wfile.write(response_line)
        self.send_header("Server", "Neo's HTTP Server")
        
    def send_header(self, name, value):
        self.wfile.write("%s: %s\r\n"%(name, value))
        if name.lower() == "connection":
            if value.lower() == "close":
                self.close_connection = True
            elif value.lower() == "keep-alive":
                self.close_connection = False

    def end_headers(self):
        self.wfile.write("\r\n")
        
    def send_error_response(self, code, explanation):
        self.send_response_line(code, explanation)
        self.send_header("Content-type", "text/html")
        self.send_header("Connection", "close")
        self.end_headers()
        message_body = error_tpl%(code, code,  explanation)
        self.wfile.write(message_body)
        if not self.wfile.closed:
            self.wfile.flush()
        
# helper functions
def timestamp_to_string(timestamp=None):
    """Return the current date and time formatted for a message header."""
    weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    monthname = [None,
             'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    if timestamp is None:
        timestamp = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
            weekdayname[wd],
            day, monthname[month], year,
            hh, mm, ss)
    return s

def add_error_log(entry):
    print "[ERROR] - " + entry

def add_access_log(entry):
    print "[REQUEST] - " + entry

# The driver
def main():
    server = WebServer()
    server.start()

if __name__ == "__main__":
    main()
