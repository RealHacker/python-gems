from datetime import date
import os

# A simple script to open a new markdown todo file every day. 

year = date.today().year
month = date.today().strftime('%b').lower()
day = date.today().day

filename  = os.path.join(str(year) + '_' + month, str(day) + '.md')
try:
    os.mkdir(os.path.abspath(str(year) + '_' + month))
except:
    pass
file = open(filename, 'a')
file.close()

# replace this line with your way of opening markown files
os.system('start typora ' + filename)

# you could also just update a symbolic link and reference that link while opening your editor of choice
