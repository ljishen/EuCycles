#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import locale
import os
import re


def __get_args():
    parser = argparse.ArgumentParser(
        description='Script for extracting numbers from the output of perfing \
        the Pyben-nio servers and client.')
    parser.add_argument(
        '-s', '--size', type=str,
        help='Size of data I/O in the test',
        required=True)
    parser.add_argument(
        '-i', '--index', type=int,
        help='The index of the test',
        required=True)
    parser.add_argument(
        '-n', '--num_servs', type=int,
        help='Number of servers used in the test',
        required=True)
    parser.add_argument(
        '-f', '--result_filename', metavar='FILENAME', type=str,
        help='Name of the result file',
        required=True)

    args = parser.parse_args()

    size = args.size
    index = args.index
    num_servs = args.num_servs
    result_filename = args.result_filename

    return size, index, num_servs, result_filename


def main():
    size, index, num_servs, result_filename = __get_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    playbook_dir = os.path.abspath(os.path.join(script_dir, os.pardir))
    output_dir = playbook_dir + '/output'

    result_file = output_dir + '/' + result_filename

    data = {}

    result_exists = os.path.isfile(result_file)
    if result_exists:
        with open(result_file, 'rt') as json_fobj:
            json_str = json_fobj.read()
        if json_str:
            data = json.loads(json_str)

    logs_dir = output_dir + '/logs'

    __add_client_data(logs_dir, data, size, index, num_servs)
    __add_servers_data(logs_dir, data, size, index, num_servs)

    with open(result_file, 'w') as json_fobj:
        json.dump(data, json_fobj, indent=4, sort_keys=True)


def __add_client_data(logs_dir, data, size, index, num_servs):
    client_log_filename = "perf_client_{}_{:d}_{:d}servs.log"
    client_log_file = logs_dir + '/' + client_log_filename.format(
        size, index, num_servs)

    cycles, bitrate = __extract_from_file(client_log_file)

    __set_arr_prop(data, size, str(num_servs), "cycles", "client",
                   value=cycles)
    __set_arr_prop(data, size, str(num_servs), "bitrate", "client",
                   value=bitrate)


def __add_servers_data(logs_dir, data, size, index, num_servs):
    cycles_arr = []
    bitrates_arr = []

    server_log_filename = "perf_server_{}_{:d}_{:d}servs_{:d}.log"
    for cur_i in range(num_servs):
        server_log_file = logs_dir + '/' + server_log_filename.format(
            size, index, num_servs, cur_i)

        cycles, bitrate = __extract_from_file(server_log_file)

        cycles_arr.append(cycles)
        bitrates_arr.append(bitrate)

    __set_arr_prop(data, size, str(num_servs), "cycles", "servers",
                   value=cycles_arr)
    __set_arr_prop(data, size, str(num_servs), "bitrate", "servers",
                   value=bitrates_arr)


PATTERN_CYCLES = re.compile(r'([,\d]+)\s+cycles')
PATTERN_BITRATE = re.compile(r'SUMMARY.+Bitrate:\s+([\d.]+)')


def __extract_from_file(file):
    with open(file, 'rt') as fobj:
        content = fobj.read()
        if not content:
            raise EOFError("Log file: %r is empty!" % file)

    matchobj = PATTERN_CYCLES.search(content)
    cycles = matchobj.group(1)

    matchobj = PATTERN_BITRATE.search(content)
    bitrate = matchobj.group(1)

    return locale.atoi(cycles), float(bitrate)


def __set_arr_prop(data, *args, value=None):
    obj = data
    for name in args[:-1]:
        if name not in obj:
            obj[name] = {}
        obj = obj[name]

    name = args[-1]
    if name not in obj:
        obj[name] = []

    if value is not None:
        obj[name].append(value)

    return obj[name]


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    main()
