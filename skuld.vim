if exists("g:loaded_skuld") && g:loaded_skuld
    finish
endif
let g:loaded_skuld = 1

pyfile <sfile>:h/skuld.py

command -nargs=0 SkuldBufOpen    :py skuld_adaptor.display_tasks()
command -nargs=0 SkuldBufUpdate  :py skuld_adaptor.update_buf_content()
command -nargs=0 SkuldTaskUpdate :py skuld_adaptor.set_current_buf_as_tasks()

function! SkuldMapBufKeys()
endfunction

augroup SkuldBufAu
    autocmd!
    autocmd BufEnter    \[Skuld\ Tasks\] SkuldBufUpdate
    autocmd BufLeave    \[Skuld\ Tasks\] SkuldTaskUpdate
    autocmd InsertLeave \[Skuld\ Tasks\] SkuldTaskUpdate
    autocmd InsertLeave \[Skuld\ Tasks\] SkuldBufUpdate
augroup end
