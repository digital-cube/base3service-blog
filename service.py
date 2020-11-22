#!/usr/bin/env python
import base
import os
import importlib

if __name__ == "__main__":

    my_dir_name = os.path.dirname(os.path.realpath(__file__))
    base.config.load_from_yaml(my_dir_name + f'/config/config.{os.getenv("ENVIRONMENT", "local")}.yaml')

    importlib.import_module('api.blog')

    base.run(debug=True)
