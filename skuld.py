"""
Python thread to manage your tasks in VIM.

Author:     Kay Zheng <l04m33@gmail.com>
License:    MIT (http://l04m33.mit-license.org)

"""

from __future__ import print_function
import vim
import threading
import collections
import time
import sys

try:
    import queue
except ImportError:
    import Queue as queue


SkuldCmd = collections.namedtuple('SkuldCmd', ['name', 'args', 'block'])


class Skuld(threading.Thread):

    """The thread object that manages EVERYTHING."""

    QUIT_EVENT_POLL_TIMEOUT = 0.2         # In seconds

    def __init__(self, adaptor=None, cmd_queue=None,
                 ret_queue=None, quit_event=None):
        """
        Initialize the Skuld object.

        If cmd_queue, ret_queue or quit_event is None, new `queue.Queue` and/or
        `threading.Event` object(s) will be created.

        """
        super(Skuld, self).__init__(name="Skuld")

        # Do some early checks here, instead of failing in
        # the main loop.

        # Spawn a new object for it's __class__, since the
        # real classes may not be visible in their modules.
        dummy_q = queue.Queue()
        cmd_queue = __check_arg_type__(cmd_queue,
                                       dummy_q.__class__,
                                       queue.Queue)
        ret_queue = __check_arg_type__(ret_queue,
                                       dummy_q.__class__,
                                       queue.Queue)
        del dummy_q

        dummy_e = threading.Event()
        quit_event = __check_arg_type__(quit_event,
                                        dummy_e.__class__,
                                        threading.Event)
        del dummy_e

        self._cmd_q = cmd_queue
        self._ret_q = ret_queue
        self._quit_e = quit_event
        self._work_period = 0.5
        self._rest_period = 0.5
        self._long_rest_period = 1
        self._max_work_streak = 2
        self._tasks = []
        self._cur_task = -1
        self._cur_state_start_time = None
        self._cur_state = self._state_idle
        self._cur_work_streak = 0
        self._vim_adaptor = adaptor

    def run(self):
        """Main loop."""
        while not self._quit_e.wait(self.QUIT_EVENT_POLL_TIMEOUT):
            cmd = self._recv_cmd()
            while cmd is not None:
                self._handle_cmd(cmd)
                cmd = self._recv_cmd()
            next_state = self._cur_state()
            if next_state != self._cur_state:
                self._cur_state_start_time = time.time()
                self._cur_state = next_state

    def cmd(self, cmd):
        """
        Send a command to the remote thread.

        Returns the result (could be anything) if cmd.block is True.

        """
        if self.is_alive():
            self._cmd_q.put(cmd)
            if cmd.block:
                return self._ret_q.get()
            else:
                return None
        else:
            raise RuntimeError('Skuld thread is not alive')

    def quit(self):
        """Kill the thread. Must be called by another thread."""
        self._quit_e.set()
        self.join()

    def _recv_cmd(self):
        try:
            return self._cmd_q.get(block=False)
        except queue.Empty:
            return None

    def _handle_cmd(self, cmd):
        cmd_func = getattr(self, '_cmd_' + cmd.name, self._cmd_default)
        cmd_func(cmd)

    def _reply_cmd(self, cmd, reply):
        if cmd.block:
            self._ret_q.put(reply)

    def _cmd_default(self, cmd):
        print(self, cmd, file=sys.stderr)

    def _cmd_set_adaptor(self, cmd):
        self._vim_adaptor = cmd.args

    def _cmd_set_work_period(self, cmd):
        self._work_period = cmd.args

    def _cmd_set_rest_period(self, cmd):
        self._rest_period = cmd.args

    def _cmd_set_long_rest_period(self, cmd):
        self._long_rest_period = cmd.args

    def _cmd_set_tasks(self, cmd):
        self._tasks = cmd.args

    def _cmd_get_tasks(self, cmd):
        self._reply_cmd(cmd, self._tasks)

    def _cmd_start_timer(self, cmd):
        if isinstance(cmd.args, int):
            self._cur_task = cmd.args
        else:
            self._cur_task = 0
        if self._cur_task >= 0 and self._cur_task < len(self._tasks):
            print('_state_idle -> _state_working', file=sys.stderr)
            self._cur_state_start_time = time.time()
            self._cur_state = self._state_working

    def _cmd_stop_timer(self, cmd):
        print('_state_* -> _state_idle', file=sys.stderr)
        self._cur_state_start_time = None
        self._cur_state = self._state_idle
        self._cur_work_streak = 0

    def _cmd_timer_enabled(self, cmd):
        if self._cur_state == self._state_idle:
            self._reply_cmd(cmd, False)
        else:
            self._reply_cmd(cmd, True)

    def _state_idle(self):
        return self._state_idle

    def _state_working(self):
        if self._cur_state_start_time is not None:
            now = time.time()
            diff_time = now - self._cur_state_start_time
            if diff_time >= (self._work_period * 60):
                # TODO: Trigger notification
                self._cur_work_streak += 1
                if self._cur_work_streak < self._max_work_streak:
                    print('_state_working -> _state_resting', file=sys.stderr)
                    return self._state_resting
                else:
                    self._cur_work_streak = 0
                    print('_state_working -> _state_long_resting',
                          file=sys.stderr)
                    return self._state_long_resting
            else:
                return self._state_working
        else:
            return self._state_idle

    def _state_resting(self):
        if self._cur_state_start_time is not None:
            now = time.time()
            diff_time = now - self._cur_state_start_time
            if diff_time >= (self._rest_period * 60):
                # TODO: Trigger notification
                print('_state_resting -> _state_working', file=sys.stderr)
                return self._state_working
            else:
                return self._state_resting
        else:
            return self._state_idle

    def _state_long_resting(self):
        if self._cur_state_start_time is not None:
            now = time.time()
            diff_time = now - self._cur_state_start_time
            if diff_time >= (self._long_rest_period * 60):
                # TODO: Trigger notification
                print('_state_long_resting -> _state_working', file=sys.stderr)
                return self._state_working
            else:
                return self._state_long_resting
        else:
            return self._state_idle


