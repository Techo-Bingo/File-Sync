# -*- coding: UTF-8 -*-
"""
公共方法模块

本模块提供一些通用公共方法,通过第三方模块实现
"""
import os
import pwd
import time
import threading
import subprocess
import ConfigParser


class Singleton(object):
    """ 使用__new__实现抽象单例 """

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance


def Counter(func):
    """
    计时装饰器

    参数：
        func: 需要计算函数执行时间的函数名

    返回值：
        ret: 函数执行的返回值；
        detail: 加入执行时间信息后的函数执行信息
    """

    def wrapper(*args, **kwargs):
        start = time.time()
        ret, err = func(*args, **kwargs)
        detail = "Cost time %.3fs" % (time.time() - start)
        # 失败时不为0
        if ret:
            detail = "%s; (ret:%s, err:%s)" % (detail, ret, err)
        return ret, detail
    return wrapper


class Common:
    """ 公共方法 """

    @classmethod
    def get_abspath(cls, path):
        return os.path.abspath(path)

    @classmethod
    def get_time(cls):
        ct = time.time()
        return '%s.%03d' \
               % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                  (ct - int(ct)) * 1000
                  )

    @classmethod
    def get_pid(cls):
        return os.getpid()

    @classmethod
    def pid_running(cls, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError as e:
            """ Operation not permitted (如ubp杀root)，说明有此PID """
            if 1 == e.errno:
                return True
            """ No such process 无此pid """
            if 3 == e.errno:
                return False
            return True

    @classmethod
    def start_thread(cls, target, args=()):
        thread = threading.Thread(target=target, args=args)
        thread.setDaemon(True)
        thread.start()

    @classmethod
    def mkdir(cls, dirpath):
        if os.path.isdir(dirpath):
            return True
        return os.makedirs(dirpath)

    @classmethod
    def chown(cls, filename, owner='ubp'):
        uid, gid = pwd.getpwnam(owner)[2:4]
        os.chown(filename, uid, gid)

    @classmethod
    def dirname(cls, path):
        return os.path.split(path)[0]

    @classmethod
    def split_path(cls, path):
        return os.path.split(path)

    @classmethod
    def is_ip(cls, ip):
        import re
        p = re.compile("^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
                       "(25[0-5]|2[0-4]\d|[01]?\d\d?)$")
        return p.match(ip)

    @classmethod
    def is_file(cls, filename):
        return os.path.isfile(filename)

    @classmethod
    def is_exists(cls, path):
        return os.path.exists(path)

    @classmethod
    def is_dir(cls, path):
        return os.path.isdir(path)

    @classmethod
    def is_contain(cls, directory, file):
        # directory = os.path.join(os.path.realpath(directory), '')
        directory = os.path.realpath(directory)
        file = os.path.realpath(file)
        if directory == file:
            return True
        return os.path.commonprefix([file, directory]) == directory

    @classmethod
    def exec_ret(cls, cmd):
        return cls.shell_cmd(cmd)[0]

    @classmethod
    def shell_cmd(cls, cmd):
        p = subprocess.Popen([cmd],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True)
        out, err = p.communicate()
        return p.returncode, out, err


class FileOP:
    """ 文件操作 """

    @classmethod
    def cat_file(cls, filename):
        try:
            with open(filename, 'r') as f:
                return f.read()
        except:
            return ''

    @classmethod
    def write_append_file(cls, filename, info):
        try:
            with open(filename, 'a+') as f:
                f.write(str(info) + '\n')
                return True
        except:
            return False

    @classmethod
    def write_to_file(cls, filename, info):
        try:
            with open(filename, 'w') as f:
                f.write(str(info))
                return True
        except:
            return False

    @classmethod
    def rm_file(cls, srcfile):
        try:
            srcfile = os.path.realpath(srcfile)
            os.remove(srcfile)
            return True
        except:
            return False

    @classmethod
    def get_size(cls, file_path):
        if not os.path.isfile(file_path):
            return 0
        return os.path.getsize(file_path)


class ParserConfig(object):
    """ 获取ini配置文件内容 """

    def __init__(self, conf_path):
        self.conf_path = conf_path
        self.conf = ConfigParser.ConfigParser()

    def get_sections(self):
        try:
            self.conf.read(self.conf_path)
            return self.conf.sections()
        except:
            return None

    def get_options(self, section):
        try:
            self.conf.read(self.conf_path)
            return self.conf.options(section)
        except:
            return None

    def get_value(self, section, option):
        try:
            self.conf.read(self.conf_path)
            return self.conf.get(section, option)
        except:
            return None

    def get_section_items(self, section):
        try:
            self.conf.read(self.conf_path)
            return self.conf.items(section)
        except:
            return None

    def parse_to_dict(self, out_dict):
        try:
            for section in self.get_sections():
                out_dict[section] = dict(self.get_section_items(section))
            return True
        except:
            out_dict = {}
            return False


class MyThreading(threading.Thread):
    """
    提供灵活控制线程的类

    MyThreading.start()  开启线程
    MyThreading.pause()  暂停线程
    MyThreading.resume() 恢复线程
    MyThreading.stop()   停止线程
    """

    def __init__(self, func, period=10, args=()):
        super(MyThreading, self).__init__()
        self.func = func
        self.period = period
        self.args = args
        self.daemon = True
        self._pause_flag = threading.Event()
        self._run_flag = threading.Event()
        self._pause_flag.set()
        self._run_flag.set()

    def run(self):
        _run_flag = self._run_flag.isSet
        _pause_wait = self._pause_flag.wait
        _sleep = time.sleep

        while _run_flag():
            _pause_wait()
            self.func(self.args)
            _sleep(self.period)

    def pause(self):
        self._pause_flag.clear()

    def resume(self):
        self._pause_flag.set()

    def stop(self):
        self._pause_flag.set()
        self._run_flag.clear()


class ThreadPool(object):
    """ 线程池调度类 """

    def __init__(self, func, period, args=()):
        self.func = func
        self.period = period
        self.args = args
        self._thread_list = []

    def init(self, count=1):
        if not isinstance(count, int):
            return False
        self._thread_list = [MyThreading(func=self.func,
                                         period=self.period,
                                         args=(i,) + self.args
                                         ) for i in range(count)]

    def stop(self):
        [_thread.stop() for _thread in self._thread_list]

    def start(self):
        [_thread.start() for _thread in self._thread_list]

    def pause(self):
        [_thread.pause() for _thread in self._thread_list]

    def resume(self):
        [_thread.resume() for _thread in self._thread_list]


if __name__ == '__main__':
    """ 本模块测试代码 """
    def test_func(args):
        seq, name = args
        print('{} Thread{} name:{} is running'.format(time.time(), seq, name))

    pool = ThreadPool(test_func, 2, args=('test',))
    pool.init(5)
    pool.start()

    time.sleep(20)
    pool.pause()

    time.sleep(10)
    pool.resume()

    time.sleep(20)
    pool.stop()






