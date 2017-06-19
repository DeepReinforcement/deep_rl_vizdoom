#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from async import test_async

from paths import DEFAULT_ADQN_SETTINGS_FILE
from util.parsers import parse_test_adqn_args
import os

from util.misc import print_settings, load_settings
from util.logger import setup_file_logger, log

if __name__ == "__main__":
    args = parse_test_adqn_args()

    settings = load_settings(DEFAULT_ADQN_SETTINGS_FILE, args.settings_yml)

    if settings["logfile"] is not None:
        log("Setting up file logging to: {}".format(settings["logfile"]))
        setup_file_logger(settings["logfile"], add_date=True)

    log("Loaded settings.")
    if args.print_settings:
        print_settings(settings)

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = str(settings["tf_log_level"])

    settings["display"] = not args.hide_window
    settings["async"] = not args.hide_window
    settings["smooth_display"] = not args.agent_view
    settings["fps"] = args.fps
    settings["seed"] = args.seed
    settings["write_summaries"] = False
    settings["test_only"] = True

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = str(settings["tf_log_level"])

    test_async(q_learning=True, settings=settings, modelfile=args.model, eps=args.episodes_num)
