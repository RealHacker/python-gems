# This is a LISP parser implemented in python,
# written after reading Peter Novig's lis.py essay http://www.norvig.com/lispy.html
def tokenize(program):
    return program.replace('(', '( ').replace(')', ' )').split()

def parse(program):
    tokens = tokenize(program)
    return get_next(tokens)

Symbol = str

def atom(token):
    try:
        return int(token)
    except:
        try:
            return float(token)
        except:
            return Symbol(token)
        
def get_next(tokens):
    token = tokens.pop(0)
    if token =='(':
        parsed = []
        while True:
            token = tokens[0]
            if token==')':
                tokens.pop(0)
                break
            else:
                parsed.append(get_next(tokens))
        return parsed
    elif token==")":
        raise Exception("Syntax Error")
    else:
        return atom(token)

class Env(dict):
    def __init__(self, parent={}):
        dict.__init__(self)
        self.parent = parent
    def __getitem__(self, name):
        if name in self:
            return dict.__getitem__(self, name)
        if name in self.parent:
            return self.parent[name]
        raise KeyError

global_env = Env()
import operator as op
global_env.update({
    '+':op.add, '-':op.sub, '*':op.mul, '/':op.div, 
    '>':op.gt, '<':op.lt, '>=':op.ge, '<=':op.le, '=':op.eq, 
    'abs':     abs,
})

class Proc(object):
    def __init__(self, args, exp, env):
        self.args = args
        self.exp = exp
        self.env = Env(env)
    def __call__(self, *arguments):
        for n, v in zip(self.args, arguments):
            self.env[n] = v
        return eval(self.exp, self.env)
    
def eval(exp, env = global_env):
    if isinstance(exp, basestring):
        return env[exp]
    elif isinstance(exp, (int, float)):
        return exp
    elif isinstance(exp, list):
        head = exp[0]
        if head=="define":
            _, name, val = exp
            env[name] = eval(val, env)
        elif head=="set!":
            _, name, val = exp
            if name not in env:
                raise Exception("Undefined")
            env[name] = eval(val, env)
        elif head=="quote":
            return exp[1]
        elif head=="if":
            test = eval(exp[1], env)
            if test:
                return eval(exp[2], env)
            else:
                return eval(exp[3], env)
        elif head=="lambda":
            return Proc(exp[1], exp[2], env)
        else:
            proc = env[head]
            return proc(*[eval(arg, env) for arg in exp[1:]])

def repl():
    while True:
        program = raw_input("LISP > ")
        val = eval(parse(program))
        if val:
            print val

repl()
            
