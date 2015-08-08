class DisjointSet(object):
    def __init__(self):
        self.leader = {} # maps a member to the group's leader
        self.group = {} # maps a group leader to the group (which is a set)

    def add(self, a, b):
        leadera = self.leader.get(a)
        leaderb = self.leader.get(b)
        if leadera is not None:
            if leaderb is not None:
                if leadera == leaderb: return # nothing to do
                groupa = self.group[leadera]
                groupb = self.group[leaderb]
                if len(groupa) < len(groupb):
                    a, leadera, groupa, b, leaderb, groupb = b, leaderb, groupb, a, leadera, groupa
                groupa |= groupb
                del self.group[leaderb]
                for k in groupb:
                    self.leader[k] = leadera
            else:
                self.group[leadera].add(b)
                self.leader[b] = leadera
        else:
            if leaderb is not None:
                self.group[leaderb].add(a)
                self.leader[a] = leaderb
            else:
                self.leader[a] = self.leader[b] = a
                self.group[a] = set([a, b])

mylist="""
specimen|3 
sample
prototype
example
sample|3
prototype
example
specimen
prototype|3
example
specimen
sample
example|3 
specimen
sample
prototype
prototype|1
illustration
specimen|1
cat
happy|2
glad
cheerful 
"""
ds = DisjointSet()
for line in mylist.strip().splitlines():
    if '|' in line:
         node, _ = line.split('|')
    else:
         ds.add(node, line)

for _,g in ds.group.items():
    print g
    
