# This is an asynchronous task scheduler based on coroutines
import socket
import select
from collections import deque

class YieldPoint:
    def yield_task(self, task):
        pass
    def resume_task(self, task):
        pass
    
class Scheduler:
    def __init__(self):
        self.task_cnt = 0
        self.tasks = deque()
        self.write_wait_tasks = {}
        self.read_wait_tasks = {}

    def wait_for_write(self, fileno, event, task):
        self.write_wait_tasks[fileno] = (event, task)

    def wait_for_read(self, fileno, event, task):
        self.read_wait_tasks[fileno] = (event, task)

    def new_task(self, task):
        self.tasks.append((task, None))
        self.task_cnt += 1
        print "%d tasks"%self.task_cnt

    def add_task_back(self, task, data):
        self.tasks.append((task, data))

    def _poll(self):
        r, w, x = select.select(self.read_wait_tasks, self.write_wait_tasks, [])
        for r_id in r:
            e, task = self.read_wait_tasks.pop(r_id)
            e.resume_task(task)
        for w_id in w:
            e, task = self.write_wait_tasks.pop(w_id)
            e.resume_task(task)

    def run(self):
        while self.task_cnt:
            if not self.tasks:
                self._poll()
            task, data = self.tasks.popleft()
            try:
                event = task.send(data)
                if not isinstance(event, YieldPoint):
                    raise Exception("Task must yield YieldPoint")
                event.yield_task(task)
            except StopIteration:
                self.task_cnt -= 1
                print "%d tasks"%self.task_cnt

# A echo server is implemented as an example
sched = Scheduler()
class ListenYieldPoint(YieldPoint):
    def __init__(self, sock):
        self.sock = sock        
    def yield_task(self, task):
        sched.wait_for_read(self.sock, self, task)
    def resume_task(self, task):
        s, _ = self.sock.accept()
        sched.add_task_back(task, s)

class RecvYieldPoint(YieldPoint):
    def __init__(self, sock):
        self.sock = sock        
    def yield_task(self, task):
        sched.wait_for_read(self.sock, self, task)
    def resume_task(self, task):
        data = self.sock.recv(128)
        sched.add_task_back(task, data)

class SendYieldPoint(YieldPoint):
    def __init__(self, sock, data):
        self.sock = sock
        self.data = data
    def yield_task(self, task):
        sched.wait_for_write(self.sock, self, task)
    def resume_task(self, task):
        sent = self.sock.send(self.data)
        sched.add_task_back(task, sent)
        
def listener(cnt=5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 5555))
    i = 0
    while i<cnt:
        sock.listen(5)
        new_sock = yield ListenYieldPoint(sock)
        print "Accepting Client %d"%i
        sched.new_task(handler(new_sock))
        i += 1
    
def handler(sock):
    received = yield RecvYieldPoint(sock)
    print "RECV:"+received
    sent = yield SendYieldPoint(sock, received)
    print "SENT:" + str(sent)
    sock.close()

sched.new_task(listener())
sched.run()

        
        
