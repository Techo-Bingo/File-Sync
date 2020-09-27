# -*- coding: UTF-8 -*-
"""
数据管理模块

本模块包括的数据：
    1. 文件同步主配置文件数据
    2. 待同步任务数据
    3. 重传任务数据
    4. 状态数据
"""
import fs_global as Global
from json import dumps
from threading import Lock
from fs_util import Singleton, Common, ParserConfig
from fs_logger import Logger


class ConfigError(Exception):
    """ 配置文件的异常 """
    pass


class EnvData:
    """ 系统环境数据类 """

    @classmethod
    def init(cls):
        ini_dict = {}
        cur_dir = Common.get_abspath()
        Global.G_ENV_INI = Common.join_path(cur_dir, Global.G_ENV_INI)
        Global.G_CONF_INI = Common.join_path(cur_dir, Global.G_CONF_INI)
        Global.G_RUN_DIR = Common.join_path(cur_dir, 'run')
        Global.G_PID_FILE = Common.join_path(Global.G_RUN_DIR, 'filesync.pid')
        ParserConfig(Global.G_ENV_INI).parse_to_dict(ini_dict)
        try:
            ini_dict = ini_dict['ENV']
            for key in ['log_level',
                        'log_dir',
                        'max_log_size',
                        'log_trunc_period',
                        'rsync_user',
                        'rsync_tool',
                        'fping_tool',
                        'inotify_tool',
                        'so_path']:
                if key not in ini_dict:
                    raise Exception("%s miss %s" % (Global.G_ENV_INI, key))
                if not ini_dict[key]:
                    raise Exception("%s is NULL" % key)
            log_level = ini_dict['log_level']
            Global.G_LOG_LEVEL = log_level if log_level in ['info', 'debug', 'error'] else 'info'
            Global.G_LOG_DIR = ini_dict['log_dir']
            if not Global.G_LOG_DIR.startswith('/'):
                Global.G_LOG_DIR = Common.join_path(cur_dir, Global.G_LOG_DIR)
            Global.G_LOG_FILE = Common.join_path(Global.G_LOG_DIR, 'filesync.log')
            Global.G_MAX_SIZE = int(ini_dict['max_log_size'])
            Global.G_MAX_COUNT = int(ini_dict['max_log_count'])
            Global.G_TRUNC_PERIOD = int(ini_dict['log_trunc_period'])
            Global.G_RSYNC_USER = ini_dict['rsync_user']
            # 以同步用户调用同步进程
            if not Common.user_match(Global.G_RSYNC_USER):
                raise Exception("please switch %s to continue" % Global.G_RSYNC_USER)
            rsync_tool = ini_dict['rsync_tool']
            if not Common.is_file(rsync_tool):
                raise Exception("%s is not a valid rsync tool" % rsync_tool)
            Global.G_RSYNC_TOOL = rsync_tool
            fping_tool = ini_dict['fping_tool']
            if not Common.is_file(fping_tool):
                raise Exception("%s is not a valid fping tool" % fping_tool)
            Global.G_FPING_TOOL = fping_tool
            inotify_tool = ini_dict['inotify_tool']
            if not Common.is_file(inotify_tool):
                raise Exception("%s is not a valid inotify tool" % inotify_tool)
            Global.G_INOTIFY_TOOL = inotify_tool
            so_path = ini_dict['so_path']
            if not Common.is_dir(so_path):
                raise Exception("%s is not a valid directory path" % so_path)
            Global.G_SO_PATH = so_path
            Common.mkdir(Global.G_LOG_DIR)
            Common.mkdir(Global.G_RUN_DIR)
        except Exception as e:
            return False, "EnvData Exception: %s" % e
        else:
            return True, None

    @classmethod
    def parse_log_level(cls):
        level = ParserConfig(Global.G_ENV_INI).get_value('ENV', 'log_level')
        return level if level in ['info', 'debug', 'error'] else 'info'


class ConfigWrapper:
    """ 数据包装层 """
    _config = None

    @classmethod
    def init(cls):
        cls._config = ConfigData()
        return True

    @classmethod
    def is_listen_file(cls, path):
        return path in cls._config.get_config_data()

    @classmethod
    def get_listen_path(cls, last=False):
        _data = cls._config.get_config_data(last)
        return [key for key in _data
                if key not in ['GLOBAL',
                               '__GLOBAL_REQUIRED__',
                               '__LISTEN_REQUIRED__'
                               ]]

    @classmethod
    def get_key_value(cls, key, section='GLOBAL', last=False):
        _data = cls._config.get_config_data(last)
        if section not in _data:
            return None
        if key not in _data[section]:
            return None
        return _data[section][key]


