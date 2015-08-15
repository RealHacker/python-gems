"""
This is a simplistic implementation of fileinput module
"""
import sys

class FileInput(object):
    def __init__(self, files=None):
        if not files:
            self._files = sys.argv[1:]
            if not self._files:
                self._files = ("_", )
        elif isinstance(files, list):
            self._files = tuple(files)
        elif isinstance(files, basestring):
            self._files = (files, )
        else:
            raise ValueError("Invalid input")

        self._file = None
        self._fileindex = 0
        self._lineindex = 0
        self._buffer = None
        self._filename = None
        self._is_stdin = False

    def __iter__(self):
        return self

    def next(self):
        line = self.get_next_line()
        if line:
            return line
        else:
            raise StopIteration

    def get_next_line(self):
        if not self._buffer:
            if not self.load_next_file():
                return None
        try:
            line = self._buffer[self._lineindex]
        except IndexError:
            if self.load_next_file():
                return self.get_next_line()
            else:
                return None
        else:
            self._lineindex += 1
            return line

    def load_next_file(self):
        if not self._files:
            return False
        _filename = self._files[0]
        self._files = self._files[1:]
        self._fileindex += 1
        
        if _filename == "_":
            self._filename = "<std input>"
            self._file = sys.stdin
            self._is_stdin = True
        else:
            self._filename = _filename
            if self._file and not self._is_stdin:
                self._file.close()
            try:
                self._file = open(_filename, "r")
            except:
                return self.load_next_file()
        self._lineindex = 0
        self._buffer = self._file.readlines()
        if not self._buffer:
            return load_next_file()
        return True
        
    def lineno(self):
        return self._lineindex

    def fileno(self):
        return self._fileindex

    def filename(self):
        return self._filename

if __name__ == "__main__":
    f = FileInput()
    f = FileInput("../test.js")
    f = FileInput(["../test.js", "../weixin.txt", "foobar.txt"])
    for line in f:
        print "%s(%d):%d\t%s"%(f.filename(), f.fileno(), f.lineno(), line)
        
        
