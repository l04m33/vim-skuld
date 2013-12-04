if exists("g:loaded_skuld") && g:loaded_skuld
    finish
endif
let g:loaded_skuld = 1

pyfile skuld.py

command -nargs=0 SkuldBufOpen    :py skuld_adaptor.display_tasks()
command -nargs=0 SkuldTaskUpdate :py skuld_adaptor.set_current_buff_as_tasks()

noremap <leader>td :SkuldBufOpen<cr>

function! SkuldSetBufType()
    setlocal nomodified
    setlocal buftype=nofile
    setlocal bufhidden=hide
    setlocal noswapfile
endfunction

augroup SkuldBufAu
    autocmd!
    autocmd BufEnter             \[Skuld\ Tasks\] SkuldBufOpen
    autocmd BufLeave,InsertLeave \[Skuld\ Tasks\] SkuldTaskUpdate
augroup end
