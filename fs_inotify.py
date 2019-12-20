# -*- coding: UTF-8 -*-
"""
Inotifywait事件监听模块

本模块负责：
    1. inotifywait进程的创建，该进程持续监听配置文件中指定
        文件或目录的变化事件（写关闭、修改、删除、移动、修改权限等）；
    2. 把收集的事件交由Master模块处理，生成对应的同步任务。
"""
import subprocess
from json import dumps
import fs_global as Global
from fs_util import FileOP, Common, Singleton
from fs_logger import Logger
from fs_data import ConfigWrapper, StateInfo
from fs_message import Receiver


class Inotify(Singleton):

    def __init__(self):
        self.listen_file = '{0}/listen.ini'.format(Global.G_RUN_DIR)
        self.event_list = []
        self.inotify_process = None
        self.inotify_event = ''

    def steps(self):
        """ 初始化配置文件和参数 """
        self.inotify_event = ''
        try:
            self.init_listen_file()
            self.init_inotify_event()
            self.register_event()
        except Exception as e:
            Logger.error(e)
            return False
        else:
            return True

    def init_listen_file(self):
        """ 初始化监听的目录到文件中 """
        listen_list = ConfigWrapper.get_listen_path()
        if not listen_list:
            raise Exception('[fs_inotify] inotify listen path is NULL')
        Logger.info('[fs_inotify] inotify listen path:%s'
                    % dumps(listen_list, indent=4))

        """ 写入监听文件，由inotifywait监听 """
        FileOP.write_to_file(self.listen_file, '')
        [FileOP.write_append_file(self.listen_file, line)
         for line in listen_list]

    def init_inotify_event(self):
        """ 初始化inotifywait命令参数 """
        _get_global_value = ConfigWrapper.get_key_value
        is_delete = _get_global_value('event_delete')
        is_create = _get_global_value('event_create')
        is_close_write = _get_global_value('event_closewrite')
        is_move = _get_global_value('event_move')
        is_moved_to = _get_global_value('event_movedto')
        is_moved_from = _get_global_value('event_movedfrom')
        is_attrib = _get_global_value('event_attrib')
        _event_param = ''
        if is_delete == 'true':
            _event_param += '-e delete'
        if is_create == 'true':
            _event_param += ' -e create'
        if is_close_write == 'true':
            _event_param += ' -e close_write'
        if is_move == 'true':
            _event_param += ' -e move'
        if is_moved_to == 'true':
            _event_param += ' -e moved_to'
        if is_moved_from == 'true':
            _event_param += ' -e moved_from'
        if is_attrib == 'true':
            _event_param += ' -e attrib'
        if _event_param == '':
            raise Exception("[fs_inotify] ALL event type is false")
        self.inotify_event += _event_param

    def register_event(self):
        Receiver.bind(Global.G_INOTIFY_EVENT_MSGID, self._get_event_list)
        Receiver.bind(Global.G_INOTIFY_HEARTBEAT_MSGID, self._heartbeat)

    def _get_event_list(self, param=None):
        return self.event_list

    def _heartbeat(self, param=None):
        if self._get_inotify_pid() != -1:
            return True
        return False

    def _get_inotify_pid(self):
        try:
            if self.inotify_process.poll() is None:
                pid = self.inotify_process.pid
            else:
                pid = -1
        except:
            pid = -1
        return pid

    def _inotify_process(self, args=None):
        """ 开启inotifywait进程 """
        inotify_cmd = "{0} -rmq "\
                      "--format '%e %w%f' {1} "\
                      "--fromfile {2}".format(
                      Global.G_INOTIFY_TOOL,
                      self.inotify_event,
                      self.listen_file)

        Logger.info("[fs_inotify] start %s" % inotify_cmd)
        self.inotify_process = subprocess.Popen([inotify_cmd],
                                                bufsize=10240,
                                                stdout=subprocess.PIPE,
                                                shell=True)
        Logger.info("[fs_inotify] filesync pid: %s" % Common.get_pid())
        Logger.info("[fs_inotify] inotifywait pid: %s" % self._get_inotify_pid())
        _proc_poll = self.inotify_process.poll
        _readline = self.inotify_process.stdout.readline
        _append = self.event_list.append

        while _proc_poll() is None:
            event_line = Common.stream_2_str(_readline()).strip()
            if event_line != "":
                _append(event_line)

    def start(self):
        Common.start_thread(target=self._inotify_process)

    def stop(self):
        try:
            if self.inotify_process.poll() is None:
                Logger.info("[fs_inotify] inotifywait(%s) exit"
                            % self.inotify_process.pid)
                self.inotify_process.kill()
        except:
            pass

    def reload(self):
        """ 重新加载 """
        self.stop()
        if self.steps():
            self.start()

    def status(self):
        pid = self._get_inotify_pid()
        StateInfo.set_inotify_pid(pid)

