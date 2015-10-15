import curses
import curses.ascii
import sys
import copy

# helpers
def is_direction_char(ch):
    return ch in (curses.KEY_DOWN, curses.KEY_UP, curses.KEY_LEFT, curses.KEY_RIGHT)

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
                _buffer[y] = _buffer[y][:x]+_buffer[y][x+self.cnt:]
            elif self.edit_type == "insert":
                _buffer[y] = _buffer[y][:x] + self.value + _buffer[y][x:]
            else:
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
        self.cnt += 1
        self.value += chr(char)

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

    def main_loop(self, stdscr):        
        self.scr = stdscr
        self.maxy, self.maxx = stdscr.getmaxyx()
        self.topline = 0
        self.line_heights = []
        self.mode = "editing"
        self.command_editing = False
        self.pos = (0,0) # line and column of buffer

        self.refresh()
        while True:
            ch = self.scr.getch()
            if not self.do_command(ch):
                break

    def start_new_char_edit(self, etype, pos):
        # check if old edit is committed
        if self.editop:
            self.editlist.commitEdit(self.editop)
        self.editop = EditOp(self, etype, "char", pos)

    def do_command(self, ch):
        if curses.ascii.isprint(ch):
            if not self.editop or not self.editop.edit_type == "insert":
                self.start_new_char_edit("insert", self.pos)
            self.editop.append_edit(ch)
            y, x = self.pos
            self.buffer[y] = self.buffer[y][:x]+chr(ch)+self.buffer[y][x:]
            self.refresh()
            self.pos = y, x+1
            self.refresh_cursor()
        elif is_direction_char(ch):
            # finish the last edit if exists
            if self.editop:
                self.editlist.commitEdit(self.editop)
                self.editop = None
            y, x = self.pos
            # print y, x
            if ch==curses.KEY_UP and y > 0:
                y = y-1
                x = min(x, len(self.buffer[y])-1)
                self.pos = (y, x)
                if y<self.topline:
                    self.topline -= 1
                    self.refresh()
                self.refresh_cursor()
            elif ch==curses.KEY_DOWN and y < len(self.buffer)-1:
                y = y + 1
                x = min(x, len(self.buffer[y])-1)
                self.pos = (y, x)
                in_screen = self.refresh_cursor()
                while not in_screen:
                    self.topline += 1
                    self.refresh()
                    in_screen = self.refresh_cursor()
            elif ch==curses.KEY_LEFT and x>0:
                self.pos = (y, x-1)
                self.refresh_cursor()
            elif ch==curses.KEY_RIGHT and x<len(self.buffer[y])-1:
                self.pos = (y, x+1)
                in_screen = self.refresh_cursor()
                if not in_screen:
                    self.topline += 1
                    self.refresh()
                    self.refresh_cursor()
        elif ch==curses.ascii.NAK: # Ctrl+Z for undo
            if self.editop:
                self.editlist.commitEdit(self.editop)
                self.editop = None
            pos = self.editlist.get_pos()
            if not self.editlist.undo():
                self.scr.addstr(self.maxy-1,0, "--Already at the earliest edit--")
            else:
                self.pos = pos
                self.refresh()
                self.refresh_cursor()
        elif ch==curses.ascii.DC2: # Ctrl+Y for redo
            if self.editop:
                self.editlist.commitEdit(self.editop)
                self.editop = None
            if not self.editlist.redo():
                self.scr.addstr(self.maxy-1,0, "--Already at the lastest edit--")
            else:
                self.pos = self.editlist.get_pos()
                self.refresh()
                self.refresh_cursor()
        return True

    def refresh_cursor(self):
        # move the cursor position based on self.pos
        screen_y = sum(self.line_heights[:self.pos[0]-self.topline])
        screen_y += self.pos[1]/self.maxx
        screen_x = self.pos[1]%self.maxx
        if screen_y >= self.maxy-1:
            return False
        self.scr.move(screen_y, screen_x)
        return True
            
    def refresh_command_line(self):
        if self.mode=="editing":
            self.scr.addstr(self.maxy-1,0, "-- INSERT --")
        else:
            if not self.command_editing:
                self.scr.addstr(self.maxy-1, 0, " "*self.maxx)
        
    def refresh(self):
        _y = 0
        self.line_heights = []
        for line in self.buffer[self.topline:]:
            idx = 0
            line_height = 0
            while idx<len(line):
                singleline = line[idx:idx+self.maxx]
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
            self.scr.addstr(_y,0,"~", curses.COLOR_RED)
            _y+=1
        # last line is reserved for commands
        self.refresh_command_line()
        
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
    

    
        
