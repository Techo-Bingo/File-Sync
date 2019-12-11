# -*- coding: UTF-8 -*-
"""
文件同步入口

本模块为文件同步的启停入口，不能被其他模块引用。

调用方式:
    python filesync.py [start|stop|restart|status|reload|pause|resume]
"""
import sys
import time
import fs_global as Global
from fs_util import Daemon
from fs_monitor import Monitor
from fs_inotify import Inotify
from fs_master import Master
from fs_message import Publisher, Receiver
from fs_logger import Logger, LogTrunc
from fs_data import EnvData, ConfigWrapper, ConfigData, StateInfo


class FileSync(Daemon):
    """
    文件同步控制类
    功能：
        1. 负责环境初始化；
        2. 负责Inotify和Master类的启动和重加载
        3. 负责处理外部动态请求（事件）
    """

    @classmethod
    def init(cls):
        if not all([Logger.init(),
                    LogTrunc.init(),
                    ConfigWrapper.init(),
                    ConfigData().init(),
                    Inotify().init(),
                    Master().init(),
                    Monitor().init()]):
            Logger.error('[filesync] FileSync init failed')
            raise SystemExit(3)

    @classmethod
    def mainloop(cls):
        while True:
            time.sleep(10)

    @classmethod
    def start_callback(cls):
        cls.init()
        Logger.info('[filesync] notify signal: start')
        Publisher.notify('SIGNAL', 'start')
        cls.mainloop()

    @classmethod
    def stop_callback(cls):
        Logger.info('[filesync] notify signal: stop')
        Publisher.notify('SIGNAL', 'stop')

    @classmethod
    def pause_callback(cls, signum, stack=None):
        Logger.info('[filesync] notify signal(%s): pause' % signum)
        Publisher.notify('SIGNAL', 'pause')

    @classmethod
    def resume_callback(cls, signum, stack=None):
        Logger.info('[filesync] notify signal(%s): resume' % signum)
        Publisher.notify('SIGNAL', 'resume')

    @classmethod
    def reload_callback(cls, signum, stack=None):
        Logger.info('[filesync] notify signal(%s): reload' % signum)
        Publisher.notify('SIGNAL', 'reload')

    @classmethod
    def status_callback(cls, signum, stack=None):
        Logger.info('[filesync] notify signal(%s): status' % signum)
        Publisher.notify('SIGNAL', 'status')
        Logger.info(StateInfo.get_state_info())


def main():
    if len(sys.argv) != 2:
        usage = "Usage: %s [start|stop|restart|status|reload|pause|resume]"
        sys.stderr.write(usage)
        sys.exit(1)
    # 初始化系统环境变量
    result, err = EnvData.init()
    if not result:
        sys.stderr.write(err)
        sys.exit(2)
    # 定义信号处理回调函数
    callback_funs = (FileSync.start_callback,
                     FileSync.stop_callback,
                     FileSync.pause_callback,
                     FileSync.resume_callback,
                     FileSync.reload_callback,
                     FileSync.status_callback)
    filesync = FileSync(Global.G_PID_FILE, Global.G_LOG_FILE, callback_funs)
    # 绑定reload回调函数, fs_monitor模块中reload
    Receiver.bind(Global.G_RELOAD_MSGID, filesync.reload)

    op_type = sys.argv[1]
    if op_type == 'start':
        filesync.start()
    elif op_type == 'stop':
        filesync.stop()
    elif op_type == 'restart':
        filesync.restart()
    elif op_type == 'status':
        filesync.status()
    elif op_type == 'pause':
        filesync.pause()
    elif op_type == 'resume':
        filesync.resume()
    elif op_type == 'reload':
        filesync.reload()
    else:
        sys.stderr.write("Unknown command %s" % op_type)
        sys.exit(4)


if __name__ == '__main__':
    main()
    sys.exit(0)


