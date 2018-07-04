#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This script is used to check if the percentage number in file match the
# percentage number present in the filename for all the perf_server_*.log
# under the logs folder.

import argparse
import os
import re


def __get_args():
    parser = argparse.ArgumentParser(
        description='Extract outputs of iostat to json file based on the \
                     corresponding perf stat profiles')
    parser.add_argument(
        '-d', '--work_dir', metavar='DIR', type=str,
        help='Path of the working directory',
        required=True)
    parser.add_argument(
        '-t', '--threshold', type=float,
        help='The value of threashold for checking',
        default=0.01,
        required=False)

    return parser.parse_args()


PATTERN_NUMBER_IN_CONTENT = re.compile(r'SUMMARY.*\(([\d\.]+)%')
PATTERN_NUMBER_IN_NAME = re.compile(r'(\d+)%')


def main():
    cmd_args = __get_args()

    logs_dir = cmd_args.work_dir + '/logs'

    perf_server_profile_filename = \
        sorted([entry.name for entry in os.scandir(logs_dir)
                if entry.is_file() and
                entry.name.startswith('perf_server_') and
                entry.name.endswith('.log')])

    for filename in perf_server_profile_filename:
        perf_server_profile_file = logs_dir + '/' + filename
        print("checking %s" % perf_server_profile_file)

        num_in_name = PATTERN_NUMBER_IN_NAME.search(filename).group(1)
        with open(perf_server_profile_file, 'rt') as fobj:
            num_in_content = PATTERN_NUMBER_IN_CONTENT.search(
                fobj.read()).group(1)

        diff = abs(int(num_in_name) - float(num_in_content))
        if diff > cmd_args.threshold:
            print("Found invalid nums (name: %s, content: %s, diff: %s) \
                  in file: %s" %
                  (num_in_name,
                   num_in_content,
                   diff,
                   perf_server_profile_file))
            break


if __name__ == "__main__":
    main()
