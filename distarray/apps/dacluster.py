#!/usr/bin/env python
# encoding: utf-8
# ---------------------------------------------------------------------------
#  Copyright (C) 2008-2014, IPython Development Team and Enthought, Inc.
#  Distributed under the terms of the BSD License.  See COPYING.rst.
# ---------------------------------------------------------------------------
"""
Start, stop and manage a IPython.parallel cluster. `dacluster` can take
all the commands IPython's `ipcluster` can, and a few extras that are
distarray specific.
"""

from __future__ import print_function

import argparse
import sys
from time import sleep
from subprocess import Popen, PIPE

from distarray.externals import six
from distarray.context import DISTARRAY_BASE_NAME
from distarray.cleanup import cleanup, get_local_keys


if six.PY2:
    ipcluster_cmd = 'ipcluster'
elif six.PY3:
    ipcluster_cmd = 'ipcluster3'
else:
    raise NotImplementedError("Not run with Python 2 *or* 3?")


def start(n=4, engines=None, **kwargs):
    """Convenient way to start an ipcluster for testing.

    Doesn't exit until the ipcluster prints a success message.
    """
    if engines is None:
        engines = "--engines=MPIEngineSetLauncher"

    cluster = Popen([ipcluster_cmd, 'start', '-n', str(n), engines],
                    stdout=PIPE, stderr=PIPE)

    started = "Engines appear to have started successfully"
    running = "CRITICAL | Cluster is already running with"
    while True:
        line = cluster.stderr.readline().decode()
        if not line:
            break
        print(line, end='')
        if (started in line):
            break
        elif (running in line):
            raise RuntimeError("ipcluster is already running.")


def stop(**kwargs):
    """Convenient way to stop an ipcluster."""
    stopping = Popen([ipcluster_cmd, 'stop'], stdout=PIPE, stderr=PIPE)

    stopped = "Stopping cluster"
    not_running = ("CRITICAL | Could not read pid file, cluster "
                   "is probably not running.")
    while True:
        line = stopping.stderr.readline().decode()
        if not line:
            break
        print(line, end='')
        if (stopped in line) or (not_running in line):
            break


def restart(n=4, engines=None, **kwargs):
    """Convenient way to restart an ipcluster."""
    stop()

    started = False
    while not started:
        sleep(2)
        try:
            start(n=n, engines=engines)
        except RuntimeError:
            pass
        else:
            started = True

_RESET_ENGINE_DISTARRAY = '''
from sys import modules
orig_mods = set(modules)
for m in modules.copy():
    if m.startswith('distarray'):
        del modules[m]
deleted_mods = sorted(orig_mods - set(modules))
'''


def clear(**kwargs):
    from IPython.parallel import Client
    c = Client()
    dv = c[:]
    dv.execute(_RESET_ENGINE_DISTARRAY, block=True)
    mods = dv['deleted_mods']
    print("The following modules were removed from the engines' namespaces:")
    for mod in mods[0]:
        print('    ' + mod)
    dv.clear()


def dump(**kwargs):
    """ Print out key names that exist on the engines. """
    from IPython.parallel import Client
    c = Client()
    view = c[:]
    targets_from_key = get_local_keys(view=view, prefix=DISTARRAY_BASE_NAME)
    num_keys = len(targets_from_key)
    print('*** %d ENGINE KEYS ***' % (num_keys))
    for key, targets in sorted(targets_from_key):
        print('%s : %r' % (key, targets))


def purge(**kwargs):
    """ Remove keys from the engine namespaces. """
    print('Purging keys from engines...')
    from IPython.parallel import Client
    c = Client()
    view = c[:]
    cleanup(view=view, prefix=DISTARRAY_BASE_NAME)


def main():
    main_description = """
    Start, stop and manage a IPython.parallel cluster. `dacluster` can take
    all the commands IPython's `ipcluster` can, and a few extras that are
    distarray specific. For details on a subcommand, try `dacluster
    <subcommand> --help`.
    """
    parser = argparse.ArgumentParser(description=main_description)

    # Print help if no command line args are supplied
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    subparsers = parser.add_subparsers()

    start_description = """
    Start a new IPython.parallel cluster.
    """

    stop_description = """
    Stop a IPython.parallel cluster.
    """

    restart_description = """
    Restart a IPython.parallel cluster.
    """

    clear_description = """
    Clear the namespace and imports on the cluster. This should be the
    same as restarting the engines, but faster.
    """

    purge_description = """
    Clear all the DistArray objects from the engines. This sometimes
    fails to delete all keys.
    """

    dump_description = """
    Print out key names that exist on the engines.
    """

    # subparses for all our commands
    parser_start = subparsers.add_parser('start',
                                         description=start_description)
    parser_stop = subparsers.add_parser('stop', description=stop_description)
    parser_restart = subparsers.add_parser('restart',
                                           description=restart_description)
    parser_clear = subparsers.add_parser('clear',
                                         description=clear_description)
    parser_purge = subparsers.add_parser('purge',
                                         description=purge_description)
    parser_dump = subparsers.add_parser('dump', description=dump_description)

    engine_help = """
    Number of engines to start.
    """

    # Add some optional arguments for `start` and `restart`
    parser_start.add_argument('-n', '--n', type=int, nargs='?', default=4,
                              help=engine_help)
    parser_restart.add_argument('-n', '--n', type=int, nargs='?', default=4,
                                help=engine_help)

    # set the functions each command should use
    parser_start.set_defaults(func=start)
    parser_stop.set_defaults(func=stop)
    parser_restart.set_defaults(func=restart)
    parser_clear.set_defaults(func=clear)
    parser_purge.set_defaults(func=purge)
    parser_dump.set_defaults(func=dump)

    # run it
    args = parser.parse_args()
    args.func(**vars(args))

if __name__ == '__main__':
    main()
