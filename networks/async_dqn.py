# -*- coding: utf-8 -*-

import tensorflow as tf

from tensorflow.contrib.framework import arg_scope
from tensorflow.contrib import layers

from util import Record
from util.tfutil import gather_2d

from .common import default_conv_layers


class ADQNNet(object):
    def __init__(self,
                 actions_num,
                 img_shape,
                 misc_len=0,
                 entropy_beta=0.01,
                 thread="global",
                 activation_fn="tf.nn.relu",
                 **ignored):
        self.activation_fn = eval(activation_fn)
        self.ops = Record()
        self.vars = Record()
        self.vars.state_img = tf.placeholder(tf.float32, [None] + list(img_shape), name="state_img")
        self.use_misc = misc_len > 0
        if self.use_misc:
            self.vars.state_misc = tf.placeholder("float", [None, misc_len], name="state_misc")
        self.actions_num = actions_num
        self._name_scope = self._get_name_scope() + "_" + str(thread)

        self.params = None
        self._entropy_beta = entropy_beta

        with arg_scope([layers.conv2d], data_format="NCHW"), \
             arg_scope([layers.fully_connected, layers.conv2d], activation_fn=self.activation_fn):
            # TODO make it configurable from yaml
            self.ops.q = self.create_architecture()
        self._prepare_loss_op()
        self.params = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope=self._name_scope)

    def prepare_sync_op(self, global_network):
        global_params = global_network.get_params()
        local_params = self.get_params()
        sync_ops = [tf.assign(dst_var, src_var) for dst_var, src_var, in zip(local_params, global_params)]

        self.ops.sync = tf.group(*sync_ops, name="SyncWithGlobal")

    def prepare_unfreeze_op(self, target_network):
        target_params = target_network.get_params()
        global_params = self.get_params()
        sync_ops = [tf.assign(dst_var, src_var) for dst_var, src_var, in zip(target_params, global_params)]

        self.ops.unfreeze = tf.group(*sync_ops, name="SyncWithGlobal")

    def _prepare_loss_op(self):
        self.vars.a = tf.placeholder(tf.float32, [None], name="action")
        self.vars.advantage = tf.placeholder(tf.float32, [None], name="advantage")
        self.vars.target_q = tf.placeholder(tf.float32, [None], name="R")
        # TODO add summaries for entropy, policy and value

        active_q = gather_2d(self.ops.q, self.vars.a)
        self.ops.loss = 0.5 * tf.reduce_sum((active_q - self.vars.target_q) ** 2)

    def create_architecture(self):
        conv_layers = default_conv_layers(self.vars.state_img, self._name_scope)

        if self.use_misc:
            fc_input = tf.concat(concat_dim=1, values=[conv_layers, self.vars.state_misc])
        else:
            fc_input = conv_layers

        fc1 = layers.fully_connected(fc_input, num_outputs=512, scope=self._name_scope + "/fc1")
        q = layers.linear(fc1, num_outputs=self.actions_num, scope=self._name_scope + "/q")
        return q

    def get_standard_feed_dict(self, state):
        feed_dict = {self.vars.state_img: [state[0]]}
        if self.use_misc > 0:
            if len(state[1].shape) == 1:
                misc = state[1].reshape([1, -1])
            else:
                misc = state[1]
            feed_dict[self.vars.state_misc] = misc
        return feed_dict

    def get_q_values(self, sess, state):
        q = sess.run(self.ops.q, feed_dict=self.get_standard_feed_dict(state))
        return q

    def get_params(self):
        return self.params

    def has_state(self):
        return False

    def _get_name_scope(self):
        return "async_dqn"
