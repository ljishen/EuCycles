#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from datetime import timedelta
from enum import Enum
from numbers import Number

import argparse
import json
import os
import re
import typing


def _iostat_calc_sum_of_busyness(
        start_time_str: str,
        end_time_str: str,
        cpustat_log_file: str,
        cachelines: typing.Dict[str, typing.List[str]]) -> float:

    in_section = False
    num_in_cur_line = False
    sum_of_busyness = 0.0
    for line in cachelines:
        if not in_section:
            if start_time_str in line:
                in_section = True
            continue

        if num_in_cur_line:
            idle_percentage = float(line.split()[-1])
            # print(idle_percentage)
            sum_of_busyness += 100 - idle_percentage
            num_in_cur_line = False
            continue

        if '%idle' in line:
            num_in_cur_line = True
            continue

        if end_time_str in line:
            return sum_of_busyness

    raise __error_timestamp_not_found(
        in_section,
        start_time_str,
        end_time_str,
        cpustat_log_file)


def __error_timestamp_not_found(
        in_section,
        start_time_str,
        end_time_str,
        cpustat_log_file):
    err_msg_tmpl = 'Unable to find the {} timestamp {!r} \
in iostat log file {!r}'
    if not in_section:
        err_msg = err_msg_tmpl.format(
            'start', start_time_str, cpustat_log_file)
    else:
        err_msg = err_msg_tmpl.format(
            'end', end_time_str, cpustat_log_file)

    return RuntimeError(err_msg)


def _mpstat_calc_sum_of_busyness(
        start_time_str: str,
        end_time_str: str,
        cpustat_log_file: str,
        cachelines: typing.Dict[str, typing.List[str]]) -> float:

    in_section = False
    sum_of_busyness = 0.0
    for line in cachelines:
        if not in_section:
            if start_time_str not in line:
                continue
            in_section = True

        if end_time_str in line:
            return sum_of_busyness

        if 'all' in line:
            idle_percentage = float(line.split()[-1])
            # print(idle_percentage)
            sum_of_busyness += 100 - idle_percentage

    raise __error_timestamp_not_found(
        in_section,
        start_time_str,
        end_time_str,
        cpustat_log_file)


KEY_FUNC = 'func'
KEY_TIME_FORMAT = 'time_format'


class _CPUStat(Enum):
    iostat = {KEY_FUNC: _iostat_calc_sum_of_busyness,
              # e.g. 06/29/2018 06:49:21 PM
              KEY_TIME_FORMAT: '%m/%d/%Y %I:%M:%S %p'}
    mpstat = {KEY_FUNC: _mpstat_calc_sum_of_busyness,
              KEY_TIME_FORMAT: '%I:%M:%S %p'}

    def __str__(self):
        return self.name

    @staticmethod
    def from_string(in_str):
        """Convert input string to instance of _CPUStat."""
        try:
            return _CPUStat[in_str]
        except KeyError:
            raise ValueError()


def __get_args():
    parser = argparse.ArgumentParser(
        description='Extract outputs of cpustat to json file based on the \
                     corresponding perf stat profiles.')
    parser.add_argument(
        '-d', '--work_dir', metavar='DIR', type=str,
        help='Path of the working directory',
        required=True)
    parser.add_argument(
        '-s', '--cpustat', type=_CPUStat.from_string,
        choices=list(_CPUStat),
        help='Name of the CPU statistic tool',
        required=True)

    return parser.parse_args()


TIME_FORMAT_PYBEN_NIO = '%Y-%m-%d %H:%M:%S'  # e.g. 2018-06-29 21:12:01


def __convert_time(
        time_str_in_pyben_nio: str,
        delta_in_sec: int,
        cpustat: _CPUStat) -> str:
    d_time = datetime.strptime(
        time_str_in_pyben_nio, TIME_FORMAT_PYBEN_NIO) + \
        timedelta(seconds=delta_in_sec)
    return d_time.strftime(cpustat.value[KEY_TIME_FORMAT])


PATTERN_PYBEN_NIO_TIME = re.compile(
    r'(\d{4}\-\d{2}\-\d{2}\s\d{2}:\d{2}:\d{2}),\d{3}\s\|')
PATTERN_PYBEN_NIO_IP = re.compile(r'\-\-bind\s([\d\.]+)')


