"""
Usage:
    dcos app add
    dcos app info
    dcos app list
    dcos app remove [--force] <app-id>
    dcos app show [--app-version=<app-version>] <app-id>

Options:
    -h, --help                   Show this screen
    --version                    Show version
    --force                      This flag disable checks in Marathon during
                                 update operations.
    --app-version=<app-version>  This flag specifies the application version to
                                 use for the command. The application version
                                 (<app-version>) can be specified as an
                                 absolute value or as relative value. Absolute
                                 version values must be in ISO8601 date format.
                                 Relative values must be specified as a
                                 negative integer and they represent the
                                 version from the currently deployed
                                 application definition.
"""
import os
import sys

import docopt
from dcos.api import (config, constants, emitting, errors, marathon, options,
                      util)

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    err = util.configure_logger_from_environ()
    if err is not None:
        emitter.publish(err)
        return 1

    args = docopt.docopt(
        __doc__,
        version='dcos-app version {}'.format(constants.version))

    if not args['app']:
        emitter.publish(options.make_generic_usage_error(__doc__))
        return 1

    if args['info']:
        return _info()

    if args['add']:
        return _add()

    if args['list']:
        return _list()

    if args['remove']:
        return _remove(args['<app-id>'], args['--force'])

    if args['show']:
        return _show(args['<app-id>'], args['--app-version'])

    emitter.publish(options.make_generic_usage_error(__doc__))
    return 1


def _info():
    """
    :returns: Process status
    :rtype: int
    """

    emitter.publish('Deploy and manage applications on Apache Mesos')
    return 0


def _add():
    """
    :returns: Process status
    :rtype: int
    """

    # Check that stdin is not tty
    if sys.stdin.isatty():
        # We don't support TTY right now. In the future we will start an editor
        emitter.publish(
            "We currently don't support reading from the TTY. Please specify "
            "an application JSON.\n"
            "E.g. dcos app add < app_resource.json")
        return 1

    application_resource, err = util.load_jsons(sys.stdin.read())
    if err is not None:
        emitter.publish(err)
        return 1

    # Add application to marathon
    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))
    err = client.add_app(application_resource)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def _list():
    """
    :returns: Process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    apps, err = client.get_apps()
    if err is not None:
        emitter.publish(err)
        return 1

    if not apps:
        emitter.publish("No applications to list.")

    for app in apps:
        emitter.publish(app['id'])

    return 0


def _remove(app_id, force):
    """
    :param app_id: ID of the app to remove
    :type app_id: str
    :param force: Whether to override running deployments.
    :type force: bool
    :returns: Process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    err = client.remove_app(app_id, force)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def _show(app_id, version):
    """Show details of a Marathon application.

    :param app_id: The id for the application
    :type app_id: str
    :param version: The version, either absolute (date-time) or relative
    :type version: str
    :returns: Process status
    :rtype: int
    """

    client = marathon.create_client(
        config.load_from_path(
            os.environ[constants.DCOS_CONFIG_ENV]))

    if version is not None:
        version, err = _calculate_version(client, app_id, version)
        if err is not None:
            emitter.publish(err)
            return 1

    app, err = client.get_app(app_id, version=version)
    if err is not None:
        emitter.publish(err)
        return 1

    emitter.publish(app)

    return 0


def _calculate_version(client, app_id, version):
    """
    :param client: Marathon client
    :type client: dcos.api.marathon.Client
    :param app_id: The ID of the application
    :type app_id: str
    :param version: Relative or absolute version or None
    :type version: str
    :returns: The absolute version as an ISO8601 date-time; Error otherwise
    :rtype: (str, Error)
    """

    # First let's try to parse it as a negative integer
    value, err = _parse_int(version)
    if err is None and value < 0:
        value = -1 * value
        # We have a negative value let's ask Marathon for the last abs(value)
        versions, err = client.get_app_versions(app_id, value + 1)
        if err is not None:
            return (None, err)

        if len(versions) <= value:
            # We don't have enough versions. Return an error.
            msg = "Application {!r} only has {!r} version(s)."
            return (
                None,
                errors.DefaultError(msg.format(app_id, len(versions), value))
            )
        else:
            return (versions[value], None)
    elif err is None:
        return (
            None,
            errors.DefaultError(
                'Relative versions must be negative: {}'.format(version))
        )
    else:
        # Let's assume that we have an absolute version
        return (version, None)


def _parse_int(string):
    """
    :param string: String to parse as an integer
    :type string: str
    :returns: The interger value of the string
    :rtype: (int, Error)
    """

    try:
        return (int(string), None)
    except:
        error = sys.exc_info()[0]
        logger = util.get_logger(__name__)
        logger.error(
            'Unhandled exception while parsing string as int: %r -- %r',
            string,
            error)
        return (None, errors.DefaultError('Error parsing string as int'))