class ConfigData(Singleton):
    """ 同步主配置文件数据类 """
    _curr_config = {}
    _last_config = {}

    def steps(self):
        """ 初始化配置文件 """
        self._curr_config = {}
        try:
            # 解析配置文件
            self.parsed_data()
            # 检查配置文件数据的正确性
            self.check_data()
        except ConfigError as e:
            Logger.error('[fs_data] Exception: %s' % e)
            return False
        else:
            # 转换成json字符串格式，提高日志可读性；
            Logger.info('[fs_data] curr_config: %s' % dumps(self._curr_config, indent=4))
            return True

    def reload(self):
        """
        热加载配置文件

        reload时保存上一次配置文件数据；
        防止修改配置文件后之前的数据可能无法继续同步。

        参数：None
        返回值：bool值
        """
        self._last_config = self._curr_config
        Logger.info('[fs_data] last_config: %s' % dumps(self._last_config, indent=4))

        _prev_miss_listen = Global.G_MISS_LISTEN.copy()
        _ret = self.steps()

        Global.G_APPEAR_LISTEN = _prev_miss_listen - Global.G_MISS_LISTEN
        return _ret

    def get_config_data(self, last=False):
        if last:
            return self._last_config
        return self._curr_config

    def parsed_data(self):
        config_file = Global.G_CONF_INI

        if not Common.is_file(config_file):
            raise ConfigError("%s is not exist !" % config_file)

        # 配置文件一次性解析到字典中
        ParserConfig(config_file).parse_to_dict(self._curr_config)

        if not self._curr_config:
            raise ConfigError("parser %s failed" % config_file)

    @classmethod
    def _check_type(cls, value, types):
        """
        核查元素数据类型

        注: value进来的都是字符串

        参数：
            value：元素值
            type：核查类型

        返回值：bool值
        """
        if types == 'str_type' and value == '':
            return False
        elif types == 'bool_type' and value not in ['true', 'false']:
            return False
        elif types == 'int_type':
            try:
                if int(value) <= 0:
                    return False
            except:
                return False
        elif types == 'float_type':
            try:
                if float(value) < 0:
                    return False
            except:
                return False
        return True

    def check_data(self):
        """
        配置项元素核查

        核查元素是否存在且类型是否正确
        注：只做required元素的核查；
        optional元素不核查，后续使用时如果不存在，则使用默认值

        参数：None

        返回值：None
        """
        if 'GLOBAL' not in self._curr_config:
            raise ConfigError("GLOBAL section not in config file")

        Global.G_MISS_LISTEN.clear()
        inner_type = ['str_type', 'int_type', 'bool_type']
        inner_keys = ['__GLOBAL_REQUIRED__', '__LISTEN_REQUIRED__']
        listen_keys = [x for x in self._curr_config if x not in inner_keys]
        listen_keys.remove('GLOBAL')
        if not listen_keys:
            raise ConfigError("listen path is NULL")
        global_required = {}
        listen_required = {}

        """ 获取GLOBAL和监听目录各自元素的类型 """
        for inner in inner_keys:
            if inner not in self._curr_config:
                raise ConfigError("%s section not in config file" % inner)
            tmp_maps = self._curr_config[inner]

            if inner == '__GLOBAL_REQUIRED__':
                check_data = global_required
            else:
                check_data = listen_required
            for types in inner_type:
                check_str = tmp_maps[types]
                if check_str == '':
                    continue
                check_keys = check_str.split('\n')
                check_data[types] = check_keys

        """ GLOBAL section下元素核查 """
        for types, check_keys in global_required.items():
            for key in check_keys:
                # 判断必要元素是否存在
                if key not in self._curr_config['GLOBAL']:
                    raise ConfigError("%s option is not in GLOBAL" % key)
                value = self._curr_config['GLOBAL'][key]
                # 判断对应元素是否满足类型要求
                if not self._check_type(value, types):
                    raise ConfigError("%s of GLOBAL must be %s"
                                      % (key, types))

        """ 监听目录section下元素核查 """
        for types, check_keys in listen_required.items():
            for key in check_keys:
                for listen in listen_keys:
                    # 判断元素是否存在
                    if key not in self._curr_config[listen]:
                        raise ConfigError("%s option is not in %s"
                                          % (key, listen))
                    value = self._curr_config[listen][key]
                    # 判断对应元素是否满足类型要求
                    if not self._check_type(value, types):
                        raise ConfigError("%s of %s must be %s"
                                          % (key, listen, types))
                    # 判断监听路径是否存在
                    if not Common.is_exists(listen):
                        # 先过滤，然后加入Monitor中动态监控，后续目录存在后自动reload
                        if listen not in Global.G_MISS_LISTEN:
                            Logger.warn("path of %s is not exist" % listen)
                            Global.G_MISS_LISTEN.add(listen)
                            continue
        # 剔除内部核查数据
        [self._curr_config.pop(inner) for inner in inner_keys]
        # 剔除目录不存在的监听项
        [self._curr_config.pop(m) for m in Global.G_MISS_LISTEN]

        del inner_type
        del inner_keys
        del listen_keys
        del global_required
        del listen_required


