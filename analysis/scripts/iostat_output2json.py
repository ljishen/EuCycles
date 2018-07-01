#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from datetime import timedelta
from numbers import Number

import argparse
import json
import os
import re
import typing


def __get_args():
    parser = argparse.ArgumentParser(
        description='Extract outputs of iostat to json file based on the \
                     corresponding perf stat profiles')
    parser.add_argument(
        '-d', '--work_dir', metavar='DIR', type=str,
        help='Path of the working directory',
        required=True)

    return parser.parse_args()


TIME_FORMAT_PYBEN_NIO = '%Y-%m-%d %H:%M:%S'  # e.g. 2018-06-29 21:12:01
TIME_FORMAT_PERF = '%m/%d/%Y %I:%M:%S %p'  # e.g. 06/29/2018 06:49:21 PM


def __get_time_str_in_perf_profile(
        time_str_in_pyben_nio: str,
        delta_in_sec: int) -> str:
    d_time = datetime.strptime(
        time_str_in_pyben_nio, TIME_FORMAT_PYBEN_NIO) + \
        timedelta(seconds=delta_in_sec)
    return d_time.strftime(TIME_FORMAT_PERF)


IOSTAT_CONTENT_CACHE = {}  # type: typing.Dict[str, typing.List[str]]


def __calc_sum_of_busyness(
        start_time_str: str,
        end_time_str: str,
        iostat_profiles_dir: str,
        host_ip: str) -> float:
    iostat_log_filename = 'iostat.log.' + host_ip
    if host_ip not in IOSTAT_CONTENT_CACHE:
        with open(iostat_profiles_dir + '/' + iostat_log_filename,
                  'rt') as fobj:
            IOSTAT_CONTENT_CACHE[host_ip] = fobj.readlines()

    in_section = False
    num_in_cur_line = False
    sum_of_busyness = 0.0
    for line in IOSTAT_CONTENT_CACHE[host_ip]:
        if not in_section:
            if start_time_str in line:
                in_section = True
            continue

        if num_in_cur_line:
            idle_percentage = float(line.split()[-1])
            # print(idle_percentage)
            sum_of_busyness += 100 - idle_percentage
            num_in_cur_line = False

        if '%idle' in line:
            num_in_cur_line = True
            continue

        if end_time_str in line:
            return sum_of_busyness

    raise RuntimeError('Unable to find the end timestamp %r \
in iostat log file %r' % (end_time_str, iostat_log_filename))


PATTERN_PYBEN_NIO_TIME = re.compile(
    r'(\d{4}\-\d{2}\-\d{2}\s\d{2}:\d{2}:\d{2}),\d{3}\s\|')
PATTERN_PYBEN_NIO_IP = re.compile(r'\-\-bind\s([\d\.]+)')


def __extract_from_perf_profile(perf_profile_file):
    with open(perf_profile_file, 'rt') as fobj:
        content = fobj.read()
        matchobj = PATTERN_PYBEN_NIO_TIME.findall(content)

        raw_times = matchobj
        if len(raw_times) < 2:
            raise RuntimeError("Unable to extract timestamps from %r" %
                               perf_profile_file)

        host_ip = PATTERN_PYBEN_NIO_IP.search(content).group(1)

        return raw_times, host_ip


def __get_result_file(work_dir):
    for entry in os.scandir(work_dir):
        if entry.name.endswith('.json'):
            return work_dir + '/' + entry.name

    raise RuntimeError(
        'Cannot find json result file in work_dir %r' % work_dir)


PATTERN_PERCENTAGE = re.compile(r'\d+%')
PATTERN_NUM_SERVS = re.compile(r'(\d+)servs')
PATTERN_TEST_INDEX = re.compile(r'%_(\d+)')


def main():
    cmd_args = __get_args()

    logs_dir = cmd_args.work_dir + '/logs'
    iostat_profiles_dir = logs_dir + '/iostat'

    if not os.path.isdir(iostat_profiles_dir):
        raise RuntimeError("work_dir does not contain folder 'logs/iostat'. \
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
        raw_times, host_ip = __extract_from_perf_profile(perf_profile_file)

        start_time_str = __get_time_str_in_perf_profile(raw_times[0], -1)
        end_time_str = __get_time_str_in_perf_profile(raw_times[-1], 2)
        print(perf_profile_file,
              ': [', start_time_str,
              '-',
              end_time_str, ']')

        sum_of_busyness = __calc_sum_of_busyness(
            start_time_str,
            end_time_str,
            iostat_profiles_dir,
            host_ip)

        num_servs_data = __json_get_data_in_path(
            result_file,
            data,
            PATTERN_PERCENTAGE.search(filename).group(0),
            PATTERN_NUM_SERVS.search(filename).group(1))

        test_idx = int(PATTERN_TEST_INDEX.search(filename).group(1)) - 1
        if 'client' in filename:
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

    result_file_bak = result_file + '.bak'
    print('Backup result file to: ', result_file_bak)
    os.rename(result_file, result_file_bak)
    with open(result_file, 'w') as json_fobj:
        json.dump(data, json_fobj, indent=4, sort_keys=True)
    print('Extraction completed successfully.')


def __json_get_data_in_path(result_file, data_root, *path):
    data = data_root
    for key in path:
        if key not in data:
            raise RuntimeError("result file %r does not have \
                               data in path %r" %
                               (result_file, path))
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
