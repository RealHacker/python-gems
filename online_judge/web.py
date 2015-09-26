import tornado
import tornado.web
import tornado.template
from problem import Problem
from judge import Judge
import json

class ProblemHandler(tornado.web.RequestHandler):
    def get(self, pid=1):
        p = Problem.get_problem_by_id(int(pid))
        if not p:
            # TODO: a 404 page
            self.write("404 - Problem not found.")
        else:
            loader = tornado.template.Loader("html")
            html = loader.load("page.html").generate(
                    _id=p._id,
                    title=p.title,
                    description= p.description,
                    method_name = p.method_name,
                    args = p.args
                )
            self.write(html)

    def post(self):
        try:
            payload = json.loads(self.request.body)
        except ValueError:
            raise
        if "id" not in payload or 'src' not in payload:
            raise Exception("Argument missing")
        pid = int(payload['id'])
        src = payload['src']
        judge = Judge(pid, src, mode="inline")
        ok, msg = judge.run_tests()
    
        if not ok:
            ret = json.dumps({"pass":False, "msg": msg})
        else:
            ret = json.dumps({"pass":True})
        self.set_header("content-type", "application/json")
        self.write(ret)

import tornado.wsgi
application = tornado.wsgi.WSGIApplication([
    (r"/", ProblemHandler),
])
#import sae
#application = sae.create_wsgi_app(app)

def debug():
    application = tornado.web.Application([
        (r"/", ProblemHandler),
        (r"/([0-9]+)/", ProblemHandler),
    ])
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    debug()
