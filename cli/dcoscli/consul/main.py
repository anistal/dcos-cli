import json
import os
import sys
import time

import dcoscli
import docopt
import pkg_resources
from dcos import cmds, consul, emitting, http, jsonitem, marathon, options, util
from dcos.errors import DCOSException
from dcoscli import tables
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage

emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("consul"),
        argv=argv,
        version='dcos-consul version {}'.format(dcoscli.version))

    http.silence_requests_warnings()

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: all the supported commands
    :rtype: list of dcos.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['consul', 'status', 'leader'],
            arg_keys=[],
            function=_status_leader),
        cmds.Command(
            hierarchy=['consul', 'status', 'peers'],
            arg_keys=[],
            function=_status_peers),
        cmds.Command(
            hierarchy=['consul', 'keyvalue', 'get'],
            arg_keys=['<key>'],
            function=_keyvalue_get),
        cmds.Command(
            hierarchy=['consul', 'keyvalue', 'set'],
            arg_keys=['<key>', '<value>'],
            function=_keyvalue_set)
    ]

def _status_leader():
    consul_manager = _get_consul_manager()
    json = consul_manager.status_leader()
    emitter.publish(json)
    return 0

def _status_peers():
    consul_manager = _get_consul_manager()
    json = consul_manager.status_peers()
    emitter.publish(json)
    return 0

def _keyvalue_get(key):
    consul_manager = _get_consul_manager()
    json = consul_manager.keyvalue_get(key)
    emitter.publish(json)
    return 0

def _keyvalue_set(key, value):
    consul_manager = _get_consul_manager()
    result = consul_manager.keyvalue_set(key, value)
    emitter.publish(result)
    return 0

def _get_consul_url():
    """
    :returns: consul base url
    :rtype: str
    """
    config = util.get_config()
    consul_url = config.get("package.consul_url")
    consul_url = "http://localhost:8500"
    if consul_url is None:
        consul_url = util.get_config_vals(['core.dcos_url'], config)[0]
    return consul_url


def _get_consul_manager():
    """Returns type of consul manager to use

    :returns: ConsulManager instance
    :rtype: ConsulManager
    """

    consul_url = _get_consul_url()
    return consul.Consul(consul_url)