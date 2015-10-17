"""
This is my implementaion of the classic vi editor
The plan is to support only the very basic functionality and commands
"""
import curses
import curses.ascii
import sys
import copy
import signal

class EditOp(object):
    """Edit operation:
        * edit_type: insert/delete/replace
        * object_type: char/line
        * cnt: the number of objects operated on
        * pos: the position when the operation happened
        * value: could be chars/single line/lines
        * replacement: only used by replace ops
        * backwards: boolean, true for delete command with backspace
    """
    def __init__(self, editor, etype, otype, pos):
        self.editor = editor
        self.edit_type = etype
        self.object_type = otype
        self.pos = pos
        self.cnt = 0
        self.value = ""
        self.backwards = False

    def reverse(self):
        reverse_op = copy.copy(self)
        if self.edit_type == "insert":
            reverse_op.edit_type = "delete"
        elif self.edit_type == "delete":
            reverse_op.edit_type = "insert"
        else: # replace, just swap value and replacement
            reverse_op.value = self.replacement
            reverse_op.replacement = self.value
        reverse_op.apply()

    def apply(self):
        _buffer = self.editor.buffer
        y, x = self.pos
        if self.object_type == "char":
            if self.edit_type == "delete":
                if "\n" in self.value:
                    segments = self.value.split("\n")
                    if y<len(_buffer)-1:
                        _buffer[y] = _buffer[y][:x]+_buffer[y+1][len(segments[1]):]
                        del _buffer[y+1]
                    else:
                        _buffer[y] = _buffer[y][:x]
                else:
                    _buffer[y] = _buffer[y][:x]+_buffer[y][x+self.cnt:]
            elif self.edit_type == "insert":
                if "\n" in self.value:
                    segments = self.value.split("\n")
                    oldline = _buffer[y]
                    _buffer[y] = oldline[:x]+segments[0]
                    _buffer.insert(y+1, segments[1]+oldline[x:])
                else:
                    _buffer[y] = _buffer[y][:x] + self.value + _buffer[y][x:]
            else:
                # TODO: need to handle carriage return
                _buffer[y] = _buffer[y][:x] + self.replacement + _buffer[y][x+len(self.value):]
        else: #line
            if self.edit_type == "delete":
                del _buffer[y:y+self.cnt]
            elif self.edit_type =="insert":
                _buffer.insert(y, self.value)
            else:
                del _buffer[y:y+len(self.value)]
                _buffer.insert(y, self.replacement)
        # after apply, editor should refresh view

    def append_edit(self, char):
        self.cnt += len(char)
        self.value += char

class EditList(object):
    def __init__(self, editor):
        self.editor = editor
        self.edits = []
        self.cursor = -1

    def get_pos(self):
        if self.cursor<0:
            return None
        op = self.edits[self.cursor]
        return op.pos

    def undo(self):
        "When return False, editor should display Error in status line"
        if self.cursor < 0:
            return False
        op = self.edits[self.cursor]
        op.reverse()
        self.cursor -= 1 
        return True

    def redo(self):
        if self.cursor == len(self.edits)-1:
            return False
        self.cursor += 1
        op = self.edits[self.cursor]
        op.apply()
        return True

    def repeat(self):
        if self.cursor<0:
            return False
        # First remove the ops after cursor
        del self.edits[self.cursor+1:]
        new_op = copy.copy(self.edits[self.cursor])
        # the op should be applied at current position
        new_op.pos = self.editor.pos
        new_op.apply()
        self.edits.append(new_op)
        self.cursor += 1
        return True

    def commitEdit(self, op):
        del self.edits[self.cursor+1:]
        # for backward delete, correct the pos and value
        if op.backwards:
            op.value = op.value[::-1]
            op.pos = op.pos-len(op.value)
        # The editop should have been applied before commit
        self.edits.append(op)
        self.cursor += 1

