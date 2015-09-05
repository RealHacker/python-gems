# The implementation of Dr Knuth's dancing links/algorithm X
#       https://www.ocf.berkeley.edu/~jchu/publicportal/sudoku/0011047.pdf
# And demonstrate a N-Queens solver with dancing links
# TODO: will add a soduku solver in the future

# Both Node and HeaderNode have pointers in 4 directions
#   next, prev, up, down
class Node:
    # instance of Node has a candidate attribute
    def __init__(self, candidate):
        # The candidate is actually index in candidates list
        self.candidate = candidate            
class HeaderNode:
    # Header node has a constraint
    def __init__(self, constraint):
        self.constraint = constraint

class DancingLinks(object):
    def __init__(self, candidates, constraints, optional, check_func):
        self.candidates = candidates
        self.constraints = constraints
        self.optional = optional
        self.check = check_func
        # self.rows = []
        self.head = None
        # to hold complete results and partial result
        self.results = []
        self.partial = []
        
    def build_links(self):
        # first build the header row
        self.head = HeaderNode(None)
        cursor = self.head
        for constraint in self.constraints:
            header = HeaderNode(constraint)
            cursor.next = header
            header.prev = cursor
            # single node loop in vertical direction
            header.up = header
            header.down = header
            cursor = header
        cursor.next = self.head
        self.head.prev = cursor
        
        # Now build the rows
        for i, candidate in enumerate(self.candidates):
            rowhead = None
            current = None
            cursor = self.head.next
            while cursor!=self.head:
                if self.check(candidate, cursor.constraint):
                    # print candidate, cursor.constraint
                    node = Node(i)
                    # build left/right links
                    if not rowhead:
                        rowhead = current = node
                    else:
                        current.next = node
                        node.prev = current
                        current = node
                    # build up/down links
                    temp = cursor.up
                    cursor.up = node
                    node.down = cursor
                    node.up = temp
                    temp.down = node
                # go to next constraint
                cursor = cursor.next
            # close the row loop
            if current:
                current.next = rowhead
                rowhead.prev = current
            # self.rows.append(rowhead)

    # run algorithm x to find all exact matches
    def algorithm_x(self):
        # if constraint list is empty, current partial is a solution
        empty = (self.head.next == self.head)
        # very delicate situation: all constraints left are optional constraints, with no row satisfying each of them
        if not empty:
            all_empty_optional = True
            col = self.head.next
            while col!=self.head:
                if col.constraint not in self.optional or col.down != col:
                    all_empty_optional = False
                    break
                col = col.next
                    
        if empty or all_empty_optional:
            result = sorted(self.partial)
            if result not in self.results:
                self.results.append(result)
        else:
            col = self.head.next
            if col.down == col:
                if col.constraint in self.optional:
                    col = col.next                
                else:
                    # if non-optional constraint column is empty -> deadend, backtrack
                    return
            # Pick this col to start
            row = col.down
            while row!=col:
                # Add this row to partial result
                self.partial.append(row.candidate)
                # Cover this row
                self.cover_row(row)
                # Recurse
                self.algorithm_x()
                # Uncover picked row
                self.uncover_row(row)
                # Pop picked row
                self.partial.pop()
                # Back track to next row
                row = row.down

    def cover_row(self, r):
        rr = r
        self.cover_column(r)
        r = r.next
        while r!=rr:
            self.cover_column(r)
            r = r.next

    def uncover_row(self, r):
        rr = r
        r = r.prev
        while r!=rr:
            self.uncover_column(r)
            r = r.prev
        self.uncover_column(r)
            
    def cover_column(self, c):
        # First find the column header
        while not isinstance(c, HeaderNode):
            c = c.up
        # Remove the header from header row
        # The dancing links!
        c.next.prev = c.prev
        c.prev.next = c.next
        
        # Remove the rows up  down
        h = c
        c = c.down
        while c!=h:
            r = c
            cell = c.next
            while cell!=r:
                cell.up.down = cell.down
                cell.down.up = cell.up
                cell = cell.next
            c = c.down

    def uncover_column(self, c):
        # First find the column header
        while not isinstance(c, HeaderNode):
            c = c.up
        # Put the header node back into header row
        c.prev.next = c
        c.next.prev = c
        # Restore the rows, bottom up
        h = c
        c = c.up
        while c!=h:
            r = c
            cell = c.next
            while cell!=r:
                cell.up.down = cell
                cell.down.up = cell
                cell = cell.next
            c = c.up

    def get_results(self):
        # convert the result index list into actual candidates list
        return [map(lambda x: self.candidates[x], result) for result in self.results]

def solve_N_queens(n):
    candidates = [(x, y) for x in range(n) for y in range(n)]
    constraints = []
    optional = []
    for i in range(n):
        # Every row should have one and only one queen
        constraints.append(('row', i))
    for i in range(n):
        # Every column should have one and only one queen
        constraints.append(('col', i))
        
    # Diagnal constraints are optional, very hard-to-find bug
    for i in range(n*2-1):
        # diagnal
        constraints.append(('diag', i))
        optional.append(('diag', i))
    for i in range(n*2-1):
        constraints.append(('rdiag', i))
        optional.append(('rdiag', i))

    def checker(candidate, constraint):
        t, val = constraint
        if t=='row':
            return candidate[0]==val
        if t=='col':
            return candidate[1]==val
        if t=='diag':
            return (candidate[0]+candidate[1])==val
        else:
            return (n-1-candidate[0]+candidate[1])==val

    dl = DancingLinks(candidates, constraints, optional, checker)
    dl.build_links()
    dl.algorithm_x()
    results = dl.get_results()
    
    for result in results:
        print "+++++++++"
        for i in range(n):
            s = ""
            for j in range(n):
                if (i, j) in result:
                    s+="1"
                else:
                    s+="0"
            print s
        print "+++++++++"
    print "%d results found for N-Queen"%len(results)

def main():
    solve_N_queens(10)

if __name__ == "__main__":
    main()
