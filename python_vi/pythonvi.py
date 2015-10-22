"""
This is my implementaion of the classic vi editor
The plan is to support only the very basic functionality and commands
"""
import curses
import curses.ascii
import sys
import copy
import signal
import re
import string

debug = True
if debug:
    logfile = open("log.txt", "a")

def writelog(*argv):
    if debug:
        logline = " ".join(["%s"%arg for arg in argv])
        logfile.write(logline+"\n")

class LineBeyondScreenError(Exception):
    "Raised when the line or cursor is beyond the screen and needs scrolling"

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
                    _buffer[y] = _buffer[y][:x]+_buffer[y][x+len(self.value):]
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
        else: # line
            assert isinstance(self.value, list) # invariant
            if self.edit_type == "delete":
                del _buffer[y:y+len(self.value)]
            elif self.edit_type =="insert":
                for line in reversed(self.value):
                    _buffer.insert(y, line)
            else:
                del _buffer[y:y+len(self.value)]
                for line in reversed(self.replacement):
                    _buffer.insert(y, line)
        # after apply, editor should refresh view
    def append_edit(self, char):
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
            op.pos = op.pos[0], op.pos[1]-len(op.value)
        # The editop should have been applied before commit
        self.edits.append(op)
        self.cursor += 1

class ClipBoard(object):
    def __init__(self):
        self.type = "char" # either char or line
        self.value = ""
    def store(self, value):
        if isinstance(value, basestring):
            self.type = "char"
        else:
            self.type = "line"
        self.value = value
    def retrieve(self):
        return self.type, self.value

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
        self.screen_lines = 0
        self.mode = "command"
        self.command_editing = False
        self.pos = (0,0) # line and column of buffer
        self.partial = "" # partial cmd in command mode
        self.status_line = "-- COMMAND --"
        self.commandline = "" # command entered in command line at the bottom of screen
        self.checkpoint = -1 # pointer into the editlist where save happens
        self.searchpos = (0,0)
        self.searchkw = None
        self.searchdir = "forward"
        self.clipboard = ClipBoard()
        self.showlineno = False
        # render the initial screen
        self.refresh()
        self.refresh_command_line()
        self.refresh_cursor()
        while True:
            ch = self.scr.getch()
            if not self.do_command(ch):
                break

    @property
    def dirty(self):
        return self.editlist.cursor != self.checkpoint

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
            ("gg", "goto_first_line"),
            ("dw", "delete_word"),
            ("dW", "delete_term"),
            ("yw", "yank_word"),
            ("yW", "yank_term"),
            ("dd", "delete_line"),
            ("yy", "yank_line"),
            ("r", "replace_char"),
            ("i", "insert_mode"),
            ("I", "insert_line_start"),
            ("o", "insert_line_after"),
            ("O", "insert_line_before"),
            ("a", "insert_after"),
            ("A", "insert_line_end"),
            ("s", "delete_char_insert"),
            ("S", "delete_line_insert"),
            ("D", "delete_line_end"),
            ("u", "undo"),
            (".", "repeat_edit"),
            ("^", "goto_line_start"),
            ("0", "goto_line_start"),
            ("$", "goto_line_end"),
            ("-", "goto_prev_line_start"),
            ("+", "goto_next_line_start"),
            ("H", "goto_first_screen_line"),
            ("L", "goto_last_screen_line"),
            ("M", "goto_middle_screen_line"),
            ("G", ":goto_line"),
            ("w", "next_word_start"),
            ("W", "next_term_start"),
            ("e", "word_end"),
            ("E", "term_end"),
            ("b", "word_start"),
            ("B", "term_start"),
            (":", "command_edit_mode"),
            ("~", "switch_case"),
            ("x", "delete_char"),
            ("X", "delete_last_char"),
            ("%", "match_pair"),
            ("/", "search_mode"),
            ("?", "reverse_search_mode"),
            ("n", "search_next"),
            ("N", "search_previous"),
            ("Y", "yank_line"),
            ("p", "paste_after"),
            ("P", "paste_before"),
        ]
        chr_cmd_map = dict(chr_cmd_tuples)
        meta_cmd_map = {
            curses.ascii.DC2: "redo", # CTRL + R
            curses.ascii.ACK: "next_page", # CTRL + F
            curses.ascii.STX: "prev_page", # CTRL + B
            curses.ascii.ENQ: "scroll_down", # CTRL + E
            curses.ascii.EM: "scroll_up", # CTRL + Y
            curses.KEY_DC: "delete_char",
            curses.KEY_BACKSPACE: "backup_char",
            curses.KEY_HOME: "goto_line_start",
            curses.KEY_END: "goto_line_end",
            curses.KEY_PPAGE: "prev_page",
            curses.KEY_NPAGE:"next_page",
            127: "backup_char", # on Mac, backspace key doesn't map to curses.KEY_BACKSPACE
        }

        if curses.ascii.isprint(ch):
            self.partial += chr(ch)
            for t in chr_cmd_tuples:
                if self.partial.endswith(t[0]):
                    cmd = t[1]
                    if cmd.startswith(":"):
                        cmd = cmd[1:]
                        # meaning this command has a number before it
                        regex = re.compile(".*?([0-9]+)$") # non-greedy
                        mo = regex.match(self.partial[:-1])
                        self.partial = ""
                        if mo:
                            number = int(mo.group(1))
                            return (cmd, number)
                        else:
                            return cmd
                    elif cmd=="replace_char":
                        ch = self.scr.getch()
                        self.partial = ""
                        if curses.ascii.isprint(ch):
                            return (cmd, chr(ch))
                        else:
                            return None
                    else:
                        # reset the partial after find a command
                        self.partial = ""
                        return cmd
        else:
            # when meet a meta key, clear the partial command
            self.partial = ""
            if ch in meta_cmd_map:
                return meta_cmd_map[ch]
        return None

    def is_direction_char(self, ch):
        return (ch in (curses.KEY_DOWN, curses.KEY_UP, curses.KEY_LEFT, curses.KEY_RIGHT) 
            or (ch in (ord('h'), ord('j'), ord('k'), ord('l')) 
                and self.mode=="command" and not self.command_editing))

    def advance_word(self, s, idx, direction="forward"):
        wordchars = string.letters + string.digits + "_"
        if idx >= len(s) or idx <0: return idx
        step = 1 if direction=="forward" else -1
        if s[idx] in wordchars:
            while idx>=0 and idx < len(s) and s[idx] in wordchars : idx += step
        elif s[idx] == " ":
            while idx>=0 and idx < len(s) and s[idx] == " ": idx += step
        else:
            while id>=0 and idx < len(s) and s[idx] not in wordchars and s[idx] != " ": idx+=step
        return idx

    def advance_term(self, s, idx, direction="forward"):
        step = 1 if direction=="forward" else -1
        while idx>=0 and idx < len(s) and s[idx] != " ": idx +=step
        return idx

    def advance_spaces(self, s, idx, direction="forward"):
        step = 1 if direction=="forward" else -1
        while idx>=0 and idx < len(s) and s[idx]==" ": idx+=step
        return idx

    def advance_one_char(self, pos, direction="forward"):
        y, x = pos
        if direction=="forward":
            x = x+1
            if x >= len(self.buffer[y]):
                if y==len(self.buffer)-1:
                    return None
                else:
                    y+=1
                    while len(self.buffer[y])==0: y+=1
                    if y>=len(self.buffer): return None
                    else: return y, 0
            else:
                return y, x
        else:
            x = x - 1
            if x < 0:
                if y == 0:
                    return None
                else:
                    y -= 1
                    while len(self.buffer[y])==0: y-=1
                    if y<0: return None
                    else: return y, len(self.buffer[y])-1
            else:
                return y, x

    def handle_command(self, ch):
        if self.is_direction_char(ch):
            self.handle_cursor_move(ch)
            return
        cmd = self.parse_command_after_char(ch)
        if not cmd: return
        # if is a tuple, set the parameter
        if isinstance(cmd, tuple):
            parameter = cmd[1]            
            cmd = cmd[0]
        else:
            parameter = None
        ### commands for switching to editing mode ###
        if cmd == "insert_line_after":
            self.buffer.insert(self.pos[0]+1, "")
            self.pos = (self.pos[0]+1, 0)
            self.refresh()
            self.refresh_cursor()
        elif cmd == "insert_line_before":
            self.buffer.insert(self.pos[0], "")
            self.pos = (self.pos[0], 0)
            self.refresh()
            self.refresh_cursor()
        elif cmd == "insert_line_start":
            self.pos = (self.pos[0], 0)
            self.refresh_cursor()
        elif cmd == "insert_after":
            if self.buffer[self.pos[0]]:
                self.pos = (self.pos[0], self.pos[1]+1)
                self.refresh_cursor()
        elif cmd == "insert_line_end":
            self.pos = (self.pos[0], len(self.buffer[self.pos[0]]))
            self.refresh_cursor()
        elif cmd == "delete_char_insert":
            s = self.buffer[self.pos[0]]
            if s:
                char = s[self.pos[1]]
                s = s[:self.pos[1]]+s[self.pos[1]+1:]
                self.buffer[self.pos[0]] = s
                self.refresh()
                self.refresh_cursor()
                self.editop = EditOp(self, "delete", "char", self.pos)
                self.editop.value = char
                self.commit_current_edit()
        elif cmd == "delete_line_insert":
            s = self.buffer[self.pos[0]]
            if s:
                oldline = self.buffer[self.pos[0]]
                self.buffer[self.pos[0]] = ""
                self.pos = self.pos[0], 0
                self.refresh()
                self.refresh_cursor()
                self.editop = EditOp(self, "replace", "char", (self.pos[0], 0))
                self.editop.value = oldline
                self.editop.replacement = ""
                self.commit_current_edit()
        ### commands for moving cursor position ###
        elif cmd == "goto_line_start":
            self.pos = (self.pos[0], 0)
            self.refresh_cursor()
        elif cmd == "goto_line_end":
            self.pos = (self.pos[0], max(len(self.buffer[self.pos[0]])-1, 0))
            self.refresh_cursor()
        elif cmd == "goto_prev_line_start":
            if self.pos[0]>0:
                y, x = self.pos
                self.pos = (y-1, 0)
                self.refresh_cursor()
        elif cmd == "goto_next_line_start":
            if self.pos[0]<len(self.buffer)-1:
                y, x = self.pos
                self.pos = (y+1, 0)
                self.refresh_cursor()
        elif cmd == "goto_first_screen_line":
            self.pos = self.topline, 0
            self.refresh_cursor()
        elif cmd == "goto_last_screen_line":
            self.pos = self.topline +self.screen_lines-1, 0
            self.refresh_cursor()
        elif cmd == "goto_middle_screen_line":
            self.pos = self.topline + self.screen_lines/2, 0
            self.refresh_cursor()
        elif cmd == "next_page":
            if self.topline == len(self.buffer)-1: 
                return
            self.topline = self.topline + self.screen_lines -1
            self.refresh()
            self.pos = (self.topline, 0)
            self.refresh_cursor()
        elif cmd == "prev_page":
            if self.topline == 0:
                return
            # need to calculate how many line we need to scroll up
            idx = self.topline
            line_cnt = 0
            while idx>=0:
                line_cnt += len(self.buffer[idx])/self.maxx+1
                if line_cnt > self.maxy-1:
                    break
                idx -= 1
            idx = min(idx+1, self.topline)
            self.topline = idx
            self.refresh()
            self.pos = (self.topline + self.screen_lines-1, 0)
            self.refresh_cursor()
        elif cmd == "scroll_down":
            if self.topline == len(self.buffer)-1: 
                return
            self.topline = self.topline + 1
            self.refresh()
            if self.pos[0] < self.topline:
                # if the cursor is beyond top of screen, move cursor to topline, keep the x pos
                xpos = max(0, min(self.pos[1], len(self.buffer[self.topline])-1))
                self.pos = (self.topline, xpos)
            self.refresh_cursor()
        elif cmd == "scroll_up":
            if self.topline == 0:
                return
            self.topline = self.topline - 1
            self.refresh()
            # to make it simple, when cursor is beyond the bottom, move it to the start of last line
            if self.pos[0] >= self.topline+self.screen_lines-1:
                self.pos = (self.topline+self.screen_lines-1, 0)
            self.refresh_cursor()
        elif cmd=="goto_line" or cmd=="goto_first_line":
            if cmd=="goto_first_line":
                lineno = 0
            elif not parameter or parameter>len(self.buffer):
                # go to last line
                lineno = len(self.buffer)-1
            else:
                lineno = parameter-1
            self.topline = lineno
            self.refresh()
            self.pos = (lineno, 0)
            self.refresh_cursor()
        elif cmd == "next_word_start":
            s = self.buffer[self.pos[0]]
            idx = self.pos[1]
            idx = self.advance_word(s, idx)
            idx = self.advance_spaces(s, idx)
            if idx >= len(s):
                if self.pos[0] < len(self.buffer)-1:
                    self.pos = self.pos[0]+1, 0
            else:
                self.pos = self.pos[0], idx
            self.refresh_cursor()
        elif cmd == "next_term_start":
            s = self.buffer[self.pos[0]]
            idx = self.pos[1]
            idx = self.advance_term(s, idx)
            idx = self.advance_spaces(s, idx)
            if idx >= len(s):
                if self.pos[0] < len(self.buffer)-1:
                    self.pos = self.pos[0]+1, 0
            else:
                self.pos = self.pos[0], idx
            self.refresh_cursor()
        elif cmd == "word_end":
            s = self.buffer[self.pos[0]]
            idx = self.pos[1]+1
            if idx >= len(s):
                if self.pos[0] < len(self.buffer)-1:
                    self.pos = self.pos[0]+1, 0
                    s = self.buffer[self.pos[0]]
                    idx = 0
            idx = self.advance_word(s, idx)
            self.pos = self.pos[0], max(idx-1, 0)
            self.refresh_cursor()
        elif cmd == "term_end":
            s = self.buffer[self.pos[0]]
            idx = self.pos[1]+1
            if idx >= len(s):
                if self.pos[0] < len(self.buffer)-1:
                    self.pos = self.pos[0]+1, 0
                    s = self.buffer[self.pos[0]]
                    idx = 0
            idx = self.advance_spaces(s, idx)
            idx = self.advance_term(s, idx)
            self.pos = self.pos[0], max(idx-1, 0)
            self.refresh_cursor()
        elif cmd == "word_start":
            s = self.buffer[self.pos[0]]
            idx = self.pos[1]-1
            if idx < 0:
                if self.pos[0]>0:
                    # back up to last line and recurse
                    lineno = self.pos[0]-1
                    self.pos = lineno, len(self.buffer[lineno])
                    self.handle_command(ch) 
                return
            if s[idx] == " ":
                idx = self.advance_spaces(s, idx, "backwards")
            # this is duplicate code, need a way to dedup
            if idx < 0:
                if self.pos[0]>0:
                    # back up to last line and recurse
                    lineno = self.pos[0]-1
                    self.pos = lineno, len(self.buffer[lineno])
                    self.handle_command(ch) 
                return
            idx = self.advance_word(s, idx, "backwards")
            self.pos = self.pos[0], idx+1
            self.refresh_cursor()
        elif cmd == "term_start": 
            s = self.buffer[self.pos[0]]
            idx = self.pos[1]-1
            if idx < 0:
                if self.pos[0]>0:
                    # back up to last line and recurse
                    lineno = self.pos[0]-1
                    self.pos = lineno, len(self.buffer[lineno])
                    self.handle_command(ch) 
                return
            if s[idx] == " ":
                idx = self.advance_spaces(s, idx, "backwards")
            # this is duplicate code, need a way to dedup
            if idx < 0:
                if self.pos[0]>0:
                    # back up to last line and recurse
                    lineno = self.pos[0]-1
                    self.pos = lineno, len(self.buffer[lineno])-1
                    self.handle_command(ch) 
                return
            idx = self.advance_term(s, idx, "backwards")
            self.pos = self.pos[0], idx+1
            self.refresh_cursor()
        elif cmd == "backup_char":
            self.pos = self.pos[0], max(self.pos[1]-1,0)
            self.refresh_cursor()
        ### commands for managing edits history ###
        elif cmd == "undo": # for undo
            pos = self.editlist.get_pos()
            if not self.editlist.undo():
                self.flash_status_line("-- Already at the first edit --")
            else:
                self.pos = pos
                self.refresh()
                self.refresh_cursor()
        elif cmd=="redo": # Ctrl+R for redo
            if not self.editlist.redo():
                self.flash_status_line("-- Already at the last edit --")
            else:
                self.pos = self.editlist.get_pos()
                self.refresh()
                self.refresh_cursor()
        elif cmd=="repeat_edit":
            if self.editlist.repeat():
                self.pos = self.editlist.get_pos()
                self.refresh()
                self.refresh_cursor()
        ### commands for entering command editing mode (Ex mode) ###
        elif cmd in ("command_edit_mode", "search_mode", "reverse_search_mode"):
            self.command_editing = True
            self.commandline = chr(ch)
            self.refresh_command_line()
        ### edit commands ###
        elif cmd == "switch_case":
            line = self.buffer[self.pos[0]]
            ch = line[self.pos[1]]
            if ch in string.letters:
                line = line[:self.pos[1]]+ch.swapcase()+line[self.pos[1]+1:]
                self.buffer[self.pos[0]] = line
                self.refresh()
                # add edit operation to list
                self.editop = EditOp(self, "replace", "char", self.pos)
                self.editop.value = ch
                self.editop.replacement = ch.swapcase()
                self.commit_current_edit()
            if self.pos[1]<len(line)-1:
                self.pos = self.pos[0], self.pos[1]+1
            self.refresh_cursor()
        elif cmd in ("delete_char", "delete_last_char"):
            self.handle_delete_char(ch)
        elif cmd in ("delete_word", "yank_word"):
            s = self.buffer[self.pos[0]]
            idx = self.pos[1]
            idx = self.advance_word(s, idx)
            idx = self.advance_spaces(s, idx)
            if cmd =="delete_word":
                self.buffer[self.pos[0]] = s[:self.pos[1]]+s[idx:]
                self.refresh()
            if self.pos[1]<idx:
                deleted = s[self.pos[1]:idx]
                self.clipboard.store(deleted)
                if cmd =="delete_word":
                    self.start_new_char_edit("delete", self.pos)
                    self.editop.append_edit(deleted)
                    self.commit_current_edit()
            if cmd =="delete_word":
                if self.pos[1] >= len(s): 
                    newx = self.pos[1]-1
                else:
                    newx = self.pos[1]
                self.pos = self.pos[0], max(newx, 0)
            self.refresh_cursor()
        elif cmd in ("delete_term", "yank_term"):
            s = self.buffer[self.pos[0]]
            idx = self.pos[1]
            idx = self.advance_term(s, idx)
            idx = self.advance_spaces(s, idx)
            if cmd =="delete_term":
                self.buffer[self.pos[0]] = s[:self.pos[1]]+s[idx:]
                self.refresh()
            if self.pos[1]<idx:
                deleted = s[self.pos[1]:idx]
                self.clipboard.store(deleted)
                if cmd =="delete_term":
                    self.start_new_char_edit("delete", self.pos)
                    self.editop.append_edit(deleted)
                    self.commit_current_edit()
            if cmd =="delete_term":
                if idx >= len(s): 
                    newx = self.pos[1]-1
                else:
                    newx = self.pos[1]
                self.pos = self.pos[0], max(newx, 0)
            self.refresh_cursor()
        elif cmd == "delete_line":
            if not len(self.buffer) or (len(self.buffer)==1 and not self.buffer[0]): return
            oldline = self.buffer[self.pos[0]]
            self.clipboard.store([oldline]) # deleted lines are stored in clipboard
            del self.buffer[self.pos[0]]
            if not self.buffer: # should preserve at least one blank line
                self.buffer =[""]
                self.editop = EditOp(self, "replace", "line", self.pos)
                self.editop.replacement = [""]
            else:
                self.editop = EditOp(self, "delete", "line", self.pos)
            self.editop.value = [oldline]
            self.commit_current_edit()
            self.refresh()
            if self.pos[0] >= len(self.buffer):
                y = len(self.buffer)-1
            else:
                y = self.pos[0]
            x = min(self.pos[1], len(self.buffer[y])-1)
            self.pos = y, max(x, 0)
            self.refresh_cursor()
        elif cmd == "delete_line_end":
            s = self.buffer[self.pos[0]]
            if s:
                oldpos = self.pos
                deleted = s[self.pos[1]:]
                self.buffer[self.pos[0]] = s[:self.pos[1]]
                self.pos = self.pos[0], max(self.pos[1]-1, 0)
                self.refresh()
                self.refresh_cursor()
                self.clipboard.store(deleted)
                self.editop = EditOp(self, "delete", "char", oldpos)
                self.editop.value = deleted
                self.commit_current_edit()
        elif cmd == "replace_char":
            line = self.buffer[self.pos[0]]
            oldchar = line[self.pos[1]]
            line = line[:self.pos[1]]+parameter+line[self.pos[1]+1:]
            self.buffer[self.pos[0]] = line
            self.refresh()
            self.refresh_cursor()
            # add replace operation
            self.editop = EditOp(self, "replace", "char", self.pos)
            self.editop.value = oldchar
            self.editop.replacement = parameter
            self.commit_current_edit()
        ### search related commands ###
        elif cmd == "match_pair":
            chrs = "()[]{}"
            matcher = {"(":")", ")":"(", "[":"]", "]":"[","{":"}", "}":"{"}
            char = self.buffer[self.pos[0]][self.pos[1]]
            if char not in chrs: return
            if char in "([{":
                direction = "forward"
            else:
                direction = "backward"
            pos = self.pos
            depth = 1
            while True:
                pos = self.advance_one_char(pos, direction)
                # import pdb;pdb.set_trace()
                if not pos:
                    self.flash_status_line("--No matching symbol found--")
                    break
                current = self.buffer[pos[0]][pos[1]]
                if current == char: depth+=1
                elif current == matcher[char]: 
                    depth -=1
                    if depth == 0:
                        self.pos = pos
                        self.refresh_cursor()
                        break
        elif cmd in ("search_next", "search_previous"):
            if cmd=="search_next":
                direction = self.searchdir 
            else:
                direction = "forward" if self.searchdir == "backward" else "backward"
            pos = self.search_for_keyword(direction)
            if not pos:
                self.flash_status_line("--Search pattern not found--")
                return
            self.pos = pos
            self.refresh_cursor()
        ### copy paste commands ###
        elif cmd == "yank_line":
            self.clipboard.store([self.buffer[self.pos[0]]])
        elif cmd in ("paste_before", "paste_after"):
            t, v = self.clipboard.retrieve()
            if not v: return
            if t=="char":
                line = self.buffer[self.pos[0]]
                insertx = self.pos[1] if cmd=="paste_before" else self.pos[1]+1
                self.buffer[self.pos[0]] = line[:insertx] + v +line[insertx:]
                insert_pos = self.pos[0], insertx
                if not line: 
                     self.pos = self.pos[0], len(v) -1
                else: 
                     self.pos = self.pos[0], self.pos[1] + len(v)
                # commit the edit operation
                self.start_new_char_edit("insert", insert_pos)
                self.editop.value = v
                self.commit_current_edit()
            else:
                assert isinstance(v, list)
                inserty = self.pos[0] if cmd =="paste_before" else self.pos[0]+1
                for line in reversed(v):
                    self.buffer.insert(inserty, line)
                self.pos = inserty, 0
                self.editop = EditOp(self, "insert", "line", self.pos)
                self.editop.value = v
                self.commit_current_edit()
            self.refresh()
            self.refresh_cursor()                
        # Check if needs to switching to editing mode
        if "insert" in cmd:
            self.mode = "editing"
            self.refresh_command_line()

    def save_file(self):
        assert self.outfile is not None
        self.outfile.truncate(0)
        # Seek is absolutely necessary as truncate does NOT modify file position
        self.outfile.seek(0) 
        for line in self.buffer:
            self.outfile.write(line)
            self.outfile.write("\n")
        self.outfile.flush()
        # save the editlist cursor
        self.checkpoint = self.editlist.cursor

    def handle_editing_command(self, ch):
        if curses.ascii.isprint(ch):
            self.commandline += chr(ch)
            self.refresh_command_line()
        elif ch==curses.KEY_BACKSPACE or ch==127:
            self.commandline = self.commandline[:-1]
            self.refresh_command_line()
        elif ch==27 or ch==curses.ascii.ETX: # ESC, back to command mode
            self.command_editing = False
            self.commandline = ""
            self.refresh_command_line()
            self.refresh_cursor()
        elif ch==10: # new line \n
            self.command_editing = False
            if self.commandline.startswith(":"):
                commandline = self.commandline[1:].strip()
                if commandline in ("q", "q!"): # handle quit commands
                    if commandline == "q" and self.dirty:
                        self.flash_status_line("--Unsaved Changes--")
                    else:
                        raise SystemExit()
                elif commandline in ("w", "wq"): # handle write and write/quit without filename
                    if self.outfile:
                        self.save_file()
                        if commandline == "wq":
                            raise SystemExit()
                        else:
                            self.flash_status_line("--File saved--")
                    else:
                        self.flash_status_line("--Target file not specified--")
                elif commandline.startswith("w ") or commandline.startswith("wq "):
                    parts = commandline.split()
                    if len(parts)>2:
                        self.flash_status_line("--Only one file name allowed--")
                    else:
                        cmd, filename = parts
                        try:
                            self.outfile = open(filename, "w")
                        except Exception as e:
                            self.flash_status_line("--File open fails: %s--"%e)
                        else:
                            self.save_file()
                            if cmd == "wq":
                                raise SystemExit()
                            else:
                                self.flash_status_line("--File saved--")
                elif commandline in ("nu", "nonu"):
                    self.showlineno = (commandline=="nu")
                    if self.showlineno:
                        self.maxx = self.scr.getmaxyx()[1] - self.get_lineno_width()
                    else:
                        self.maxx = self.scr.getmaxyx()[1]
                    self.refresh()
                    self.refresh_cursor()
                else:
                    self.flash_status_line("-- Command not recognized --")
            elif self.commandline.startswith("/") or self.commandline.startswith("?"):
                keyword = self.commandline[1:]
                try:
                    keyword_regex = re.compile(keyword)
                except:
                    self.flash_status_line("--Invalid search pattern string--")
                    return
                self.searchpos = self.pos
                self.searchkw = keyword_regex
                if self.commandline.startswith("/"):
                    self.searchdir = "forward"
                else:
                    self.searchdir = "backward"
                pos = self.search_for_keyword(self.searchdir)
                if not pos:
                    self.flash_status_line("--Search pattern not found--")
                    return
                self.pos = pos
                self.refresh_cursor()
            self.refresh_command_line()
            self.refresh_cursor()

    def search_for_keyword(self, direction="forward"):
        # return a position where the keyword is found, or return None if not found
        y, x = self.searchpos
        # First make sure the start_pos is valid position, if invalid, fall back to 0,0
        if y>=len(self.buffer) or (x>=len(self.buffer[y]) and x!=0):
            y, x =  0, 0
        step = 1 if direction=="forward" else -1
        visited = []
        while True: # iterate over the lines
            visited.append((y, x))
            line = self.buffer[y][x:] if direction=="forward" else self.buffer[y][:x]
            if line:
                if direction == "forward":
                    mo = self.searchkw.search(line) # left to right
                    if mo:
                        self.searchpos = y, x+mo.end()
                        if self.searchpos[1] == len(self.buffer[y]):
                            self.searchpos = (y+step)%len(self.buffer), 0
                        return (y, x+mo.start())
                else: # backward
                    # to search right to left for regex: http://stackoverflow.com/questions/33232729/how-to-search-for-the-last-occurrence-of-a-regular-expression-in-a-string-in-pyt
                    starts = [mo.start() for mo in self.searchkw.finditer(line)]
                    if starts:
                        self.searchpos = y, starts[-1]
                        return (y, starts[-1])
            y = y+step
            if y >=len(self.buffer): 
                y = 0
                self.flash_status_line("--Search hit BOTTOM, continuing at TOP--")
            elif y<0:
                y = len(self.buffer)-1
                self.flash_status_line("--Search hit TOP, continuing at BOTTOM--")
            x = 0 if direction=="forward" else len(self.buffer[y])
            if (y, x) in visited: # revisit a visited position, meaning the doc has been scanned in full
                return None

    def handle_cursor_move(self, ch):
        # finish the last edit if exists
        self.commit_current_edit()
        y, x = self.pos
        # print y, x
        if ch in (curses.KEY_UP, ord('k')) and y > 0:
            y = y-1
            last_char = len(self.buffer[y])
            if self.mode == "command" and last_char>0:
                last_char = last_char-1
            x = min(x, last_char)
            self.pos = (y, x)
            # if y<self.topline:
            #     self.topline -= 1
            #     self.refresh()
            self.refresh_cursor()
        elif ch in (curses.KEY_DOWN, ord('j')) and y < len(self.buffer)-1:
            y = y + 1
            last_char = len(self.buffer[y])
            if self.mode == "command" and last_char>0:
                last_char = last_char-1
            x = min(x, last_char)
            self.pos = (y, x)
            self.refresh_cursor()
        elif ch in (curses.KEY_LEFT, ord('h')) and x>0:
            self.pos = (y, x-1)
            self.refresh_cursor()
        elif ch in (curses.KEY_RIGHT, ord('l')):
            last_char = len(self.buffer[y])
            if self.mode == "command" and last_char>0:
                last_char = last_char-1
            if x<last_char:
                self.pos = (y, x+1)
                self.refresh_cursor()
                
    def handle_delete_char(self, ch):
        if (not self.editop or not self.editop.edit_type == "delete" 
            or (self.editop.backwards and ch==curses.KEY_DC) 
            or (not self.editop.backwards and ch==curses.KEY_BACKSPACE)
            or ch==120 or ch==88):
            self.start_new_char_edit("delete", self.pos)
            if ch==curses.KEY_BACKSPACE or ch==88: 
                self.editop.backwards = True
        y, x = self.pos
        if ch==curses.KEY_DC or ch==120: # del or x
            if x == len(self.buffer[y]):
                if y < len(self.buffer)-1: 
                    # delete the \n at the end of a line
                    self.editop.append_edit("\n")
                    if ch==120: self.clipboard.store("\n")
                    self.buffer[y] = self.buffer[y] + self.buffer[y+1]
                    del self.buffer[y+1]
                    self.commit_current_edit()
                # else, last line, last char, ignore
            else:
                char = self.buffer[y][x]
                self.editop.append_edit(char)
                if ch == 120: 
                    self.clipboard.store(char)
                    self.commit_current_edit()
                self.buffer[y] = self.buffer[y][:x]+self.buffer[y][x+1:]
        else: # backspace or X
            if x==0:
                if y > 0:
                    self.editop.append_edit("\n")
                    if ch==88: self.clipboard.store("\n")
                    lastlen = len(self.buffer[y-1])
                    self.buffer[y-1] = self.buffer[y-1] + self.buffer[y]
                    del self.buffer[y]
                    self.pos = y-1, lastlen
                    self.commit_current_edit()
            else:
                char = self.buffer[y][x-1]
                self.editop.append_edit(char)
                if ch == 88: 
                    self.clipboard.store(char)
                    self.commit_current_edit()
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
        elif ch in (curses.KEY_DC, curses.KEY_BACKSPACE, 127): # DEL or BACKSPACE
            self.handle_delete_char(ch)
        elif self.is_direction_char(ch):
            self.handle_cursor_move(ch)
        elif ch==curses.KEY_HOME:
            self.pos = self.pos[0], 0
            self.refresh_cursor()
        elif ch==curses.KEY_END:
            self.pos = self.pos[0], len(self.buffer[self.pos[0]]) if self.buffer[self.pos[0]] else 0
            self.refresh_cursor()
        elif ch==27 or ch==curses.ascii.ETX: # ESC, to exit editing mode
            self.mode = "command"
            self.command_editing = False
            self.partial = ""
            self.status_line = "-- COMMAND --"
            # need to commit edit before switching mode
            self.commit_current_edit()
            # If currently pos beyond end of line, move back 1 char before entering command mode
            if x != 0 and x == len(self.buffer[y]):
                self.pos = (y, x-1)
                self.refresh_cursor()
            self.refresh_command_line()
        return True

    # View part of MVC: screen rendering 
    def clear_scr_line(self, y):
        self.scr.move(y,0)
        self.scr.clrtoeol()

    def get_lineno_width(self):
        if self.showlineno:
            return len(str(len(self.buffer)))
        else:
            return 0

    def refresh_cursor(self):
        # move the cursor position based on self.pos
        # when cursor moves beyond top of screen
        if self.pos[0] < self.topline:
            self.topline = self.pos[0]
            self.refresh()
        screen_y = sum(self.line_heights[:self.pos[0]-self.topline])
        screen_y += self.pos[1]/self.maxx
        screen_x = self.pos[1]%self.maxx + self.get_lineno_width()

        if screen_y >= self.maxy-1 and self.topline<len(self.buffer)-1:
            # if the cursor is beyond the bottom of screen, scroll down 1 line and retry
            self.topline += 1
            self.refresh()
            self.refresh_cursor()
        else:
            self.scr.move(screen_y, screen_x)

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
        if self.mode=="command" and self.command_editing:
            self.scr.addstr(self.maxy-1, 0, self.commandline)
            self.scr.move(self.maxy-1, len(self.commandline))
        else:
            if self.mode=="editing":
                self.status_line = "-- INSERT --"
            self.scr.addstr(self.maxy-1,0, self.status_line)
            self.scr.move(_y, _x)

    def refresh(self):
        _y = 0
        self.line_heights = []
        self.screen_lines = 0
        for i, line in enumerate(self.buffer[self.topline:]):
            singleline = line[:self.maxx]
            self.clear_scr_line(_y)
            if self.showlineno:
                self.scr.addstr(_y, 0, str(self.topline+i+1).rjust(self.get_lineno_width()), curses.A_REVERSE)
            self.scr.addstr(_y, self.get_lineno_width(), singleline)
            idx = self.maxx
            line_height = 1
            self.screen_lines += 1
            _y += 1
            try:
                if _y >= self.maxy-1:
                    raise LineBeyondScreenError()
                while idx<len(line):
                    singleline = line[idx:idx+self.maxx]
                    self.clear_scr_line(_y)
                    self.scr.addstr(_y, self.get_lineno_width(), singleline)
                    idx += self.maxx
                    _y+=1
                    line_height += 1
                    if _y >= self.maxy-1:
                        raise LineBeyondScreenError()
            except LineBeyondScreenError:
                self.line_heights.append(line_height)
                break
            self.line_heights.append(line_height)
                
        # fill the extra lines with ~
        while _y < self.maxy-1:
            self.clear_scr_line(_y)
            self.scr.addstr(_y,0,"~", curses.COLOR_RED)
            _y+=1
        # last line is reserved for commands
        # self.refresh_command_line()
        
def intercept_signals():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

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
        buf = [line[:-1] if line.endswith('\n') else line for line in f.readlines()]
    else:
        f = None
        buf = [""]
    intercept_signals()
    editor = Editor(f, buf)
    try:
        curses.wrapper(editor.main_loop)
    except Exception:
        editor.outfile = open("before_crash_text", "w")
        editor.save_file()
        print "Sorry, pythonvi crashed, your text has been saved in before_crash_text in current directory."
    finally:
        if editor.outfile: editor.outfile.close()
        

if __name__ == "__main__":
    main() 
    