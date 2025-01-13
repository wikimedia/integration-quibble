from pymemcache.client.base import Client
from pymemcache.client.hash import HashClient
from pymemcache.client.retrying import RetryingClient
from pymemcache.exceptions import MemcacheUnexpectedCloseError


CONNECT_TIMEOUT = 2.0
SOCKET_TIMEOUT = 2.0
KEY_PREFIX = 'quibble/v0/'


def client(server, retries=3, retry_delay=0.5):
    """
    Returns a memcached client.

    server: Memcached server to use for caching, e.g. 'localhost:11211'.
    Multiple servers can be specified (separated by ',') for
    clustering/failover.
    """

    def new_client(**kwargs):
        servers = server.split(',')
        if len(servers) > 1:
            return HashClient(servers, **kwargs)
        else:
            return Client(server, **kwargs)

    return RetryingClient(
        new_client(
            connect_timeout=CONNECT_TIMEOUT,
            timeout=SOCKET_TIMEOUT,
            key_prefix=KEY_PREFIX,
        ),
        attempts=retries,
        retry_delay=retry_delay,
        retry_for=[MemcacheUnexpectedCloseError],
    )
