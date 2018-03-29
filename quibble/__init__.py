import logging
import os
import os.path


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
