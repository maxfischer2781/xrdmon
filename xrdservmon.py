#!/usr/bin/python
from __future__ import print_function, division, with_statement
import os
import sys
import glob
import argparse
import subprocess
import pickle
import logging


CLI = argparse.ArgumentParser("Manager for XRootD ServMon")
CLI_TARGET = CLI.add_argument_group("service to monitor")
CLI_TARGET.add_argument('--target-pidpath', help='basepath storing pid files (all.pidpath + name)')
CLI_TARGET.add_argument('--target-port', help='port of xrootd to monitor', default=os.environ.get('XRDSERVERPORT', '1094'))
CLI_INFO = CLI.add_argument_group("information to provide")
CLI_INFO.add_argument('--se-name', help='SE this server belongs to', required=True)
CLI_INFO.add_argument('--report-to', help='hostname or address to send reports to', default='localhost')
CLI_MANAGER = CLI.add_argument_group("manager settings")
CLI_MANAGER.add_argument('--run-path', help='basepath storing pid and state files', default='/tmp')
CLI_MANAGER.add_argument('--log-level', help='Log level to use', default='WARNING')


logging.basicConfig()
APP_LOGGER = logging.getLogger(os.path.basename(__file__))


def validate_process(pid, name):
    """Check whether there is a process with `pid` and `name`"""
    try:
        with open(os.path.join('/proc', str(pid), 'comm')) as proc_comm:
            proc_name = next(proc_comm).strip()
    except (OSError, IOError):
        return False
    return name == proc_name


# What to Monitor
#################
# Todo: make class
def get_targets(target_pidpath):
    """Get the target processes to monitor, as mapping `{pid: (daemon_type, name)}`"""
    targets = {}  # pid => daemon_type, name
    # xrd stores pid as: pidpath/<name>/<daemon_type>.pid
    for daemon_type in ('cmsd', 'xrootd'):
        pid_file = os.path.join(target_pidpath, daemon_type + '.pid')
        try:
            with open(pid_file) as pid_data:
                pid = int(next(pid_data))
        except (OSError, IOError, ValueError) as err:
            APP_LOGGER.warning('failed to read PID file for daemon type %s: %s', daemon_type, err)
        else:
            target_name = os.path.split(os.path.dirname(pid_file))[-1]
            if validate_process(pid, daemon_type):
                targets[pid] = (daemon_type, target_name)
                APP_LOGGER.debug('adding monitor target: type=%s, name=%s, pid=%s', daemon_type, target_name, pid)
            else:
                APP_LOGGER.warning('failed to read PID file for daemon type %s: %s', daemon_type, 'process not running')
    return targets


# How to Monitor
################
# Todo: make class
def format_servmon_targets(se_name, targets):
    """Format targets for the servMon.sh CLI, e.g. `'ALICE::FOO::SE_server_cmsd', '5123'`"""
    return [
        part for target_info in (
            ('%s_%s_%s' % (se_name, target[1], target[0]), str(pid)) for pid, target in targets.items()
        )
        for part in target_info
        ]


def dispatch_monitor(monitor_targets, run_path, se_name, report_to, target_port):
    """Launch separate monitoring process"""
    pid_basename = run_path + 'xrdservom.pid'  # TODO: Unify #1
    command = (
        ['servMon.sh', '-p', pid_basename, '-f']
        + ['%s_xrootd' % se_name]
        + format_servmon_targets(se_name=se_name, targets=monitor_targets)
    )
    command_env = os.environ.copy()
    command_env['MONALISA_HOST'] = report_to
    command_env['XRDSERVERPORT'] = target_port
    APP_LOGGER.debug(
        'starting monitor: cmd=%r, env+=%r',
        "'" + "' '".join(command) +  "'",
        "'" + "':'".join((key + '=' + command_env[key]) for key in ('MONALISA_HOST', 'XRDSERVERPORT')) + "'"
    )
    proc = subprocess.Popen(command, env=command_env)
    return proc


def monitor_pids(run_path):
    """Yield the pid of any running monitoring process"""
    pid_basename = run_path + 'xrdservom.pid'  # TODO: Unify #1
    pid_files = glob.glob(pid_basename + '*')
    for pid_file in pid_files:
        with open(pid_file) as pid:
            pid = int(pid.readline().strip())
        if validate_process(pid, 'perl'):
            APP_LOGGER.debug('monitor exists: pid=%s', pid)
            yield pid
        else:
            APP_LOGGER.debug('monitor defunct: pid=%s', pid)
            os.unlink(pid_file)


# State Glue
#############
# Todo: make class
def store_state(run_path, monitor_targets, monitor_pid):
    """Store targets being monitored"""
    with open(run_path + 'xrdservmon_state.pkl', 'wb') as state_file:
        pickle.dump({'process': sys.executable, 'targets': monitor_targets, 'pid': monitor_pid}, state_file, 0)


def load_state(run_path):
    """Load targets being monitored"""
    try:
        with open(run_path + 'xrdservmon_state.pkl', 'rb') as state_file:
            return pickle.load(state_file)['targets']
    except (IOError, OSError):
        return {}


def ensure_monitor(target_pidpath, target_port, se_name, report_to, run_path):
    """Deploy or validate monitoring process"""
    monitor_targets = get_targets(target_pidpath=target_pidpath)
    current_pids = list(monitor_pids(run_path=run_path))
    # if a valid monitor is already running, don't do anything
    if len(current_pids) == 1:
        if load_state(run_path=run_path) == monitor_targets:
            APP_LOGGER.warning('monitor already running')
            return 0
        APP_LOGGER.warning('replacing outdated monitor')
    if not monitor_targets:
        APP_LOGGER.warning('no targets to monitor')
        return 0
    monitor_proc = dispatch_monitor(monitor_targets=monitor_targets, run_path=run_path, se_name=se_name, report_to=report_to, target_port=target_port)
    store_state(run_path=run_path, monitor_targets=monitor_targets, monitor_pid=monitor_proc.pid)
    return monitor_proc.wait()


def main():
    args = CLI.parse_args()
    options = vars(args)
    log_level = options.pop('log_level')
    try:
        log_level = int(log_level)
    except ValueError:
        log_level = getattr(logging, log_level)
    APP_LOGGER.setLevel(log_level)
    sys.exit(ensure_monitor(**options))

if __name__ == '__main__':
    main()
