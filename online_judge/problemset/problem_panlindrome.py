from problem import Problem


class PalindromeProblem(Problem):
    _id = 5
    title = "Palindrome Or Not"
    description = "A palindrome is a word, phrase, number,\
or other sequence of characters which reads the same backward or forward.\
return True if the supplied word is palindrome, else return False"
    method_name = "is_palindrome"
    args = ("word",)
    tests = [
        ("abcdcba", True),
        ("a", True),
        ("ABCba", False),
        ("aaaaa", True),
        ("aabaaa", False),
    ]
