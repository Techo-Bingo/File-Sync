# -*- coding: UTF-8 -*-
"""
消息驱动模块

使用发布/订阅模式实现消息回调
本模块负责：
    1. 各模块之间解耦，通过消息驱动
    2. 实现一对一和一对多的消息模式
"""
from collections import defaultdict


class _Intermedia:
    """ 一对多模式 """
    messages = defaultdict(dict)

    @classmethod
    def broadcast(cls, msg, param):
        for name, callback in cls.messages[msg].items():
            callback(param)

    @classmethod
    def register(cls, msg, handler):
        cls.messages[msg][handler.name] = handler.callback

    @classmethod
    def unregister(cls, msg, handler):
        try:
            del cls.messages[msg][handler.name]
        except:
            pass


class Subscriber(object):

    def __init__(self, name):
        self.name = name
        self.callback = None

    def register(self, msg, callback):
        self.callback = callback
        _Intermedia.register(msg, self)

    def unregister(self, msg):
        _Intermedia.unregister(msg, self)


class Publisher:
    @classmethod
    def notify(cls, msg, param=None):
        _Intermedia.broadcast(msg, param)


class _Medium:
    """ 一对一模式 """
    messages = {}

    @classmethod
    def unicast(cls, msg, param):
        callback = cls.messages[msg]
        return callback(param)

    @classmethod
    def bind(cls, msg, callback):
        cls.messages[msg] = callback

    @classmethod
    def unbind(cls, msg):
        try:
            del cls.messages[msg]
        except:
            pass


class Receiver:

    @classmethod
    def bind(cls, msg, callback):
        _Medium.bind(msg, callback)

    @classmethod
    def unbind(cls, msg):
        _Medium.unbind(msg)


class Sender:

    @classmethod
    def send(cls, msg, param=None):
        return _Medium.unicast(msg, param)


