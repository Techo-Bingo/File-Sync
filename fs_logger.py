# -*- coding: UTF-8 -*-
import fs_global as Global
from fs_util import Common, FileOP, MyThreading


class Logger:
    """
    日志类

    即开即写，日志回滚裁剪不影响日志写入
    写日志前对比一下当前日志级别，不符合时不记录相应的日志
    """
    _log_file = None

    @classmethod
    def init(cls, filepath):
        cls._log_file = filepath
        cls._write_append('\n\n< Init FileSync >')
        Common.chown(filepath)

    @classmethod
    def _write_append(cls, info):
        if not cls._log_file:
            return False
        try:
            with open(cls._log_file, 'a+') as f:
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


class TruncLog(object):
    """ 日志裁剪回滚类 """

    def __init__(self):
        self.log_path = None

    def init(self):
        #  初始化日志
        self.log_path = '%s/filesync-%s.log' % (Global.G_LOG_DIR, Common.get_pid())
        log_level = FileOP.cat_file(Global.G_LOGLEVEL_INI).strip().lower()
        Logger.init(self.log_path)
        if log_level in ['info', 'debug', 'error']:
            Global.G_LOG_LEVEL = log_level
        else:
            Global.G_LOG_LEVEL = 'info'
            Logger.warn("[filesync] Not support loglevel:%s, set to info"
                        % log_level)
        # 启动日志回滚线程
        MyThreading(func=self.rollback, period=Global.G_LOG_PERIOD).start()

    def trunk_log(self):
        if FileOP.get_size(self.log_path) < Global.G_LOG_LIMIT:
            return
        Logger.info("[fs_logger] Trunk log: %s" % self.log_path)
        # 获取去除.log后的日志文件前缀
        name = '.'.join(self.log_path.split('.')[:-1])
        # 压缩当前进程日志并限制压缩包个数
        Common.shell_cmd("mv {0} {0}.1 && > {0} && "
                         "tar zcvf {1}_$(date +'%Y%m%d-%H%M').tar.gz {0}.1 && "
                         "rm {0}.1;ls -t {1}_*.tar.gz|sed -n '15,100p'|xargs rm -rf"
                         .format(self.log_path, name))

    def keep_count(self):
        # TODO 如果日志对应pid的filesync正在运行，则不能删除该日志；
        # 当前需求中不可能超过10个文件同步同时运行，则先默认值保留10个.
        Common.shell_cmd("ls -t %s/*.log|sed -n '10,1000p'|xargs rm -rf"
                         % Global.G_LOG_DIR)

    def rollback(self, args=None):
        # 日志个数回滚
        self.keep_count()
        # 当前进程日志过大裁剪
        self.trunk_log()

