# -*- coding: UTF-8 -*-
"""
事件过滤处理模块

本模块功能：
    1. 初始化并启动Slaves线程池管理类，
    2. 定时从inotify消息队列中解析事件到任务到队列
"""
from time import sleep
import fs_global as Global
from fs_logger import Logger
from fs_slaves import Slaves
from fs_message import Sender
from fs_util import Singleton, Common
from fs_data import ConfigWrapper, TaskQueue, RetryQueue, StateInfo


class Master(Singleton):

    def __init__(self):
        self.slaves = None
        self.thread_count = None

    def steps(self):
        try:
            self.init_task()
            self.handle_event()
            self.slaves = Slaves(self.thread_count)
        except Exception as e:
            Logger.error(e)
            return False
        else:
            return True

    def init_task(self):
        """ 初始化任务队列 """
        count = int(ConfigWrapper.get_key_value('thread_count'))
        if count < 1 or count > 100:
            raise Exception('[fs_master] thread_count is invalid:%s' % count)
        self.thread_count = count

        limit_size = int(ConfigWrapper.get_key_value('sync_queue_size'))
        TaskQueue.init(limit_size, count)

        limit_size = int(ConfigWrapper.get_key_value('fail_queue_size'))
        RetryQueue.init(limit_size)

    def handle_event(self):
        Common.start_thread(target=self.parse_task, args=())

    @classmethod
    def parse_task(cls, args=None):
        """
        事件处理函数

        死循环处理inotify原始事件；
        如果事件是监控的同步文件，则直接将文件放入队列(同步文件)
        否则将该事件的上级目录放入队列(同步目录)

        参数: None

        返回值: None
        """
        event_list = Sender.send(Global.G_INOTIFY_EVENT_MSGID)
        _evt_pop = event_list.pop
        _is_listen_file = ConfigWrapper.is_listen_file
        _get_value = ConfigWrapper.get_key_value
        _is_dir = Common.is_dir
        _dirname = Common.dirname
        _push_task = TaskQueue.push_task

        while 1:
            while 1:
                if not len(event_list):
                    break
                event, path = _evt_pop(0).split()
                Logger.debug("[fs_master] get inotifywait event: %s %s"
                             % (event, path))

                if not _is_listen_file(path) and not _is_dir(path):
                    path = _dirname(path)
                _push_task(path)

            """ 防止同一事件频繁同步，每次等待一段时间 """
            sleep(int(_get_value('sync_period')))

    def start(self):
        self.slaves.start()

    def status(self):
        syncing, connect = self.slaves.status()
        StateInfo.set_syncing_task(syncing)
        StateInfo.set_connected_ip(connect)
        StateInfo.set_waiting_task(TaskQueue.status())
        StateInfo.set_retry_task(RetryQueue.status())

    def pause(self):
        self.slaves.pause()

    def resume(self):
        self.slaves.resume()

