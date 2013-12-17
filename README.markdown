Introduction
============

Skuld is a [pomodoro timer][1] that runs inside Vim. It can help you track
your tasks in an simple (or stupid) way.

[1]: http://en.wikipedia.org/wiki/Pomodoro_technique

Dependencies
============

Skuld depends on `+python` or `+python3`, as well as `+clientserver`.
Nothing else is needed.

Usage
=====

After a successful installation, these commands are available:

- `SkuldStartTimer <task_id>`   : Start the pomodoro timer
- `SkuldStopTimer`              : Stop the pomodoro timer
- `SkuldSwitchTask <task_id>`   : Switch current task
- `SkuldGetState`               : Display current timer state
- `SkuldBufOpen`                : Open the buffer containing the task list (`[Skuld Tasks]`)
- `SkuldTaskUpdate`             : Update the internal task list according to `[Skuld Tasks]` buffer

`SkuldBufOpen` is mapped to `<leader>sb` by default. You can open a scratch
buffer called `[Skuld Tasks]` using this command, and then write down your
tasks in that buffer, **one task per line**. Whenever you leave insert mode,
or leave the `[Skuld Tasks]` buffer, your tasks will be set automatically.

Once the tasks are set, you can invoke `SkuldStartTimer 0` to start the
timer, indicating that you will be working on the first task. As you may
have noticed, Task IDs start from zero. And you don't need to keep the 
`[Skuld Tasks]` buffer open.

When the pomodoro timer times out, there will be a Vim message signifying
the change of timer state. You can start working or have a break
accordingly. Skuld will append a pomodoro completion symbol, which defaults
to `*`, after the current task, when a working period ends.

You can edit `[Skuld Tasks]` buffer while the timer is running. Edited
tasks will be synchronized automatically once you leave insert mode or
leave the buffer.

Mappings
========

```VimL
    noremap <leader>sb :SkuldBufOpen<cr>
    noremap <leader>ss :SkuldGetState<cr>
```

Settings
========

These variables can be set in you `.vimrc` to override the defaults:

```VimL
    " Pomodoro completion symbol
    let g:skuld_progress_symbol = '*'

    " Pomodoro working period (in minutes)
    let g:skuld_work_period = 25

    " Pomodoro resting period (in minutes)
    let g:skuld_rest_period = 5

    " Pomodoro long resting period (in minutes)
    let g:skuld_long_rest_period = 15

    " Max working streak before long resting
    let g:skuld_max_work_streak = 4

    " Notification command
    let g:skuld_notify_cmd = 'notify-send'
```

License
=======

This Vim plugin is licensed under the terms of [the MIT license][2].

[2]: http://l04m33.mit-license.org/

