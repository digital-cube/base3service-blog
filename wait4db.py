#!/usr/bin/env python

import os
import sys
import base


if __name__ == '__main__':

    my_dir_name = os.path.dirname(os.path.realpath(__file__))

    base.config.load_from_yaml(my_dir_name + f'/config/config.{os.getenv("ENVIRONMENT", "local")}.yaml')

    if not base.sync_order.wait4store(max_attempts=50):
        sys.exit(127)

    if not base.sync_order.wait4store_permissions(max_attempt=50):
        sys.exit(127)

    if not base.sync_order.wait4database(base.config.conf['db'], max_attempts=50):
        sys.exit(127)

    sys.exit(0)
