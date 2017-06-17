#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

from util.parsers import parse_train_dqn_args
from util.logger import log,setup_file_logger
from util.misc import load_settings,print_settings
from dqn import DQN
from constants import *

if __name__ == "__main__":

    args = parse_train_dqn_args()
    settings = load_settings(DEFAULT_DQN_SETTINGS_FILE, args.settings_yml)

    if settings["logfile"] is not None:
        log("Setting up file logging to: {}".format(settings["logfile"]))
        setup_file_logger(settings["logfile"], add_date=True)

    log("Loaded settings:")
    print_settings(settings)

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = str(settings["tf_log_level"])

    dqn = DQN(**settings)
    dqn.train()
