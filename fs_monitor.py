# -*- coding: UTF-8 -*-
import fs_global as Global
from fs_logger import Logger
from fs_data import EnvData
from fs_message import Sender
from fs_util import Singleton, MyThreading, Common


class Monitor(Singleton):
    """
    状态监控类

    负责动态监控：
        1. 日志级别变更
        2. 缺失的监听目录
        3. inotifywait子进程状态
    """

    def __init__(self):
        self.hb_fail_count = 0
        self.ip_null_count = 0

    def start(self):
        MyThreading(func=self.monitor, behind=True, period=2).start()

    def monitor(self, args=None):
        Logger.debug("[fs_monitor] monitor start...")
        # 监控日志级别
        log_level = EnvData.parse_log_level().lower()
        if log_level != Global.G_LOG_LEVEL:
            Logger.info("[fs_monitor] LogLevel changed to %s" % log_level)
            Global.G_LOG_LEVEL = log_level

        # 监控目标IP是否为空
        if Global.G_CONNECT_IP_LIST:
            self.ip_null_count = 0
        else:
            self.ip_null_count += 1
            # filesync进程启动后2 * 30 = 60s之内要检测完IP连接状态，否则此处可能误判
            if self.ip_null_count < 30:
                Logger.warn('[fs_monitor] G_CONNECT_IP_LIST is NULL, times %s' % self.ip_null_count)
            else:
                Logger.warn('[fs_monitor] G_CONNECT_IP_LIST is NULL, stop filesync')
                Sender.send(Global.G_STOP_MSGID)
                return

        # 监控监听目录
        reload_switch = False
        for listen in Global.G_MISS_LISTEN:
            if not Common.is_exists(listen):
                continue
            Logger.info('[fs_monitor] %s is exist now' % listen)
            reload_switch = True
        if reload_switch:
            Logger.info('[fs_monitor] send signal reload')
            Sender.send(Global.G_RELOAD_MSGID)
            return

        # 监控inotify进程状态
        if Sender.send(Global.G_INOTIFY_HEARTBEAT_MSGID):
            self.hb_fail_count = 0
        else:
            self.hb_fail_count += 1
            # filesync进程启动后 2 * 2 = 4s 内要启动inotifywait进程，否则此处可能误判
            if self.hb_fail_count < 2:
                Logger.warn('[fs_monitor] inotify heartbeat lost, times %s' % self.hb_fail_count)
            else:
                Logger.info("[fs_monitor] inotify heartbeat failed, reload")
                Sender.send(Global.G_RELOAD_MSGID)
                return

