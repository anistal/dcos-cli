import collections
import functools
import json

import pystache
import six
from dcos import emitting, http, util
from dcos.errors import (DCOSAuthenticationException,
                         DCOSAuthorizationException, DCOSException,
                         DCOSHTTPException, DefaultError)

from six.moves import urllib

logger = util.get_logger(__name__)

emitter = emitting.FlatEmitter()


class Consul():
    """Implementation of Package Manager using Consul"""

    def __init__(self, consul_url):
        config = util.get_config()
        self._consul_url = consul_url
        self._timeout = config.get('core.timeout')

    def status_leader(self):
        url = self._create_url('v1/status/leader')
        return http.get(url, timeout=self._timeout).json()

    def status_peers(self):
        url = self._create_url('v1/status/peers')
        return http.get(url, timeout=self._timeout).json()

    def keyvalue_get(self, key):
        url = self._create_url('v1/kv/{}'.format(key))
        return http.get(url, timeout=self._timeout).json()

    def keyvalue_set(self, key, value):
        url = self._create_url('v1/kv/{}'.format(key))
        return http.put(url, value).text

    def _create_url(self, path):
        """Creates the url from the provided path.
        :param path: url path
        :type path: str
        :returns: constructed url
        :rtype: str
        """
        return urllib.parse.urljoin(self._consul_url, path)