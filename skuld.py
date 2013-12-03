"""
Python thread to manage your tasks in VIM.

Author:     Kay Zheng <l04m33@gmail.com>
License:    MIT (http://l04m33.mit-license.org)

"""

from __future__ import print_function
#import vim
import threading
import collections

try:
    import queue
except ImportError:
    import Queue as queue


SkuldCmd = collections.namedtuple('SkuldCmd', ['name', 'args', 'block'])


class Skuld(threading.Thread):

    """The thread object that manages EVERYTHING."""

    QUIT_EVENT_POLL_TIMEOUT = 0.2         # In seconds

    def __init__(self, cmd_queue=None, ret_queue=None, quit_event=None):
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
        self._tasks = []

    def run(self):
        """Main loop."""
        while not self._quit_e.wait(self.QUIT_EVENT_POLL_TIMEOUT):
            cmd = self._recv_cmd()
            while cmd is not None:
                self._handle_cmd(cmd)
                cmd = self._recv_cmd()

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

    def _cmd_default(self, cmd):
        print(self, cmd)

    def _cmd_set_tasks(self, cmd):
        self._tasks = cmd.args

    def _cmd_get_tasks(self, cmd):
        self._ret_q.put(self._tasks)


def __check_arg_type__(obj, cls, ctor):
    if not isinstance(obj, cls):
        if obj is None:
            obj = ctor()
        else:
            raise TypeError
    return obj


if __name__ == '__main__':
    s = Skuld()
    s.setDaemon(True)
    s.start()
    import code
    code.interact(local=locals())