class SkuldVimAdaptor(object):

    """The Bridge between Skuld and Vim."""

    SKULD_BUFFER_NAME = '[Skuld Tasks]'

    def __init__(self, skuld_obj=None):
        if skuld_obj is None:
            skuld_obj = Skuld()
            skuld_obj.setDaemon(True)
            skuld_obj.start()
        self._skuld = skuld_obj
        skuld_obj.cmd(SkuldCmd(name='set_adaptor', args=self, block=False))

    #def set_current_range_as_tasks(self):
    #    """Set the current range as tasks."""
    #    tasks = __filter_task_lines__(vim.current.range[:])
    #    self._skuld.cmd(SkuldCmd(name='set_tasks',
    #                             args=tasks,
    #                             block=False))

    def set_current_buf_as_tasks(self):
        """Set the contents of current buffer as tasks."""
        tasks = __filter_task_lines__(vim.current.buffer[:])
        self._skuld.cmd(SkuldCmd(name='set_tasks',
                                 args=tasks,
                                 block=False))

    def display_tasks(self):
        """Display the tasks in a new window. Return nothing."""
        skuld_tab, skuld_window = __find_vim_window__(self.SKULD_BUFFER_NAME)
        if skuld_window is None:
            vim.command('tabedit ' + self.SKULD_BUFFER_NAME)
        else:
            vim.current.tabpage = skuld_tab
            vim.current.window = skuld_window
        self.update_buf_content(vim.current.window.buffer)
        vim.current.buffer.options['modified'] = False
        vim.current.buffer.options['buftype'] = 'nofile'
        vim.current.buffer.options['bufhidden'] = 'hide'
        vim.current.buffer.options['swapfile'] = False
        vim.command('call SkuldMapBufKeys()')

    def update_buf_content(self, buf=None):
        """Write tasks to a buffer."""
        if buf is None:
            buf = vim.current.buffer
        tasks = self._skuld.cmd(SkuldCmd(name='get_tasks',
                                         args=[],
                                         block=True))
        buf[:] = tasks


def __filter_task_lines__(lines):
    for l in lines[:]:
        sl = l.strip()
        if sl.startswith('#') or len(sl) == 0:
            lines.remove(l)
    return [ll.strip() for ll in lines]


def __search_vim_tab__(t, name):
    for w in t.windows:
        if w.valid and w.buffer.name.endswith(name):
            return w
    return None


def __find_vim_window__(name):
    for t in vim.tabpages:
        if t.valid:
            w = __search_vim_tab__(t, name)
            if w is not None:
                return (t, w)

    return (None, None)


def __check_arg_type__(obj, cls, ctor):
    if not isinstance(obj, cls):
        if obj is None:
            obj = ctor()
        else:
            raise TypeError
    return obj


if __name__ == '__main__':
    skuld_adaptor = SkuldVimAdaptor()
