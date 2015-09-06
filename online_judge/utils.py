"""
This module defines a few data structures and utility functions
for use in problem solution and solver
"""

LISTNODE_DEF = """
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None
"""

class ListNode(object):
    """
    ListNode has a next pointer and a val field.
    """
    def __init__(self, x):
        self.val = x
        self.next = None

def make_linked_list(numbers):
    next = None
    node = None
    for n in reversed(numbers):
        node = ListNode(n)
        node.next = next
        next = node
    return node

def dump_linked_list(llist):
    numbers = []
    while llist:
        numbers.append(llist.val)
        llist = llist.next
    return numbers

def cmp_linked_list(llist, numbers):
    node = llist
    for number in numbers:
        if not node or node.val != number:
            return False
        node = node.next
    return not node
    