def __extract_from_perf_profile(perf_profile_file: str,
                                cpustat: _CPUStat):
    with open(perf_profile_file, 'rt') as fobj:
        content = fobj.read()
        raw_times = PATTERN_PYBEN_NIO_TIME.findall(content)

        if len(raw_times) < 2:
            raise RuntimeError("Unable to extract timestamps from %r" %
                               perf_profile_file)

        matchobj = PATTERN_PYBEN_NIO_IP.search(content)
        if matchobj:
            host_ip = matchobj.group(1)

    # generate the compatible start and end time string before and after
    # 2 seconds of the first and last timestamps in the corresponding perf
    # profile.
    start_time_str = __convert_time(raw_times[0], -2, cpustat)
    end_time_str = __convert_time(raw_times[-1], 3, cpustat)
    print(perf_profile_file,
          ': [', start_time_str,
          '-',
          end_time_str, ']')

    return start_time_str, end_time_str, host_ip


def __get_result_file(work_dir):
    for entry in os.scandir(work_dir):
        if entry.name.endswith('.json'):
            return work_dir + '/' + entry.name

    raise RuntimeError(
        'Cannot find json result file in work_dir %r' % work_dir)


CPUSTAT_CONTENT_CACHE = {}  # type: typing.Dict[str, typing.List[str]]


def main():
    cmd_args = __get_args()

    logs_dir = cmd_args.work_dir + '/logs'
    cpustat_profiles_dir = logs_dir + '/cpustat'

    if not os.path.isdir(cpustat_profiles_dir):
        raise RuntimeError("work_dir does not contain folder 'logs/cpustat'. \
Please check if you are pointing to the correct work_dir.")

    result_file = __get_result_file(cmd_args.work_dir)
    print('Found result file:', result_file)
    with open(result_file, 'rt') as json_fobj:
        data = json.load(json_fobj)

    perf_profile_filenames = \
        sorted([entry.name for entry in os.scandir(logs_dir)
                if entry.is_file() and
                entry.name.endswith('.log')])

    for filename in perf_profile_filenames:
        perf_profile_file = logs_dir + '/' + filename
        (start_time_str,
         end_time_str,
         host_ip) = __extract_from_perf_profile(
             perf_profile_file, cmd_args.cpustat)

        cpustat_log_file = cpustat_profiles_dir + '/cpustat.log.' + host_ip
        if host_ip not in CPUSTAT_CONTENT_CACHE:
            with open(cpustat_log_file, 'rt') as fobj:
                CPUSTAT_CONTENT_CACHE[host_ip] = fobj.readlines()

        sum_of_busyness = cmd_args.cpustat.value[KEY_FUNC](
            start_time_str,
            end_time_str,
            cpustat_log_file,
            CPUSTAT_CONTENT_CACHE[host_ip])

        __update_data(data, filename, sum_of_busyness)

    __backup_and_update(result_file, data)


PATTERN_PERCENTAGE = re.compile(r'\d+%')
PATTERN_NUM_SERVS = re.compile(r'(\d+)servs')
PATTERN_TEST_INDEX = re.compile(r'%_(\d+)')


def __update_data(data, perf_profile_filename, sum_of_busyness):
    num_servs_data = __json_get_data_in_path(
        data,
        PATTERN_PERCENTAGE.search(perf_profile_filename).group(0),
        PATTERN_NUM_SERVS.search(perf_profile_filename).group(1))

    test_idx = int(PATTERN_TEST_INDEX.search(
        perf_profile_filename).group(1)) - 1
    if 'client' in perf_profile_filename:
        __json_update_arr_prop(
            num_servs_data,
            test_idx,
            'busyness',
            'client',
            value=sum_of_busyness)
    else:
        __json_update_arr_prop(
            num_servs_data,
            test_idx,
            'busyness',
            'servers',
            value=[sum_of_busyness])


def __backup_and_update(result_file, data):
    result_file_bak = result_file + '.bak'
    print('Backup result file to: ', result_file_bak)
    os.rename(result_file, result_file_bak)
    with open(result_file, 'w') as json_fobj:
        json.dump(data, json_fobj, indent=4, sort_keys=True)
    print('Extraction completed successfully.')


def __json_get_data_in_path(data_root, *path):
    data = data_root
    for key in path:
        if key not in data:
            raise RuntimeError("result file does not have \
                               data in path %r" % path)
        data = data[key]

    return data


def __json_update_arr_prop(data, idx, *path, value=None):
    obj = data
    for key in path[:-1]:
        if key not in obj:
            obj[key] = {}
        obj = obj[key]

    key = path[-1]
    if key not in obj:
        obj[key] = []

    obj = obj[key]

    if value is not None:
        if len(obj) <= idx or isinstance(value, Number):
            obj.append(value)
        else:
            obj[idx].extend(value)


if __name__ == "__main__":
    main()
