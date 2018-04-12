from functools import lru_cache
import logging
import os
import os.path
import subprocess


def colored_logging():
    # Color codes http://www.tldp.org/HOWTO/Bash-Prompt-HOWTO/x329.html
    logging.addLevelName(  # cyan
        logging.DEBUG, "\033[36m%s\033[0m" %
        logging.getLevelName(logging.DEBUG))
    logging.addLevelName(  # green
        logging.INFO, "\033[32m%s\033[0m" %
        logging.getLevelName(logging.INFO))
    logging.addLevelName(  # yellow
        logging.WARNING, "\033[33m%s\033[0m" %
        logging.getLevelName(logging.WARNING))
    logging.addLevelName(  # red
        logging.ERROR, "\033[31m%s\033[0m" %
        logging.getLevelName(logging.ERROR))
    logging.addLevelName(  # red background
        logging.CRITICAL, "\033[41m%s\033[0m" %
        logging.getLevelName(logging.CRITICAL))


def use_headless():
    log = logging.getLogger('quibble.use_headless')
    log.info("Display: %s" % os.environ.get('DISPLAY', '<None>'))

    return not bool(os.environ.get('DISPLAY'))


def chromium_flags():
    args = [os.environ.get('CHROMIUM_FLAGS', '')]
    if is_in_docker():
        args.append('--no-sandbox')
    if use_headless():
        args.extend([
            '--headless',
            '--disable-gpu',
            '--remote-debugging-port=9222',
        ])

    log = logging.getLogger('quibble.chromium_flags')
    log.debug("Flags: %s" % args)
    return ' '.join(args)


def is_in_docker():
    return os.path.exists('/.dockerenv')


@lru_cache(maxsize=1)
def php_is_hhvm():
    return b'HipHop' in subprocess.check_output(['php', '--version'])
