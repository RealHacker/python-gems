from problem import Problem


class SortProblem(Problem):
    _id = 4
    title = "Sort Numbers Array"
    description = "Given an array of integers, sort it ascendingly and return the resulting list."
    method_name = "sort_array"
    args = ("nums",)
    tests = [
        ([1], [1]),
        ([1, 3, 2,4, 5], [1,2, 3,4,5]),
        ([5, 5, 5, 5, 5, 1], [1, 5, 5, 5, 5, 5]),
        (range(999, 0, -1), range(1, 1000))
    ]
