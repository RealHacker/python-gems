import curses
import curses.ascii
import sys

class Editor(object):
    def __init__(self, f, buf):
        self.outfile = f
        self.buffer = buf
        
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

    def do_command(self, ch):
        if ch==curses.KEY_UP:
            _y, _x = self.pos
            if _y > 0:
                y = _y-1
                x = min(_x, len(self.buffer[y])-1)
                self.pos = (y, x)
                if y>=self.topline:
                    self.refresh_cursor()
                else:
                    self.topline -= 1
                    self.refresh()
                    self.refresh_cursor()
                    
        elif ch==curses.KEY_DOWN:
            _y, _x = self.pos
            if _y < len(self.buffer)-1:
                y = _y + 1
                x = min(_x, len(self.buffer[y])-1)
                self.pos = (y, x)
                in_screen = self.refresh_cursor()
                while not in_screen:
                    self.topline += 1
                    self.refresh()
                    in_screen = self.refresh_cursor()
                
        elif ch==curses.KEY_LEFT:
            y, x = self.pos
            if x>0:
                self.pos = (y, x-1)
                self.refresh_cursor()
        elif ch==curses.KEY_RIGHT:
            y, x = self.pos
            if x<len(self.buffer[y])-1:
                self.pos = (y, x+1)
                in_screen = self.refresh_cursor()
                if not in_screen:
                    self.topline += 1
                    self.refresh()
                    self.refresh_cursor()
	return True
    def refresh_cursor(self):
        # move the cursor position based on self.pos
        screen_y = sum(self.line_heights[:self.pos[0]-self.topline])
        screen_y += self.pos[1]/self.maxx+1
        screen_x = self.pos[1]%self.maxx
        if screen_y > self.maxy-1:
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
        buf = [" "]
    editor = Editor(f, buf)
    curses.wrapper(editor.main_loop)

if __name__ == "__main__":
    main() 
    

    
        
