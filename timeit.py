# This is an implementation of timeit module, as a practice
import itertools
import gc

_template = """
def run_timer(it, _timer):
    %s
    _start = _timer.time()
    for _i in it:
        %s
    _end = _timer.time()
    return _end - _start
"""

def get_runner(f, _setup):
    def run_timer(it, _timer):
        _setup()
        _start = _timer.time()
        for _i in it:
            f()
        _end = _timer.time()
        return _end - _start
    return run_timer
    
class Timer(object):
    def __init__(self, target="pass", setup="pass"):
        self._target = target
        self._setup = setup
        ns = {}
        if isinstance(target, basestring):
            if isinstance(setup, basestring):
                src = _template%(setup, target)
            elif callable(setup):
                src = _template%("_setup()", target)
                ns["_setup"] = setup
            else:
                raise ValueError("Needs a callable or python statement")
            # print src
            code = compile(src, "_dummy_", "exec")
            exec code in globals(), ns
            self.runner = ns['run_timer']
        elif callable(target):
            if isinstance(setup, basestring):
                def temp():
                    exec setup in globals(), ns
                self.runner = get_runner(target, temp)
            elif callable(setup):
                self.runner = get_runner(target, setup)
        else:
            raise ValueError("target must be statement for callable")
        
    def timeit(self, times):
        import time
        it = itertools.repeat(None, times)
        gc_on = gc.isenabled()
        gc.disable()
        try:
            duration = self.runner(it, time)
        finally:
            if gc_on:
                gc.enable()
        return duration

    def repeat(self, cycles, times):
        t = []
        for i in xrange(cycles):
            tt = self.timeit(times)
            t.append(tt)
        return t

def timeit(target, setup, times):
    timer = Timer(target, setup)
    return timer.timeit(times)

def repeat(target, setup, times, cycles):
    timer = Timer(target, setup)
    return timer.repeat(cycles, times)


def main():
    stmt1 = "a = 2+4"
    stmt2 = "test(1)"
    setup2 = "test = lambda x:x*2"
    def test_func():
        global x
        x = x*2

    timer = Timer(stmt1)
    print stmt1, timer.timeit(100000)

    timer = Timer(stmt2, setup2)
    print stmt2, timer.timeit(10000)

    timer = Timer(test_func, "global x;x=1")
    print "func1", timer.timeit(10000)

    print "func2", timeit("i,j=m, n", "m=1;n=2", 10000) 

if __name__=="__main__":
    main()
    
        
        
        
