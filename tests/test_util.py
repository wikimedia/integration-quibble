import quibble.util


def test_parallel_run_accepts_an_empty_list_of_tasks():
    quibble.util.parallel_run([])
    assert True
