import BaseHTTPServer
import json
import subprocess

page404 = """
<html>
    <head>
        <title>PAGE NOT FOUND</title>
    </head>
    <body>
        <h1>404 - Page not found</h1>
    </body>
</html>
"""

class TerminalHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/":
            with open("index.html", 'r') as f:
                pagestr = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Content-length", str(len(pagestr)))
                self.end_headers()
                self.wfile.write(pagestr)
        else:
            self.send_error(404, "File not found")
            # self.wfile.write(page404)

    def do_POST(self):
        if self.path=="/cmd":
            body = self.rfile.read(int(self.headers['Content-Length']))
            print body
            try:
                request = json.loads(body)
            except:
                self.send_error(500, "command format error")
            else:
                cmdline = request.get("cmd", None)
                runner = CommandRunner(cmdline)
                output = runner.get_output()
                ret = json.dumps({"result":str(output)})
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(ret)
        else:
            self.send_error(404, "File not found")

class CommandRunner(object):
    def __init__(self, cmd):
        self._cmds = cmd.split()

    def get_output(self):
        print "COMMANDS:", self._cmds
        return subprocess.check_output(self._cmds, shell=True)
        
server = BaseHTTPServer.HTTPServer(("127.0.0.1", 8000), TerminalHandler)
server.serve_forever()
