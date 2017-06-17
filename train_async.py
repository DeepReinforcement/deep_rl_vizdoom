#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

from constants import *
from util.parsers import parse_train_async_args
from util.coloring import green
from async_learner import A3CLearner, ADQNLearner
from util.misc import print_settings, load_settings
from util.logger import setup_file_logger, log
import networks


def train_async(q_learning, settings):
    import tensorflow as tf

    from vizdoom_wrapper import VizdoomWrapper
    from util import ThreadsafeCounter
    from util.optimizers import ClippingRMSPropOptimizer

    tmp_vizdoom_wrapper = VizdoomWrapper(noinit=True, **settings)
    actions_num = tmp_vizdoom_wrapper.actions_num
    misc_len = tmp_vizdoom_wrapper.misc_len
    img_shape = tmp_vizdoom_wrapper.img_shape
    del tmp_vizdoom_wrapper

    # TODO target global network
    # This global step counts gradient applications not performed actions.
    global_train_step = tf.Variable(0, trainable=False, name="global_step")
    global_learning_rate = tf.train.polynomial_decay(
        learning_rate=settings["initial_learning_rate"],
        end_learning_rate=settings["final_learning_rate"],
        decay_steps=settings["learning_rate_decay_steps"],
        global_step=global_train_step)
    optimizer = ClippingRMSPropOptimizer(learning_rate=global_learning_rate, **settings["rmsprop"])

    learners = []
    network_class = eval(settings["network_type"])

    global_network = network_class(actions_num=actions_num, misc_len=misc_len, img_shape=img_shape,
                                   **settings)
    if q_learning:
        global_target_network = network_class(thread="global_target", actions_num=actions_num,
                                              misc_len=misc_len,
                                              img_shape=img_shape, **settings)
        global_network.prepare_unfreeze_op(global_target_network)
        unfreeze_thread = min(1, settings["threads_num"] - 1)
        for i in range(settings["threads_num"]):
            learner = ADQNLearner(thread_index=i, global_network=global_network,
                                  unfreeze_thread=i == unfreeze_thread,
                                  global_target_network=global_target_network, optimizer=optimizer,
                                  **settings)
            learners.append(learner)
    else:
        for i in range(settings["threads_num"]):
            learner = A3CLearner(thread_index=i, global_network=global_network, optimizer=optimizer,
                                 **settings)
            learners.append(learner)

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    session = tf.Session(config=config)

    log("Initializing variables...")
    session.run(tf.global_variables_initializer())
    log("Initialization finished.\n")
    global_steps_counter = ThreadsafeCounter()

    if q_learning:
        session.run(global_network.ops.unfreeze)

        log(green("Launching training."))
    for l in learners:
        l.run_training(session, global_steps_counter=global_steps_counter)
    for l in learners:
        l.join()


if __name__ == "__main__":
    args = parse_train_async_args()

    if args.q:
        default_settings_filepath = DEFAULT_ADQN_SETTINGS_FILE
    else:
        default_settings_filepath = DEFAULT_A3C_SETTINGS_FILE

    settings = load_settings(default_settings_filepath, args.settings_yml)

    if settings["logfile"] is not None:
        log("Setting up file logging to: {}".format(settings["logfile"]))
        setup_file_logger(settings["logfile"], add_date=True)

    log("Loaded settings:")
    print_settings(settings)

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = str(settings["tf_log_level"])

    train_async(args.q, settings)
