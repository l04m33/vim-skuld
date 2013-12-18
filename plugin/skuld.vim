let g:skuld_script_path = expand("<sfile>:h")
let g:skuld_script = g:skuld_script_path . '/skuld.py'

command! -nargs=0 SkuldLoad :call SkuldLoad()

augroup SkuldAu
    autocmd!
    autocmd VimEnter * SkuldLoad
augroup end

function! SkuldLoad()

    if !exists("v:servername") || v:servername == ''
        echohl WarningMsg
        echom  "Remote calls are not available, Skuld won't work."
        echohl None
        return
    endif

    if exists("g:loaded_skuld") && g:loaded_skuld
        return
    endif
    let g:loaded_skuld = 1

"    let g:skuld_notify_cmd = "notify-send"
"    let g:skuld_progress_symbol = "✔"
"    let g:skuld_work_period = 25
"    let g:skuld_rest_period = 5
"    let g:skuld_long_rest_period = 15
"    let g:skuld_max_work_streak = 4

    pyfile `=g:skuld_script`

    command! -nargs=1 SkuldStartTimer   :py skuld_adaptor.start_timer(int(<args>))
    command! -nargs=0 SkuldStopTimer    :py skuld_adaptor.stop_timer()
    command! -nargs=1 SkuldSwitchTask   :py skuld_adaptor.switch_task(int(<args>))
    command! -nargs=0 SkuldGetState     :py print(skuld_adaptor.get_state())
    command! -nargs=0 SkuldBufOpen      :py skuld_adaptor.display_tasks()
    command! -nargs=0 SkuldBufUpdate    :py skuld_adaptor.update_buf_content()
    command! -nargs=0 SkuldTaskUpdate   :py skuld_adaptor.set_current_buf_as_tasks()

    " Called in skuld.py
    function! SkuldBufOpenHook()
        call SkuldMapBufKeys()
        call SkuldSetBufHilight()
    endfunction

    function! SkuldMapBufKeys()
    endfunction

    function! SkuldSetBufHilight()
        syn match skuldSeperator ' |'
        syn match skuldProgress  '\(?:\|\)[^|]\+$'
        syn match skuldTask      '^[^ \t|]\+'
        hi link skuldSeperator Comment
        hi link skuldProgress  Comment
        hi link skuldTask      Function
    endfunction

    augroup SkuldBufAu
        autocmd!
        autocmd BufEnter    \[Skuld\ Tasks\] SkuldBufUpdate
        autocmd BufLeave    \[Skuld\ Tasks\] SkuldTaskUpdate
        autocmd InsertLeave \[Skuld\ Tasks\] SkuldTaskUpdate
        autocmd InsertLeave \[Skuld\ Tasks\] SkuldBufUpdate
    augroup end

    noremap <leader>sb :SkuldBufOpen<cr>
    noremap <leader>ss :SkuldGetState<cr>

endfunction
