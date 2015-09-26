# Web Server #

A simple web server in python, that supports serving:

- Static files
- WSGI application
- Proxy to another web service
- Running server in multi-thread/multi-process mode

## Configuration file ##

    {
		"server":{
			"ip": "127.0.0.1",
			"port": 8000,
			"mode": "thread"
		},
		"routes":{
			"/app": {
				"type": "wsgi",
				"application": "D:/Workspace/Example/wsgi.py"
			},
			"/app/static": {
				"type": "static",
				"dir":  "D:/workspace/static/"
			}, 
			"/app/proxy": {
				"type": "proxy",
				"proxyurl": "http://www.qq.com/"
			}
		}
	}

After setting config.json, just run:

    python web_server.py

*Note: this is just a coding practice, for learning about HTTP/wsgi, so don't using it for production.*