def run_sequentially(tasks):
    '''Replace imap_unordered with sequential execution'''
    for func_spec in tasks:
        func = func_spec[0]
        args = func_spec[1:]
        func(*args)
