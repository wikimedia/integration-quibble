import json
import os
import signal


def main():
    with open(os.environ['QUIBBLE_TMPFILE'], 'w') as f:
        json.dump({
            'PGUSER': os.environ['PGUSER'],
            'PGPASSWORD': os.environ['PGPASSWORD'],
            'PGDATABASE': os.environ['PGDATABASE'],
            'PID': os.getpid(),
        }, f)
    # Wait for a signal
    signal.pause()


if __name__ == '__main__':
    main()