class TaskQueue:
    """ 任务队列 """
    _task_queue = None
    _limit_size = None
    _thread_count = None
    _lock = Lock()

    @classmethod
    def init(cls, limit_size, thread_count):
        cls._task_queue = []
        cls._limit_size = limit_size
        cls._thread_count = thread_count

    @classmethod
    def status(cls):
        return cls._task_queue

    @classmethod
    def push_task(cls, task):
        """ list.append为原子操作，不需要加锁 """
        if task in cls._task_queue:
            return
        """ 检查队列大小 """
        length_task = len(cls._task_queue)
        half_limit = cls._limit_size / 2
        if length_task > half_limit:
            Logger.warn("[fs_data] Task count > %s !!" % half_limit)
        elif length_task >= cls._limit_size:
            Logger.error("[fs_data] Task count >= %s, "
                         "can't append task anymore !!" % cls._limit_size)
            return
        cls._task_queue.append(task)

    @classmethod
    def request_tesk(cls):
        """ 工作线程获取任务，加锁 """
        cls._lock.acquire()
        _len = len(cls._task_queue)
        if _len == 0:
            cls._lock.release()
            return
        Logger.debug("[fs_data] Task count=%s" % _len)
        # TODO 这个分配机制太简陋，待优化
        if _len > 100:
            index = int(_len/cls._thread_count)
        elif 50 <= _len < 100:
            index = 15
        elif 10 <= _len < 50:
            index = 8
        else:
            index = _len

        out_task = cls._task_queue[:index]
        cls._task_queue = cls._task_queue[index:]

        # 释放锁
        cls._lock.release()
        return out_task


class RetryQueue:
    """ 失败重传队列 """
    _task_queue = []
    _limit_size = None

    @classmethod
    def init(cls, limit_size):
        cls._limit_size = limit_size

    @classmethod
    def status(cls):
        return cls._task_queue

    @classmethod
    def push_task(cls, task):
        if task in cls._task_queue:
            return
        """ 检查队列大小 """
        length_task = len(cls._task_queue)
        half_limit = cls._limit_size / 2
        if length_task > half_limit:
            Logger.warn("[fs_data] Task count > %s !!" % half_limit)
        elif length_task >= cls._limit_size:
            Logger.error("[fs_data] Task count >= %s, "
                         "can't append task anymore !!" % cls._limit_size)
            return
        cls._task_queue.append(task)

    @classmethod
    def request_task(cls):
        out_task = cls._task_queue[:]
        cls._task_queue = []
        return out_task


class StateInfo:
    _inotify_pid = None
    _connected_ip = None
    _syncing_task = None
    _waiting_task = None
    _retry_task = None

    @classmethod
    def set_inotify_pid(cls, pid):
        cls._inotify_pid = pid

    @classmethod
    def set_connected_ip(cls, ip_list):
        cls._connected_ip = ip_list

    @classmethod
    def set_syncing_task(cls, task_list):
        cls._syncing_task = task_list

    @classmethod
    def set_waiting_task(cls, task_list):
        cls._waiting_task = task_list

    @classmethod
    def set_retry_task(cls, task_list):
        cls._retry_task = task_list

    @classmethod
    def get_state_info(cls):
        status_info = """
        [PIDS]
         daemon pid: %s
        inotify pid: %s
        
        [TASK-COUNT]
        syncing: %s
        waiting: %s
          retry: %s
        
        [TASK-LIST]
        syncing: %s
          retry: %s

        [OTHERS]
        connected-ip: %s
        missing-path: %s
        """ % (Common.get_pid(),
               cls._inotify_pid,
               len(cls._syncing_task) if cls._syncing_task else 0,
               len(cls._waiting_task) if cls._waiting_task else 0,
               len(cls._retry_task) if cls._retry_task else 0,
               cls._syncing_task,
               cls._retry_task,
               cls._connected_ip,
               list(Global.G_MISS_LISTEN))
        return status_info



