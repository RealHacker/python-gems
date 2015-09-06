from problem import Problem

class HelloProblem(Problem):
    """
    Awefully simple problem, no need to override any method
    """
    _id = 1
    title = "Hello Problem"
    description = "Just return 'Hello ' followed by the name passed in."
    "I know, it's silly, just to prove everything works"
    method_name = "hello"
    args = ("name",)
    tests = [("Foo", "Hello Foo"),
            ("Bar", "Hello Bar")]
    
