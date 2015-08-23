"""A very very simple go REPL"""
import subprocess
import tempfile

src_template = """
package main
{imports}
{variables}
{types}
{funcs}

func main(){{
    {mains}
}}
"""

class ParsingError(Exception):
    def __init__(self, msg):
        super(ParsingError, self).__init__(self, msg)
        self.msg = msg
        
class Session(object):
    PROMPT = ">>> "
    CONT = "... "
    metachars = "()[]{}`\"'"
    pairs = {
        "(":")",
        "[":"]",
        "{":"}",
        "`":"`",
        "\"":"\"",
        "'":"'"
    }
    def __init__(self):
        self._reset()
        
    def _reset(self):
        self.imports = []
        self.variables = []
        self.types = []
        self.funcs = []
        self.mains = []
        self.old_stdout = None
        self.stdout = None
        self._reset_buffer()

    def _reset_buffer(self):
        self.pair_stack = []
        self.statement = ""
        self.current_line = ""
        self.is_complete = True
        
    def handle_statement(self):
        _target = self.statement.strip()
        if _target.startswith("!"):
            self.handle_command(_target)
        elif _target.startswith("import "):
            self.imports.append(_target)
        elif "var " in _target or "const " in _target:
            # By default, we put all vars and consts in global scope
            # So that funcs can use them
            self.variables.append(_target)
        elif "type " in _target:
            self.types.append(_target)
        elif _target.startswith("func"):
            self.funcs.append(_target)
        else:
            self.mains.append(_target)
            if ":=" not in _target:
                self.run()

    def check_if_complete(self):
        # Very simplistic syntax check to determine:
        # 1 .If current statement is complete (all pairs closed)
        # 2. If there is syntax error in current line, raise
        # Checks:
        # 1. () [] {} "" '' `` should all be in pairs
        # 2. unless they are within "" or ``
        # 3. [] "" '' have to be closed in the same line
        for c in self.current_line:
            if c not in self.metachars:
                continue
            if self.pair_stack:
                stacktop = self.pair_stack[-1]
                # First check if c is closing something
                if c in self.pairs.values():                
                    if c == self.pairs[stacktop]:
                        del self.pair_stack[-1]
                        continue
                    elif c in "}])" and stacktop not in ["`", "\""]:
                        raise ParsingError("'%s' closed at wrong placse"%c)
                # Check if need to push to stack
                if stacktop in ["`", "\""]:
                    continue
                self.pair_stack.append(c)
            elif c in self.pairs:
                self.pair_stack.append(c)
            else:
                raise ParsingError("%s appears at wrong place"%c)
            
        self.is_complete = not self.pair_stack
        if self.is_complete:
            return True
        else:
            if self.pair_stack[-1] in "[\"'":
                raise ParsingError("%s have to be closed in the same line"%self.pair_stack[-1])

    def render_src(self):
        return src_template.format(
            imports = '\n'.join(self.imports),
            variables = '\n'.join(self.variables),
            types = '\n'.join(self.types),
            funcs = '\n'.join(self.funcs),
            mains = '\n'.join(self.mains)
        )
    
    def run(self):
        # generate the program source
        program = self.render_src()
        # write to temparory file
        f = tempfile.NamedTemporaryFile(suffix=".go", delete=False)
        f.write(program)
        f.flush()
        f.close()
        # Now go run
        gorun = subprocess.Popen(["go", "run", f.name],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
        stdout, stderr = gorun.communicate()
        if stdout:
            self.old_stdout = self.stdout
            self.stdout = stdout
            # Only show the diff 
            if not self.old_stdout:
                print self.stdout
            else:
                index = self.stdout.find(self.old_stdout)
                if index >=0:
                    print self.stdout[index+len(self.old_stdout):]
                else:
                    print self.stdout
        if stderr:
            # If error happens, remove the last statement in mains
            print stderr
            del self.mains[-1]

    def handle_command(self, command):
        command = command.strip()[1:]
        if command == "clear":
            self._reset()
            print "Starting afresh ..."
        elif command == "help":
            self.show_help()
        elif command == "exit":
            raise SystemExit()
        elif command == "src":
            print self.render_src()
        elif command == "history":
            if self.mains:
                for i, stmt in enumerate(self.mains):
                    print i+1, "\t", stmt
                print "Use !del <num> command to delete a statement from source"
        elif command.startswith("del"):
            segments = command.split()
            if len(segments)<2:
                print "!del should be followed by one or more index numbers"
            try:
                indice = reversed(sorted([int(seg) for seg in segments[1:]]))
            except:
                print "Some index numbers are invalid"
            else:
                for idx in indice:
                    if idx > len(self.mains) or idx <= 0:
                        print "Some index numbers are out of range"
                        break
                    del self.mains[idx-1]
        else:
            print "Invalid command."

    def show_help(self):
        print "+++++++++COMMANDS++++++++++"
        print "!help\t\tPrint this help"
        print "!exit\t\tExit this REPL"
        print "!src\t\tPrint the current source code"
        print "!clear\t\tClear defined vars/funcs/types and start afresh"
        print "!history\tShow statement you entered (not including var/func definitions)"
        print "!del <num>\tDelete the <num> statement from source code"
        print "+++++++++++++++++++++++++++"
        
    def main_loop(self):
        self.show_help()
        print "Enter your Go statements Or command(start with !):"
        while True:
            line = raw_input(self.PROMPT)
            self.statement = line
            self.current_line = line
            try:
                self.check_if_complete()
            except ParsingError as e:
                print "[ERROR] - "+e.msg
                self._reset_buffer()
                continue
            if self.is_complete:
                self.handle_statement()
            else:
                try:
                    while True:
                        line = raw_input(self.CONT)
                        if not line and self.is_complete:
                            break
                        self.current_line = line
                        self.statement += "\n" + line
                        self.check_if_complete()
                except ParsingError as e:
                    print "[ERROR] "+e.msg
                    self._reset_buffer()
                    continue
                else:
                    self.handle_statement()
            
        
def main():
    Session().main_loop()

if __name__== "__main__":
    main()
            
    






