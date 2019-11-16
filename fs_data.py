# -*- coding: UTF-8 -*-
"""
数据管理模块

本模块包括两种数据：
    1. 文件同步的配置文件数据；
    2. 过滤去重后的同步任务数据；
"""
from json import dumps
import fs_global as Global
from fs_util import Common, ParserConfig
from fs_logger import Logger
from threading import Lock


class ConfigError(Exception):
    """ 配置文件的异常 """
    pass


class ConfigWrapper:
    """ 数据包装层 """

    @classmethod
    def is_listen_file(cls, path):
        return path in ConfigData.get_config_data()

    @classmethod
    def get_listen_path(cls, last=False):
        _data = ConfigData.get_config_data(last)
        return [key for key in _data
                if key not in ['GLOBAL',
                               '__GLOBAL_REQUIRED__',
                               '__LISTEN_REQUIRED__'
                               ]]

    @classmethod
    def get_key_value(cls, key, section='GLOBAL', last=False):
        _data = ConfigData.get_config_data(last)
        if section not in _data:
            return None
        if key not in _data[section]:
            return None
        return _data[section][key]


class ConfigData:
    """ filesync配置文件数据类 """
    _curr_config = {}
    _last_config = {}

    @classmethod
    def _parsed_data(cls):
        config_file = Global.G_CONF_FILE

        if not Common.is_file(config_file):
            raise ConfigError("%s is not exist !" % config_file)

        # 配置文件一次性解析到字典中
        ParserConfig(config_file).parse_to_dict(cls._curr_config)

        if not cls._curr_config:
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
                if int(value) < 0:
                    return False
            except:
                return False
        return True

    @classmethod
    def _check_data(cls):
        """
        配置项元素核查

        核查元素是否存在且类型是否正确
        注：只做required元素的核查；
        optional元素不核查，后续使用时如果不存在，则使用默认值

        参数：None

        返回值：None
        """
        if 'GLOBAL' not in cls._curr_config:
            raise ConfigError("GLOBAL section not in config file")

        inner_type = ['str_type', 'int_type', 'bool_type']
        inner_keys = ['__GLOBAL_REQUIRED__', '__LISTEN_REQUIRED__']
        listen_keys = [x for x in cls._curr_config if x not in inner_keys]
        listen_keys.remove('GLOBAL')
        if not listen_keys:
            raise ConfigError("listen path is NULL")
        global_required = {}
        listen_required = {}

        """ 获取GLOBAL和监听目录各自元素的类型 """
        for inner in inner_keys:
            if inner not in cls._curr_config:
                raise ConfigError("%s section not in config file" % inner)
            tmp_maps = cls._curr_config[inner]

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
                if key not in cls._curr_config['GLOBAL']:
                    raise ConfigError("%s option is not in GLOBAL" % key)
                value = cls._curr_config['GLOBAL'][key]
                # 判断对应元素是否满足类型要求
                if not cls._check_type(value, types):
                    raise ConfigError("%s of GLOBAL must be %s"
                                      % (key, types))

        """ 监听目录section下元素核查 """
        for types, check_keys in listen_required.items():
            for key in check_keys:
                for listen in listen_keys:
                    # 判断监听路径是否存在
                    if not Common.is_exists(listen):
                        raise ConfigError("path of %s is not exist" % listen)
                    # 判断元素是否存在
                    if key not in cls._curr_config[listen]:
                        raise ConfigError("%s option is not in %s"
                                          % (key, listen))
                    value = cls._curr_config[listen][key]
                    # 判断对应元素是否满足类型要求
                    if not cls._check_type(value, types):
                        raise ConfigError("%s of %s must be %s"
                                          % (key, listen, types))

        """ 剔除内部核查数据 """
        [cls._curr_config.pop(inner) for inner in inner_keys]

        del inner_type
        del inner_keys
        del listen_keys
        del global_required
        del listen_required

    @classmethod
    def init_config(cls):
        """ 初始化配置文件 """
        cls._curr_config = {}
        try:
            # 解析配置文件
            cls._parsed_data()

            # 检查配置文件数据的正确性
            cls._check_data()

        except ConfigError as e:
            Logger.error('[fs_data] Exception: %s' % e)
            return False
        else:
            # 转换成json字符串格式，提高日志可读性；
            Logger.info('[fs_data] curr_config: %s'
                        % dumps(cls._curr_config, indent=4))
            return True

    @classmethod
    def reload_config(cls):
        """
        热加载配置文件

        reload时保存上一次配置文件数据；
        防止修改配置文件后之前的数据可能无法继续同步。

        参数：None

        返回值：bool值
        """
        cls._last_config = cls._curr_config
        Logger.info('[fs_data] last_config: %s'
                    % dumps(cls._last_config, indent=4))

        return cls.init_config()

    @classmethod
    def get_config_data(cls, last=False):
        if last:
            return cls._last_config
        return cls._curr_config


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

