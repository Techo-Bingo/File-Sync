# -*- coding: UTF-8 -*-
import fs_global as Global
from fs_logger import Logger
from fs_data import EnvData
from fs_message import Sender
from fs_util import Singleton, MyThreading, Common


class Monitor(Singleton):

    def __init__(self):
        pass

    # def steps(self):  # monitor暂时不用接受signal, 先覆盖基类init
    def init(self):
        MyThreading(func=self.monitor, period=1).start()
        return True

    def monitor(self, args=None):
        # 监控日志级别
        log_level = EnvData.parse_log_level().lower()
        if log_level != Global.G_LOG_LEVEL:
            Logger.info("[fs_monitor] LogLevel changed to %s" % log_level)
            Global.G_LOG_LEVEL = log_level

        # 监控监听目录
        reload_switch = False
        for listen in Global.G_MISS_LISTEN:
            if not Common.is_exists(listen):
                continue
            Logger.info('[fs_monitor] %s is exist now' % listen)
            reload_switch = True
        if reload_switch:
            Logger.info('[fs_monitor] send signal reload')
            # 清空集合， 因为reload动作会重新载入和设置该集合
            Global.G_MISS_LISTEN.clear()
            Sender.send(Global.G_RELOAD_MSGID)

