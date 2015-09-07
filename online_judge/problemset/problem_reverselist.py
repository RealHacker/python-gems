from problem import Problem, SolutionError
from utils import LISTNODE_DEF, make_linked_list, cmp_linked_list, dump_linked_list

class ReverseListProblem(Problem):
    _id = 3
    title = "Reverse Linked List"
    description = "Given a linked list, reverse it and return the head node."+\
        "\n"+ LISTNODE_DEF
    method_name = "reverse_linked_list"
    args = ("head",)
    tests = [
        ([1], [1]),
        ([1, 2, 3], [3, 2, 1]),
        ([1, 2, 2, 4, 4, 3], [3, 4, 4, 2, 2, 1]),
        (range(1, 1000), range(999, 0, -1))
    ]

    def prepare_input(self, raw_in):
        # make a linked list to send it in
        return make_linked_list(raw_in)

    def validate_result(self, raw_in, real_in, expected_out, real_out):
        cmp_result = cmp_linked_list(real_out, expected_out)
        # make sure the solution doesn't use new nodes
        if real_in:
            p = real_out
            while p.next:
                p = p.next
            if p != real_in:
                raise SolutionError, "You instantiated new nodes!"
        return cmp_result
    
    def get_output_str(self, real_out):
        return str(dump_linked_list(real_out))
