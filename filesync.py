# -*- coding: UTF-8 -*-
"""
文件同步入口

本模块为文件同步的总入口，不能被其他模块引用。
开发时请至少遵守如下PEP8风格：
    1. 类命名使用大驼峰；
    2. 函数命名使用内核风格；
    3. 基本满足每行不超过80个字符；
    4. 私有变量和函数使用_开头
    5. 一块代码的注释使用三个"扩起
    6. 一行代码的注释使用 #

调用方式:
    python filesync.py
"""
import sys
import time
import fs_global as Global
from fs_inotify import Inotify
from fs_master import Master
from fs_data import ConfigData
from fs_logger import Logger, TruncLog
from fs_util import Common, FileOP, MyThreading


class FileSync(object):
    """
    文件同步控制类
    功能：
        1. 负责环境初始化；
        2. 负责Inotify和Master类的启动和重加载
        3. 负责处理外部动态请求（事件）
    """

    def __init__(self):
        self.actor = None
        self.inotify = None
        self.master = None

    @classmethod
    def init_env(cls):
        """ 初始化环境变量等 """
        Global.G_LOCAL_DIR = Common.get_abspath('.')
        Global.G_RUN_DIR = '%s/run' % Global.G_LOCAL_DIR
        Global.G_RELOAD_FLAG = '%s/reload.flag' % Global.G_RUN_DIR
        Global.G_STATUS_FLAG = '%s/status.flag' % Global.G_RUN_DIR
        Common.mkdir(Global.G_LOG_DIR)
        Common.mkdir(Global.G_RUN_DIR)
        return True

    @classmethod
    def init_logger(cls):
        """ 初始化日志文件并启动日志回滚线程 """
        TruncLog().init()
        return True

    @classmethod
    def init_config(cls):
        """ 初始化文件同步配置文件数据 """
        return ConfigData.init_config()

    @classmethod
    def reload_config(cls):
        """ 重新加载配置文件数据 """
        return ConfigData.reload_config()

    def init_inotify(self):
        """ 初始化inotifywait """
        self.inotify = Inotify()
        return self.inotify.start()

    def reload_inotify(self):
        """ 重新加载inotifywait """
        return self.inotify.reload()

    def init_master(self):
        """ 初始化事件过滤主线程 """
        self.master = Master()
        return self.master.start()

    def init_actor(self):
        """ 处理外部请求事件 """
        self.actor = MyThreading(func=self.action, period=1)
        self.actor.start()
        return True

    def action(self, args=None):
        """
        处理外部事件函数

        根据外部事件标识以及日志级别等，
        动态调整同步状态或输出同步状态信息

        参数：None

        输出：None
        """
        if Common.is_file(Global.G_RELOAD_FLAG):
            Logger.info('[filesync] reload filesync start')
            self.reload()
            FileOP.rm_file(Global.G_RELOAD_FLAG)

        if Common.is_file(Global.G_STATUS_FLAG):
            Logger.info('[filesync] print filesync status')
            self.status()
            FileOP.rm_file(Global.G_STATUS_FLAG)

        log_level = FileOP.cat_file(Global.G_LOGLEVEL_INI).strip().lower()
        if log_level in ['info', 'debug', 'error']:
            if log_level == Global.G_LOG_LEVEL:
                return
            Global.G_LOG_LEVEL = log_level
            Logger.info("[filesync] LogLevel changed to %s" % log_level)

    def status(self):
        """ 获取同步状态等信息 """
        syncing, connect, waiting, retry = self.master.status()
        inotify_pid = self.inotify.status()
        syncing_str = '\n\t'+'\n\t'.join(syncing) if syncing else ''
        retry_str = '\n\t'+'\n\t'.join(retry) if retry else ''
        status_info = Global.G_STATUS_INFO % (Common.get_pid(),
                                              inotify_pid,
                                              '\n'.join(connect),
                                              len(syncing),
                                              len(waiting),
                                              len(retry),
                                              syncing_str,
                                              retry_str,
                                              'TODO'
                                              )
        FileOP.write_to_file('%s.tmp' % Global.G_STATUS_FLAG, status_info)
        Logger.info("[filesync] \n%s" % status_info)

    def start(self):
        """ 初始化启动 """
        if not all([self.init_env(),
                    self.init_logger(),
                    self.init_config()]):
            return False
        return all([self.init_inotify(),
                    self.init_master(),
                    self.init_actor()]
                   )

    def reload(self):
        """ reload热加载配置文件 """
        return all([self.reload_config(),
                    self.reload_inotify()]
                   )


if __name__ == '__main__':
    if not FileSync().start():
        sys.exit(1)
    while True:
        time.sleep(10)


