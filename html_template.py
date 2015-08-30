"""
An attempt to implement a HTML template engine like Django template/Jinja2
Supporting basic constructs:
1. variable {{variable}}
2. loop {% for val in vals %}... {% endfor %}
3. conditional {% if exp %} {% else %} {% endif %}
4. function call {% call funtion_name(arguments) %}
"""
import re, collections

class Context(object):
    def __init__(self, context):
        self.context_stack = [context]

    def __contains__(self, val):
        for ctx in self.context_stack:
            if val in ctx:
                return True
        return False

    def push_context(self, context):
        self.context_stack.append(context)

    def pop_context(self):
        self.context_stack.pop()

    def __getitem__(self, varname):
        for c in reversed(self.context_stack):
            if varname in c:
                return c[varname]
        return None
        
class Template(object):
    SEG_REGEX = re.compile(r"({{.*?}}|{%.*?%})")
    LOOP_REGEX = re.compile(r"for[\s+]([^\s]*)[\s+]in[\s+](.*)$")
    COND_REGEX = re.compile(r"if[\s+](.*)")
    CALL_REGEX = re.compile(r"call[\s+]([a-zA-Z0-9_]+)\((.*)\)")
    
    def __init__(self, template_str):
        self.template = template_str
         
    def _tokenize(self):
        self.tokens = self.SEG_REGEX.split(self.template)

    def compile(self):
        self._tokenize()
        self.nodes = []
        while self.tokens:
            node = self._get_next_node()
            self.nodes.append(node)
            
    def _get_next_node(self):
        if not self.tokens:
            raise Exception("The template string is invalid")
        token = self.tokens.pop(0)
        if token.startswith("{{"):
            # this is a var
            varname = token[2:-2].strip()
            varnode = VarNode(varname)
            return varnode
        elif token.startswith("{%"):
            # this is a block 
            inner = token[2:-2].strip()
            # is it a loop node?
            loop_match = self.LOOP_REGEX.match(inner)
            if loop_match:
                loop_var = loop_match.group(1)
                loop_list = loop_match.group(2)
                loopnode = LoopNode(loop_var, loop_list)
                children = []
                while True:
                    node = self._get_next_node()
                    if isinstance(node, EndLoopNode):
                        break
                    children.append(node)
                loopnode.children = children
                return loopnode
            # is it a conditional node?
            cond_match = self.COND_REGEX.match(inner)
            if cond_match:
                condnode = CondNode(cond_match.group(1))
                truenodes = []
                falsenodes = []
                in_list = truenodes
                while True:
                    node = self._get_next_node()
                    if isinstance(node, ElseNode):
                        in_list = falsenodes
                        continue
                    elif isinstance(node, EndIfNode):
                        break
                    in_list.append(node)
                condnode.true_children = truenodes
                condnode.false_children = falsenodes
                return condnode
            # is it a function call
            call_match = self.CALL_REGEX.match(inner)
            if call_match:
                fname = call_match.group(1)
                arguments = [arg.strip() for arg in call_match.group(2).split(",")]
                callnode = CallNode(fname, arguments)
                return callnode
            # Other sentinel nodes: ELSE ENDIF ENDFOR
            if inner.lower()=="else":
                return ElseNode()
            if inner.lower()=="endif":
                return EndIfNode()
            if inner.lower()=="endfor":
                return EndLoopNode()
        else:
            return TextNode(token)
                                                            
    def render(self, context):
        result_str = ""
        for node in self.nodes:
            result_str += node.render(context)
        return result_str
        
class Node(object):
    pass

class TextNode(Node):
    def __init__(self, text):
        self.text = text
    def render(self, context):
        return self.text
    
class VarNode(Node):
    def __init__(self, var):
        self.var = var
    
    def render(self, context):
        if self.var not in context:
            raise Exception("Var %s missing from context"%self.var)
        return str(context[self.var])

class LoopNode(Node):
    def __init__(self, loop_var, loop_list):
        self.loop_var = loop_var
        self.loop_list = loop_list
        self.children = []
        
    def render(self, context):
        result_str = ""
        if self.loop_list in context:
             _list = context[self.loop_list]
        else:
             _list = eval(self.loop_list,{},context)
        if not isinstance(_list, collections.Iterable):
            raise Exception("Var %s missing from context, or is not an iterable"%self.loop_list)
            
        # build in_loop context
        local_context = {
            "it":0,
            self.loop_var: None
        }
        context.push_context(local_context)
        for i, x in enumerate(_list):
            local_context["it"] = i
            local_context[self.loop_var] = x
            for child in self.children:
                result_str += child.render(context)
                
        context.pop_context()
        return result_str
        
class CondNode(Node):
    def __init__(self, exp):
        self.exp = exp
        self.true_children = []
        self.false_children = []

    def render(self, context):
        cond = eval(self.exp, {}, context)
        result_str = ""
        if cond:
            children = self.true_children
        else:
            children = self.false_children
        for child in children:
            result_str += child.render(context)
        return result_str
        
class CallNode(Node):
    def __init__(self, fname, args):
        self.fname = fname
        self.args = args
    def render(self, context):
        if self.fname not in context or not callable(context[self.fname]):
            raise Exception("Var %s missing from context, or not callable"%self.fname)
        arguments = [eval(arg, {}, context) for arg in self.args]
        result = context[self.fname](*arguments)
        return str(result)
            
# Sentinels
class EndLoopNode(Node):
    pass

class ElseNode(Node):
    pass

class EndIfNode(Node):
    pass


def render_string_template(template_str, context):
    tpl = Template(template_str)
    tpl.compile()
    
    ctx = Context(context)
    return tpl.render(ctx)

def test():
    rendered = render_string_template('{% for item in items %}<div>{{it}}: {{item}}</div>{% endfor %}', {"items":["abc", "xyz"]})
    print rendered
    rendered = render_string_template('{% for i in [1, 2, 3] %}<div>{{name}}-{{it}}-{{i}}</div>{% endfor %}', {"name":"Jon Snow"})
    print rendered
    rendered = render_string_template('{% if num > 5 %}<div>more than 5</div>{% endif %}', {"num": 6})
    print rendered
    rendered = render_string_template('{% if num > 5 %}<div>more than 5</div>{% else %}<div>less than 5</div>{% endif %}', {"num":2})
    print rendered
    def pow(m=2, e=2):
        return m ** e
    rendered = render_string_template('{% call pow(2, x) %}', {"pow":pow, "x": 4})
    print rendered

if __name__=="__main__":
    test()
    
    
