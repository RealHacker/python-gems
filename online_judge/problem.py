"""
Every Problem should inherit from Problem class.
The rationale for using python class to define problems
as opposed to persistent data (JSON file, DB) is:
1. Some problems require the program to modify data structures in place,
    so you need code to validate its correctness.
2. For some problems, input/expected output may need customized serialization
    and deserialization code.
3. Sometimes the only way to validate a program is to call a correct solver
   and compare results.
"""
import operator

class Problem(object):
    """
    Each Problem subclass should define these attributes:
    _id: the identifier
    title: the title to describe the problem
    description:
    method_name: the method name within Solution
    tests: a list of test cases, each test case is
        a tuple (input, expected_output)
        expected_output can be None if no output is expeced
    """
    def prepare_input(self, raw_in):
        # Override this when the test input needs preparation
        # (like deserialization) before passing to program
        return raw_in

    def validate_result(self, raw_in, real_in, expected_out, real_out):
        # The validation depends on the problem:
        # 1. Validate real_out == expected_out (may need deserialization)
        # 2. Validate read_in is modified correctly
        # 3. May need a real solver to run, and compare results
        # Here is the default validation, override if needed
        return expected_out == real_out

    def get_output_str(self, real_out):
        # Get a printable string for program output
        # used when the output is incorrect
        return str(real_out)
    
    @classmethod
    def load_problemset(cls):
        import problemset
        problem_classes = cls.__subclasses__()
        problems = [problem_cls() for problem_cls in problem_classes]
        problems.sort(key=operator.attrgetter("_id"))
        return problems


class SolutionError(Exception):
    """
    Solution Error with an string argument to show reason
    """
