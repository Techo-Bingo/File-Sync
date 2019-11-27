# -*- coding: UTF-8 -*-
import fs_global as Global
from fs_util import Common, FileOP, MyThreading


class Logger:
    """
    日志类

    即开即写，日志回滚裁剪不影响日志写入
    写日志前对比一下当前日志级别，不符合时不记录相应的日志
    """

    @classmethod
    def init(cls):
        try:
            cls._write_append('< FileSync-Init >')
            Common.chown(Global.G_LOG_FILE, Global.G_RSYNC_USER)
        except:
            return False
        return True

    @classmethod
    def _write_append(cls, info):
        try:
            with open(Global.G_LOG_FILE, 'a+') as f:
                f.write(info + '\n')
                return True
        except OSError:
            return False

    @classmethod
    def info(cls, info):
        if Global.G_LOG_LEVEL == 'error':
            return
        cls._write_append('[INFO ] %s: %s' % (Common.get_time(), info))

    @classmethod
    def warn(cls, info):
        if Global.G_LOG_LEVEL == 'error':
            return
        cls._write_append('[WARN ] %s: %s' % (Common.get_time(), info))

    @classmethod
    def error(cls, info):
        cls._write_append('[ERROR] %s: %s' % (Common.get_time(), info))

    @classmethod
    def debug(cls, info):
        if Global.G_LOG_LEVEL != 'debug':
            return
        cls._write_append('[DEBUG] %s: %s' % (Common.get_time(), info))


class LogTrunc:
    """ 日志裁剪回滚类 """

    @classmethod
    def init(cls):
        # 启动日志回滚线程
        MyThreading(func=cls.rollback, period=Global.G_TRUNC_PERIOD).start()
        return True

    @classmethod
    def trunk_log(cls):
        if FileOP.get_size(Global.G_LOG_FILE) < Global.G_MAX_SIZE:
            return
        Logger.info("[fs_logger] Trunk log: %s" % Global.G_LOG_FILE)
        # 获取去除.log后的日志文件前缀
        name = '.'.join(Global.G_LOG_FILE.split('.')[:-1])
        # 压缩当前进程日志并限制压缩包个数
        Common.shell_cmd("cp {0} {0}.1 && > {0} && "
                         "tar zcvf {1}_$(date +'%Y%m%d-%H%M').tar.gz {0}.1 && "
                         "rm {0}.1;ls -t {1}_*.tar.gz|sed -n '15,100p'|xargs rm -rf"
                         .format(Global.G_LOG_FILE, name))

    @classmethod
    def keep_count(cls):
        # TODO 如果日志对应pid的filesync正在运行，则不能删除该日志；
        # 当前需求中不可能超过10个文件同步同时运行，则先默认值保留10个.
        Common.shell_cmd("ls -t %s/*.log|sed -n '10,1000p'|xargs rm -rf"
                         % Global.G_LOG_DIR)

    @classmethod
    def rollback(cls, args=None):
        # 日志个数回滚
        cls.keep_count()
        # 当前进程日志过大裁剪
        cls.trunk_log()

