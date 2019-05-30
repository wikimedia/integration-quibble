import logging
from shutil import copyfile

log = logging.getLogger(__name__)


def copylog(src, dest):
    log.info('Copying %s to %s' % (src, dest))
    copyfile(src, dest)