class Editor(object):
    def __init__(self, f, buf):
        self.outfile = f
        self.buffer = buf
        self.editop = None
        self.editlist = EditList(self)
        self.config = {
            "expandtab": True,
            "tabspaces": 4,
        }

    def main_loop(self, stdscr):        
        self.scr = stdscr
        self.maxy, self.maxx = stdscr.getmaxyx()

        # This is the model part of MVC
        self.topline = 0
        self.line_heights = []
        self.mode = "command"
        self.command_editing = False
        self.pos = (0,0) # line and column of buffer
        self.partial = ""
        self.status_line = "-- COMMAND --"
        # render the initial screen
        self.refresh()
        self.refresh_command_line()
        self.refresh_cursor()
        while True:
            ch = self.scr.getch()
            if not self.do_command(ch):
                break

    def commit_current_edit(self):
        if self.editop:
            self.editlist.commitEdit(self.editop)
            self.editop = None

    def start_new_char_edit(self, etype, pos):
        # check if old edit is committed
        if self.editop:
            self.editlist.commitEdit(self.editop)
        self.editop = EditOp(self, etype, "char", pos)

    def do_command(self, ch):
        if self.mode == "editing":
            self.handle_editing(ch)
        else:
            if self.command_editing:
                self.handle_editing_command(ch)
            else:
                self.handle_command(ch)
        return True

    def reindent_line(self, lineno):
        pass

    def parse_command_after_char(self, ch):
        # The tuple should be ordered by descending length, 
        # for a command, its suffix should always be after itself 
        chr_cmd_tuples = [
            ("dd", "delete_line"),
            ("i", "insert_mode"),
            ("o", "insert_line"),
            ("u", "undo"),
            (".", "repeat_edit"),
        ]
        chr_cmd_map = dict(chr_cmd_tuples)
        meta_cmd_map = {
            curses.ascii.DC2: "redo"
        }

        if curses.ascii.isprint(ch):
            self.partial += chr(ch)
            for t in chr_cmd_tuples:
                if self.partial.endswith(t[0]):
                    # reset the partial after find a command
                    self.partial = ""
                    return t[1]
        else:
            # when meet a meta command, clear the partial
            self.partial = ""
            if ch in meta_cmd_map:
                return meta_cmd_map[ch]
        return None

    def is_direction_char(self, ch):
        return (ch in (curses.KEY_DOWN, curses.KEY_UP, curses.KEY_LEFT, curses.KEY_RIGHT) 
            or (ch in (ord('h'), ord('j'), ord('k'), ord('l')) 
                and self.mode=="command" and not self.command_editing))

    def handle_command(self, ch):
        if self.is_direction_char(ch):
            self.handle_cursor_move(ch)
            return
        cmd = self.parse_command_after_char(ch)
        if not cmd: return
        if cmd == "insert_mode":
            self.mode = "editing"
            self.refresh_command_line()
        elif cmd == "insert_line":
            self.mode = "editing"
            self.buffer.insert(self.pos[0]+1, "")
            self.pos = (self.pos[0]+1, 0)
            self.refresh()
            self.refresh_cursor()
            self.refresh_command_line()
        elif cmd == "undo": # for undo
            pos = self.editlist.get_pos()
            if not self.editlist.undo():
                self.flash_status_line("--Already at the earliest edit--")
            else:
                self.pos = pos
                self.refresh()
                self.refresh_cursor()
        elif cmd=="redo": # Ctrl+R for redo
            if not self.editlist.redo():
                self.flash_status_line("--Already at the lastest edit--")
            else:
                self.pos = self.editlist.get_pos()
                self.refresh()
                self.refresh_cursor()
        elif cmd=="repeat_edit":
            if self.editlist.repeat():
                self.pos = self.editlist.get_pos()
                self.refresh()
                self.refresh_cursor()

    def handle_editing_command(self, ch):
        pass

    def handle_cursor_move(self, ch):
        # finish the last edit if exists
        self.commit_current_edit()
        y, x = self.pos
        # print y, x
        if ch in (curses.KEY_UP, ord('k')) and y > 0:
            y = y-1
            x = min(x, len(self.buffer[y]))
            self.pos = (y, x)
            if y<self.topline:
                self.topline -= 1
                self.refresh()
            self.refresh_cursor()
        elif ch in (curses.KEY_DOWN, ord('j')) and y < len(self.buffer)-1:
            y = y + 1
            x = min(x, len(self.buffer[y]))
            self.pos = (y, x)
            in_screen = self.refresh_cursor()
            while not in_screen:
                self.topline += 1
                self.refresh()
                in_screen = self.refresh_cursor()
        elif ch in (curses.KEY_LEFT, ord('h')) and x>0:
            self.pos = (y, x-1)
            self.refresh_cursor()
        elif ch in (curses.KEY_RIGHT, ord('l')) and x<len(self.buffer[y]):
            self.pos = (y, x+1)
            in_screen = self.refresh_cursor()
            if not in_screen:
                self.topline += 1
                self.refresh()
                self.refresh_cursor()

    def handle_delete_char(self, ch):
        if (not self.editop or not self.editop.edit_type == "delete" 
            or (self.editop.backwards and ch==127) 
            or (not self.editop.backwards and ch==8)):
            self.start_new_char_edit("delete", self.pos)
            if ch==8: 
                self.editop.backwards = True
        y, x = self.pos
        if ch==127:
            if x == len(self.buffer[y]):
                if y < len(self.buffer)-1: 
                    # delete the \n at the end of a line
                    self.editop.append_edit("\n")
                    self.buffer[y] = self.buffer[y] + self.buffer[y+1]
                    del self.buffer[y+1]
                    self.commit_current_edit()
                # else, last line, last char, ignore
            else:
                char = self.buffer[y][x]
                self.editop.append_edit(char)
                self.buffer[y] = self.buffer[y][:x]+self.buffer[y][x+1:]
        else: # backspace
            if x==0:
                if y > 0:
                    self.editop.append_edit("\n")
                    lastlen = len(self.buffer[y-1])
                    self.buffer[y-1] = self.buffer[y-1] + self.buffer[y]
                    del self.buffer[y]
                    self.pos = y-1, lastlen
                    self.commit_current_edit()
            else:
                char = self.buffer[y][x-1]
                self.editop.append_edit(char)
                self.buffer[y] = self.buffer[y][:x-1]+self.buffer[y][x:]
                self.pos = y, x-1
        self.refresh()
        self.refresh_cursor()

    def handle_editing(self, ch):
        y, x = self.pos
        if curses.ascii.isprint(ch) or ch==ord("\n") or ch==ord("\t"):
            if not self.editop or not self.editop.edit_type == "insert":
                self.start_new_char_edit("insert", self.pos)
            if chr(ch)=="\t" and self.config["expandtab"]: # if expand tab into spaces
                spaces = " "*self.config["tabspaces"]
                self.editop.append_edit(spaces)
                self.buffer[y] = self.buffer[y][:x] + spaces + self.buffer[y][x:]
                self.pos = y, x+self.config["tabspaces"]
            else:
                self.editop.append_edit(chr(ch))
                if chr(ch)=="\n":
                    line = self.buffer[y]
                    self.buffer[y] = line[:x]
                    self.buffer.insert(y+1, line[x:])
                    self.pos = y+1, 0
                    # now adjust the indentation if needed
                    self.reindent_line(y+1)
                    self.start_new_char_edit("insert", self.pos)
                else:
                    self.buffer[y] = self.buffer[y][:x]+chr(ch)+self.buffer[y][x:]
                    self.pos = y, x+1
            self.refresh()
            self.refresh_cursor()
        elif ch==127 or ch==8: #DEL or BACKSPACE
            self.handle_delete_char(ch)
        elif self.is_direction_char(ch):
            self.handle_cursor_move(ch)
        elif ch==27: #ESC, to exit editing mode
            self.mode = "command"
            self.command_editing = False
            self.partial = ""
            self.status_line = "-- COMMAND --"
            # need to commit edit before switching mode
            self.commit_current_edit()
            self.refresh_command_line()
        return True

    # View part of MVC: screen rendering 
    def clear_scr_line(self, y):
        self.scr.move(y,0)
        self.scr.clrtoeol()

    def refresh_cursor(self):
        # move the cursor position based on self.pos
        screen_y = sum(self.line_heights[:self.pos[0]-self.topline])
        screen_y += self.pos[1]/self.maxx
        screen_x = self.pos[1]%self.maxx
        if screen_y >= self.maxy-1:
            return False
        self.scr.move(screen_y, screen_x)
        return True
    
    def flash_status_line(self, s):
        orig = self.status_line
        self.status_line = s
        self.refresh_command_line()
        def revert(signum, _frame):
            self.status_line = orig
            self.refresh_command_line()
        signal.signal(signal.SIGALRM, revert)
        signal.alarm(3)

    def refresh_command_line(self):
        _y, _x = self.scr.getyx()
        self.clear_scr_line(self.maxy-1)
        if self.mode=="editing":
            self.status_line = "-- INSERT --"
        self.scr.addstr(self.maxy-1,0, self.status_line)
        self.scr.move(_y, _x)

    def refresh(self):
        _y = 0
        self.line_heights = []
        for line in self.buffer[self.topline:]:
            singleline = line[:self.maxx]
            self.clear_scr_line(_y)
            self.scr.addstr(_y, 0, singleline)
            idx = self.maxx
            line_height = 1
            _y += 1
            while idx<len(line):
                singleline = line[idx:idx+self.maxx]
                self.clear_scr_line(_y)
                self.scr.addstr(_y, 0, singleline)
                idx += self.maxx
                _y+=1
                line_height += 1
                if _y >= self.maxy-1:
                    break
            self.line_heights.append(line_height)
            if _y >= self.maxy-1:
                break
        # fill the extra lines with ~
        while _y < self.maxy-1:
            self.clear_scr_line(_y)
            self.scr.addstr(_y,0,"~", curses.COLOR_RED)
            _y+=1
        # last line is reserved for commands
        # self.refresh_command_line()
        
def main():
    # parse the file argument if exists
    if len(sys.argv)==1:
        openfile = None
    elif len(sys.argv)==2:
        openfile = sys.argv[1]
    else:
        print "Only support opening one file for now"
        raise SystemExit()

    if openfile:    
        f = open(openfile, "r+")
        buf = f.readlines()
    else:
        f = None
        buf = [""]
    editor = Editor(f, buf)
    curses.wrapper(editor.main_loop)

if __name__ == "__main__":
    main() 
    

    
        
