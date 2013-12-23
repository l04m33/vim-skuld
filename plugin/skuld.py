# -*- encoding: utf-8 -*-
"""
Python thread to manage your tasks in VIM.

Author:     Kay Zheng <l04m33@gmail.com>
License:    MIT (http://l04m33.mit-license.org)

"""


from __future__ import print_function


def skuld_closure():
    """The huge closure, for preventing name leaks."""
    # ================== imports ==================

    import vim
    import threading
    import thread
    import collections
    import time
    import os

    try:
        import queue
    except ImportError:
        import Queue as queue

    try:
        from shlex import quote as shell_quote
    except ImportError:
        from pipes import quote as shell_quote

    # ================== classes ==================

    SkuldCmd = collections.namedtuple('SkuldCmd', ['name', 'args', 'block'])

    class Skuld(threading.Thread):

        """The thread object that manages EVERYTHING."""

        CMD_POLL_TIMEOUT = 0.2         # In seconds

        def __init__(self, adaptor=None, cmd_queue=None, ret_queue=None):
            """
            Initialize the Skuld object.

            If cmd_queue or ret_queue is None, new `queue.Queue` object(s)
            will be created.

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

            self._cmd_q = cmd_queue
            self._ret_q = ret_queue
            self._work_period = 25
            self._rest_period = 5
            self._long_rest_period = 15
            self._max_work_streak = 4
            self._tasks = []
            self._cur_task = -1
            self._progress_symbol = '*'
            self._squash_symbol = 'x'
            self._cur_state_start_time = None
            self._cur_state = self._state_idle
            self._cur_work_streak = 0
            self._vim_adaptor = adaptor

        def run(self):
            """Main loop."""
            while True:
                cmd = self._recv_cmd(block=True,
                                     timeout=self.CMD_POLL_TIMEOUT)
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
            self.cmd(SkuldCmd(name='quit', args=None, block=False))
            self.join()

        def _recv_cmd(self, block=False, timeout=None):
            try:
                return self._cmd_q.get(block=block, timeout=timeout)
            except queue.Empty:
                return None

        def _handle_cmd(self, cmd):
            cmd_func = getattr(self, '_cmd_' + cmd.name, self._cmd_default)
            cmd_func(cmd)

        def _reply_cmd(self, cmd, reply):
            if cmd.block:
                self._ret_q.put(reply)

        def _cmd_default(self, cmd):
            self._vim_adaptor.remote_notify("Unknown command: " + repr(cmd))

        def _cmd_quit(self, cmd):
            thread.exit()

        def _cmd_set_adaptor(self, cmd):
            self._vim_adaptor = cmd.args

        def _cmd_set_work_period(self, cmd):
            self._work_period = cmd.args

        def _cmd_set_rest_period(self, cmd):
            self._rest_period = cmd.args

        def _cmd_set_long_rest_period(self, cmd):
            self._long_rest_period = cmd.args

        def _cmd_set_max_work_streak(self, cmd):
            self._max_work_streak = cmd.args

        def _cmd_set_tasks(self, cmd):
            self._tasks = cmd.args

        def _cmd_get_tasks(self, cmd):
            self._reply_cmd(cmd, self._tasks)

        def _cmd_get_cur_task(self, cmd):
            self._reply_cmd(cmd, self._cur_task)

        def _cmd_set_progress_symbol(self, cmd):
            self._progress_symbol = cmd.args

        def _cmd_set_squash_symbol(self, cmd):
            self._squash_symbol = cmd.args

        def _cmd_start_timer(self, cmd):
            if isinstance(cmd.args, int):
                self._cur_task = cmd.args
            else:
                self._cur_task = 0
            if self._cur_task >= 0 and self._cur_task < len(self._tasks):
                self._vim_adaptor.remote_notify(
                    'Skuld: Idle -> Working')
                self._cur_state_start_time = time.time()
                self._cur_state = self._state_working

        def _cmd_stop_timer(self, cmd):
            if self._cur_state == self._state_working:
                self._tasks[self._cur_task] += self._squash_symbol
            self._vim_adaptor.remote_notify('Skuld: * -> Idle')
            self._cur_state_start_time = None
            self._cur_state = self._state_idle
            self._cur_work_streak = 0

        def _cmd_timer_enabled(self, cmd):
            if self._cur_state == self._state_idle:
                self._reply_cmd(cmd, False)
            else:
                self._reply_cmd(cmd, True)

        def _cmd_get_state(self, cmd):
            if self._cur_state == self._state_idle:
                self._reply_cmd(cmd, "Idle")
            elif self._cur_state == self._state_working:
                reply = 'Working on task {} - '.format(self._cur_task) \
                        + __str_diff_time__(time.time(),
                                            self._cur_state_start_time)
                self._reply_cmd(cmd, reply)
            elif self._cur_state == self._state_resting \
                    or self._cur_state == self._state_long_resting:
                reply = 'Resting - ' \
                        + __str_diff_time__(time.time(),
                                            self._cur_state_start_time)
                self._reply_cmd(cmd, reply)

        def _cmd_switch_task(self, cmd):
            if isinstance(cmd.args, int) and cmd.args >= 0 \
                    and cmd.args < len(self._tasks):
                self._cur_task = cmd.args

        def _state_idle(self):
            return self._state_idle

        def _state_working(self):
            if self._cur_state_start_time is not None:
                now = time.time()
                diff_time = now - self._cur_state_start_time
                if diff_time >= (self._work_period * 60):
                    try:
                        self._tasks[self._cur_task] += self._progress_symbol
                    except IndexError:
                        pass

                    self._cur_work_streak += 1
                    if self._cur_work_streak < self._max_work_streak:
                        self._vim_adaptor.remote_notify(
                            'Skuld: Working -> Resting')
                        return self._state_resting
                    else:
                        self._cur_work_streak = 0
                        self._vim_adaptor.remote_notify(
                            'Skuld: Working -> Long Resting')
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
                    self._vim_adaptor.remote_notify(
                        'Skuld: Resting -> Working')
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
                    self._vim_adaptor.remote_notify(
                        'Skuld: Long Resting -> Working')
                    return self._state_working
                else:
                    return self._state_long_resting
            else:
                return self._state_idle

    class SkuldVimAdaptor(object):

        """The Bridge between Skuld and Vim."""

        SKULD_BUFFER_NAME = '[Skuld Tasks]'
        SKULD_TASK_SEPERATOR = ' |'

        def __init__(self, vim_server=None, skuld_obj=None):
            if vim_server is None:
                vim_server = vim.vvars['servername']
            if len(vim_server) == 0:
                raise RuntimeError('v:servername not found')
            self._vim_server_name = vim_server

            if skuld_obj is None:
                skuld_obj = Skuld()
                skuld_obj.setDaemon(True)
                skuld_obj.start()

                progress_sym = vim.vars.get('skuld_progress_symbol', '*')
                skuld_obj.cmd(SkuldCmd(name='set_progress_symbol',
                                       args=progress_sym, block=False))

                squash_sym = vim.vars.get('skuld_squash_symbol', 'x')
                skuld_obj.cmd(SkuldCmd(name='set_squash_symbol',
                                       args=squash_sym, block=False))

                work_period = vim.vars.get('skuld_work_period', 25)
                skuld_obj.cmd(SkuldCmd(name='set_work_period',
                                       args=work_period, block=False))

                rest_period = vim.vars.get('skuld_rest_period', 5)
                skuld_obj.cmd(SkuldCmd(name='set_rest_period',
                                       args=rest_period, block=False))

                long_rest_period = vim.vars.get('skuld_long_rest_period', 15)
                skuld_obj.cmd(SkuldCmd(name='set_long_rest_period',
                                       args=long_rest_period, block=False))

                max_work_streak = vim.vars.get('skuld_max_work_streak', 4)
                skuld_obj.cmd(SkuldCmd(name='set_max_work_streak',
                                       args=max_work_streak, block=False))

            self._skuld = skuld_obj
            skuld_obj.cmd(SkuldCmd(name='set_adaptor', args=self, block=False))

        def set_current_buf_as_tasks(self):
            """Set the contents of current buffer as tasks."""
            tasks = __filter_task_lines__(vim.current.buffer[:])
            tasks = [self._deco_task_line(t) for t in tasks]
            self._skuld.cmd(SkuldCmd(name='set_tasks',
                                     args=tasks,
                                     block=False))

        def display_tasks(self):
            """Display the tasks in a new window. Return nothing."""
            skuld_tab, skuld_window = \
                __find_vim_window__(self.SKULD_BUFFER_NAME)
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
            vim.command('call SkuldBufOpenHook()')

        def update_buf_content(self, buf=None):
            """Write tasks to a buffer."""
            if buf is None:
                buf = self._find_skuld_buffer()
            if buf is not None and buf.number == vim.current.buffer.number:
                tasks = self._skuld.cmd(SkuldCmd(name='get_tasks',
                                                 args=[],
                                                 block=True))
                cur_task = self._skuld.cmd(SkuldCmd(name='get_cur_task',
                                                    args=[], block=True))
                buf[:] = tasks
                vim.command('sign unplace 1')
                if cur_task >= 0 and cur_task < len(tasks):
                    vim.command(
                        'sign place 1 line={} name=SkuldCurrentTask buffer={}'
                        .format(cur_task + 1, buf.number))

        def remote_notify(self, msg):
            """Display a message remotely."""
            try:
                notify_cmd = vim.vars['skuld_notify_cmd']
            except KeyError:
                notify_cmd = None
            if notify_cmd is not None and len(notify_cmd) > 0:
                os.system(notify_cmd + ' ' + shell_quote(msg))
            else:
                remote_cmd = ("<c-\\><c-n>"
                              + ":echohl WarningMsg | echo ''{0}''"
                              + " | echohl None "
                              + " | call foreground() "
                              + " | SkuldBufUpdate<cr>").format(msg)
                vim_cmd = "call remote_send('{0}', '{1}')".format(
                    self._vim_server_name, remote_cmd)
                sys_cmd = "gvim --cmd {0} --cmd qa".format(shell_quote(vim_cmd))
                os.system(sys_cmd)

        def start_timer(self, cur_task):
            """Shortcut for starting the Skuld timer."""
            self._skuld.cmd(SkuldCmd(name='start_timer',
                                     args=cur_task, block=False))

        def stop_timer(self):
            """Shortcut for stopping the Skuld timer."""
            self._skuld.cmd(SkuldCmd(name='stop_timer',
                                     args=None, block=False))

        def timer_enabled(self):
            """Shortcut for getting the timer state. Return True or False."""
            return self._skuld.cmd(SkuldCmd(name='timer_enabled',
                                            args=None, block=True))

        def switch_task(self, task_id):
            """Shortcut for switching current task."""
            self._skuld.cmd(SkuldCmd(name='switch_task',
                                     args=task_id, block=False))

        def start_task(self, task_id):
            """Shortcut for starting a task right away."""
            if self.timer_enabled():
                self._skuld.cmd(SkuldCmd(name='switch_task',
                                         args=task_id, block=False))
                self.update_buf_content()
            else:
                self._skuld.cmd(SkuldCmd(name='start_timer',
                                         args=task_id, block=False))

        def get_state(self):
            """
            Shortcut for accessing the current state of Skuld.

            Return a string description.

            """
            return self._skuld.cmd(SkuldCmd(name='get_state',
                                            args=None, block=True))

        def _find_skuld_buffer(self):
            for b in vim.buffers:
                if b.name.endswith(self.SKULD_BUFFER_NAME):
                    return b
            return None

        def _deco_task_line(self, line):
            if line.rfind(self.SKULD_TASK_SEPERATOR) >= 0:
                return line
            else:
                line_width = vim.strwidth(line)
                if line_width < 29:
                    line += ' ' * (29 - line_width)
                return line + self.SKULD_TASK_SEPERATOR

    # ================== helper functions ==================

    def __str_diff_time__(time1, time2):
        rem_time = int(time1 - time2)
        rem_min = rem_time // 60
        rem_sec = rem_time % 60
        return "{:0>2}:{:0>2}".format(rem_min, rem_sec)

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

    # ================== main routine ==================

    global skuld_adaptor
    skuld_adaptor = SkuldVimAdaptor()


if __name__ == '__main__':
    skuld_adaptor = None
    skuld_closure()
    del skuld_closure
