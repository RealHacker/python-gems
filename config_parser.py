"""
This is my own implementation of standard library ConfigParser module
It parses .ini file and generates a configuration object
"""
import re, collections

FORMAT_RE = r'.*%\([^\)]+\)[sd].*'
SECTION_RE = r'\[([^\[\]]+)\]'
OPTION_RE = r'(.*)=(.*)'
COMMENT_RE = r'^;.*'

class InvalidConfig(Exception):
	pass

def _is_format_str(s):
	regex = re.compile(FORMAT_RE)
	return regex.match(s)

def _parse_config_file(f):
	sections = {}
	current_section = None
	current_options = {}

	section_re = re.compile(SECTION_RE)
	option_re = re.compile(OPTION_RE)
	comment_re = re.compile(COMMENT_RE)

	for line in f:
		line = line.strip()

		if not line: continue
		if comment_re.match(line): continue
		
		mo = section_re.match(line)
		if mo:
			if current_section:
				sections[current_section] = current_options
			current_section = mo.group(1)
			current_options = {}
		else:
			mo1 = option_re.match(line)
			if mo1:
				if not current_section:
					raise InvalidConfig("Invalid config file")
				key, value = mo1.group(1).strip(), mo1.group(2).strip()
				current_options[key] = value
			else:
				raise InvalidConfig("Invalid config file")
	if current_section:
		sections[current_section] = current_options
	return sections

class ConfigParser(object):
    def __init__(self, defaults=None):
    	"""
        create the parser and specify a dictionary of intrinsic defaults.  The
        keys must be strings, the values must be appropriate for %()s string
        interpolation.  Note that `__name__' is always an intrinsic default;
        its value is the section's name.
        """
        self._defaults = defaults if defaults else {}
        self._sections = {}


    def sections(self):
        # return all the configuration section names
        return self._sections.keys()

    def has_section(self, section):
        return section in self._sections

    def has_option(self, section, option):
        return self.has_section(section) and option in self._sections[section]

    def options(self, section):
        if not self.has_section(section):
        	return []
        else:
        	return self._sections[section].keys()

    def read(self, filenames):
    	"""
        read and parse the list of named configuration files, given by
        name.  A single filename is also allowed.  Non-existing files
        are ignored.  Return list of successfully read files.
        """
        if isinstance(filenames, basestring):
        	f = open(filenames, 'r')
        	self.readfp(f)
        elif isinstance(filenames, collections.Iterable):
        	for fname in filenames:
        		try:
        			f = open(fname, 'r')
        			self.readfp(f)
        		except IOError:
        			print "Fail to open file %s, ignored"%fname
        		except InvalidConfig:
        			print "Invalid config file %s, ignored"%fname

    def readfp(self, fp, filename=None):
    	"""
        read and parse one configuration file, given as a file object.
        The filename defaults to fp.name; it is only used in error
        messages (if fp has no `name' attribute, the string `<???>' is used).
        """
        secs = _parse_config_file(fp)
        self._sections.update(secs)

    def parse_item(self, section, key, val):
    	# Now support only 1 level of interpolation
    	if not _is_format_str(val):
    		return val
    	else:
    		# first try default section
    		try:
    			newval = val%self._defaults
    		except KeyError:
    			try:
    				newval = val%self._sections[section]
    			except KeyError:
    				newval = val
    		return newval

    def get(self, section, option, raw=False, vars=None):
        if not self.has_section(section):
        	return None
        sec = self._sections[section]
        if option not in sec:
        	return None
        return self.parse_item(section, option, sec[option])

    def getint(self, section, option):
        return int(self.get(section, option))

    def getfloat(self, section, option):
        return float(self.get(section, option))

    def getboolean(self, section, option):
		val = self.get(section, option).strip()
		if val.lower() in ["0", "false", "no", "off"]:
			return False
		elif val.lower() in ["1", "true", "yes", "on"]:
			return True
		else:
			raise ValueError("Invalid boolean option")

    def items(self, section, raw=False, vars=None):
        try:
        	d = self._sections[section]
        except KeyError:
        	d = {}
        d.update(self._defaults)
        return d.items()

    def remove_section(self, section):
    	if self.has_section(section):
        	del self._sections[section]

    def remove_option(self, section, option):
        if self.has_option(section, option):
        	del self._sections[section][option]

    def set(self, section, option, value):
        if self.has_section(section):
        	self._sections[section][option] = value

    def write(self, fp):
        #write the configuration state in .ini format
        pass