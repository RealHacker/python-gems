# PythonVI #

----------

**VI editor implemented in python, supporting only the very basic features:**

1.  Editing mode and command mode switch
1.  Unlimited Undo/Redo history 
1.  Single clipboard for words/lines
1.  Showing/hiding line numbers
1.  Forward/backward searching, with regular expression (python re)
 
**Implemented commands (mostly commands in cheatsheet)**

 - ("gg", "goto_first_line")
 - ("dw", "delete_word")
 - ("dW", "delete_term")
 - ("yw", "yank_word")
 - ("yW", "yank_term")
 - ("dd", "delete_line")
 - ("yy", "yank_line")
 - ("r", "replace_char")
 - ("i", "insert_mode")
 - ("I", "insert_line_start")
 - ("o", "insert_line_after")
 - ("O", "insert_line_before")
 - ("a", "insert_after")
 - ("A", "insert_line_end")
 - ("s", "delete_char_insert")
 - ("S", "delete_line_insert")
 - ("D", "delete_line_end")
 - ("u", "undo")
 - (".", "repeat_edit")
 - ("^", "goto_line_start")
 - ("0", "goto_line_start")
 - ("$", "goto_line_end")
 - ("-", "goto_prev_line_start")
 - ("+", "goto_next_line_start")
 - ("H", "goto_first_screen_line")
 - ("L", "goto_last_screen_line")
 - ("M", "goto_middle_screen_line")
 - ("G", "goto_line")
 - ("w", "next_word_start")
 - ("W", "next_term_start")
 - ("e", "word_end")
 - ("E", "term_end")
 - ("b", "word_start")
 - ("B", "term_start")
 - (":", "command_edit_mode")
 - ("~", "switch_case")
 - ("x", "delete_char")
 - ("X", "delete_last_char")
 - ("%", "match_pair")
 - ("/", "search_mode")
 - ("?", "reverse_search_mode")
 - ("n", "search_next")
 - ("N", "search_previous")
 - ("Y", "yank_line")
 - ("p", "paste_after")
 - ("P", "paste_before")
 - (CTRL+R, "redo")
 - (CTRL+F, "Next page")
 - (CTRL+B, "Previous page")
 - (CTRL+E, "Scroll down")
 - (CTRL+Y, "Scroll up")
 
**Ex mode commands**

 - :w
 - :wq
 - :q
 - :q!
 - nu - show line number
 - nonu - hide line number 