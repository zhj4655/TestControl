#
# OtterTune - fabfile.py
#
# Copyright (c) 2017-18, Carnegie Mellon University Database Group
#
'''
Created on Mar 23, 2018

@author: bohan
'''
import sys
import json
import logging
import time
import os.path
import re
from multiprocessing import Process
from fabric.api import (env, local, task, lcd)
from fabric.state import output as fabric_output

LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)
Formatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")  # pylint: disable=invalid-name

# print the log
ConsoleHandler = logging.StreamHandler(sys.stdout)  # pylint: disable=invalid-name
ConsoleHandler.setFormatter(Formatter)
LOG.addHandler(ConsoleHandler)

# Fabric environment settings
env.hosts = ['localhost']
fabric_output.update({
    'running': True,
    'stdout': True,
})

with open('driver_config.json', 'r') as f:
    CONF = json.load(f)



@task
def restart_database():
    if CONF['database_type'] == 'postgres':
        cmd = 'sudo service postgresql restart'
    elif CONF['database_type'] == 'mysql':
        cmd = 'sudo service mysqld restart'
    else:
        raise Exception("Database Type {} Not Implemented !".format(CONF['database_type']))
    local(cmd)



@task
def change_conf():
    next_conf = 'next_config'
    if CONF['database_type'] == 'postgres':
        cmd = 'sudo python PostgresConf.py {} {}'.format(next_conf, CONF['database_conf'])
    elif CONF['database_type'] == 'mysql':
        cmd = 'sudo python MysqlConf.py {} {}'.format(next_conf, CONF['database_conf'])
    else:
        raise Exception("Database Type {} Not Implemented !".format(CONF['database_type']))
    local(cmd)


@task
def run_oltpbench():
    cmd = "./oltpbenchmark -b {} -c {} --execute=true -s 5 -o outputfile".\
          format(CONF['oltpbench_workload'], CONF['oltpbench_config'])
    with lcd(CONF['oltpbench_home']):  # pylint: disable=not-context-manager
        local(cmd)


@task
def run_oltpbench_bg():
    cmd = "./oltpbenchmark -b {} -c {} --execute=true -s 5 -o outputfile > {} 2>&1 &".\
          format(CONF['oltpbench_workload'], CONF['oltpbench_config'], CONF['oltpbench_log'])
    with lcd(CONF['oltpbench_home']):  # pylint: disable=not-context-manager
        local(cmd)


@task
def run_controller():
    cmd = 'gradle run -PappArgs="-c {} -d output/" --no-daemon'.\
          format(CONF['controller_config'])
    with lcd("../controller"):  # pylint: disable=not-context-manager
        local(cmd)


@task
def stop_controller():
    pid = int(open('../controller/pid.txt').read())
    cmd = 'sudo kill -2 {}'.format(pid)
    with lcd("../controller"):  # pylint: disable=not-context-manager
        local(cmd)



@task
def free_cache():
    cmd = 'sync; sudo bash -c "echo 1 > /proc/sys/vm/drop_caches"'
    local(cmd)


@task
def add_udf():
    cmd = 'sudo python ./LatencyUDF.py ../controller/output/'
    local(cmd)


def _ready_to_start_controller():
    return (os.path.exists(CONF['oltpbench_log']) and
            'Warmup complete, starting measurements'
            in open(CONF['oltpbench_log']).read())


def _ready_to_shut_down_controller():
    pid_file_path = '../controller/pid.txt'
    return (os.path.exists(pid_file_path) and os.path.exists(CONF['oltpbench_log']) and
            'Output into file' in open(CONF['oltpbench_log']).read())


@task
def preprocess_result():
#../controller/output/summary.json
    filename = '../controller/output/summary.json'
    file_in = open(filename, "r")
    json_data = json.load(file_in)
    file_in.close()

    # if json_data["database_version"] == "5.7.23-0ubuntu0.16.04.1":
    #     json_data["database_version"] = "5.7"
    # file_out = open(filename, "w")
    # file_out.write(json.dumps(json_data))
    # file_out.close()

    start_time = json_data["start_time"]
    cmd = 'cp ../controller/output ../results/{} -r'.format(start_time)
    local(cmd)

    file_in = open('filenum','r')
    filenum = file_in.read()
    file_in.close()
    filenum = int(filenum)
    resfile = 'outputfile.'+str(filenum)+'.res'
    cmd = 'cp {}/results/{} ../results/{}/outputfile.res'.format(CONF['oltpbench_home'], resfile, start_time)
    local(cmd)
    filenum = filenum + 1
    file_out = open('filenum', 'w')
    file_out.write(str(filenum))
    file_out.close()


@task
def reload_data():
    cmd = 'sudo rm -rf {}/tpcc'.format(CONF['database_disk'])
    local(cmd)
    cmd = 'sudo cp -r {}/tpcc {}/tpcc'.format(CONF['backup'], CONF['database_disk'])
    local(cmd)
    cmd = 'sudo chown -R mysql:mysql {}'.format(CONF['database_disk'])
    local(cmd)


@task
def loop(num):

    # free cache
    free_cache()

    # reload data
    if num % 6 == 0:
        reload_data()

    # restart database
    restart_database()


    # run oltpbench as a background job
    run_oltpbench_bg()

    # run controller from another process
    p = Process(target=run_controller, args=())
    while not _ready_to_start_controller():
        pass
    p.start()
    while not _ready_to_shut_down_controller():
        pass

    # stop the experiment
    stop_controller()

    p.join()

    # add user defined target objective
    # add_udf()

    preprocess_result()


    # change config
    if num % 3 ==0:
        change_conf()


@task
def run_loops(max_iter=1):
    for i in range(int(max_iter)):
        LOG.info('The %s-th Loop Starts / Total Loops %s', i + 1, max_iter)
        loop(i)
        LOG.info('The %s-th Loop Ends / Total Loops %s', i + 1, max_iter)
