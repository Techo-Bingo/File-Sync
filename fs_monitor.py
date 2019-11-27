# -*- coding: UTF-8 -*-
import fs_global as Global
from fs_logger import Logger
from fs_data import EnvData
from fs_util import MyThreading


class Monitor(object):

    def __init__(self):
        pass

    def init(self):
        MyThreading(func=self.monitor, period=1).start()
        return True

    def monitor(self, args=None):
        log_level = EnvData.parse_log_level().lower()
        if log_level == Global.G_LOG_LEVEL:
            return
        Global.G_LOG_LEVEL = log_level
        Logger.info("[filesync] LogLevel changed to %s" % log_level)




