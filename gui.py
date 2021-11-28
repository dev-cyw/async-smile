# actually a TUI because tkinter is a fucking bitch

import os
import curses
import time
from threading import Thread

kill = False


def counter_process(scr):
    n = 0
    while kill is False:
        try:
            scr.addstr(str(n) + "\n")
            n += 1
            time.sleep(1)
        except curses.error:
            scr.clear()
            scr.addstr(str(n) + "\n")
        scr.refresh()


def main2():
    terminal_size = os.get_terminal_size()
    curses.initscr()
    window_left = curses.newwin(terminal_size.lines, terminal_size.columns // 2, 0, 0)
    window_right = curses.newwin(terminal_size.lines, terminal_size.columns // 2, 0, terminal_size.columns // 2)
    window_left.refresh()
    window_right.refresh()

    counterThread = Thread(target=counter_process, args=(window_left,))
    counterThread.start()
    while True:
        key = window_right.getkey()
        if str(key) == "c":
            window_right.addstr("Cancelling...")
            window_right.refresh()
            global kill
            kill = True
            counterThread.join()


if __name__ == '__main__':
    main2()
else:
    def start():
        tui_thread = Thread(target=main2)
        tui_thread.start()

