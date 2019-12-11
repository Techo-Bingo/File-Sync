# -*- coding: UTF-8 -*-
"""
公共方法模块

本模块提供一些通用公共方法,通过第三方模块实现
"""
import os
import sys
import pwd
import time
import errno
import getpass
import atexit
import signal
import threading
import subprocess
from fs_message import Subscriber
if sys.version_info[0] == 2:
    import ConfigParser
else:
    import configparser as ConfigParser


class Singleton(object):
    """ 使用__new__实现抽象单例 """

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance

    def signal_handler(self, sig):
        eval('self.%s' % sig)()

    def register_signal(self):
        sub = Subscriber(self.__class__.__name__)
        sub.register('SIGNAL', self.signal_handler)

    def steps(self):
        """ 子类重写此函数即可完成初始化步骤 """
        return True

    def init(self):
        if not self.steps():
            return False
        self.register_signal()
        return True

    def start(self):
        pass

    def stop(self):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def reload(self):
        pass

    def status(self):
        pass


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
    def get_abspath(cls):
        return os.path.abspath(os.path.split(__file__)[0])

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
    def chown(cls, filename, owner):
        uid, gid = pwd.getpwnam(owner)[2:4]
        os.chown(filename, uid, gid)

    @classmethod
    def dirname(cls, path):
        return os.path.split(path)[0]

    @classmethod
    def split_path(cls, path):
        return os.path.split(path)

    @classmethod
    def join_path(cls, _path, path_):
        return os.path.join(_path, path_)

    @classmethod
    def is_ip(cls, ip):
        import re
        p = re.compile("^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
                       "(25[0-5]|2[0-4]\d|[01]?\d\d?)$")
        return p.match(ip)

    @classmethod
    def user_match(cls, user_name):
        return getpass.getuser() == user_name

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
    def stream_2_str(cls, in_ss):
        if sys.version_info[0] == 2:
            return in_ss
        else:
            return str(in_ss, encoding='utf-8')

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
        return p.returncode, cls.stream_2_str(out), cls.stream_2_str(err)


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


class Daemon(object):
    """ Daemon进程封装类  """

    def __init__(self, pidfile, stdout, actions):
        self.pidfile = pidfile
        self.stdout = stdout
        self.start_action = actions[0]
        self.stop_action = actions[1]
        self.pause_action = actions[2]
        self.resume_action = actions[3]
        self.reload_action = actions[4]
        self.status_action = actions[5]
        self.sig_pause = 10
        self.sig_resume = 12
        self.sig_reload = 30
        self.sig_status = 31

    @classmethod
    def sys_err(cls, msg):
        sys.stderr.write(str(msg)+'\n')

    def daemonize(self):
        try:
            if os.fork() > 0:
                raise SystemExit(0)
        except OSError as e:
            raise RuntimeError("fork failed: %s\n" % e)

        os.chdir('/')
        os.setsid()
        os.umask(0o22)

        try:
            if os.fork() > 0:
                raise SystemExit(0)
        except OSError as e:
            raise RuntimeError("fork failed : %s\n" % e)

        sys.stdout.flush()
        sys.stderr.flush()

        with open('/dev/null', 'r') as read:
            os.dup2(read.fileno(), sys.stdin.fileno())
        with open(self.stdout, 'a+') as write:
            os.dup2(write.fileno(), sys.stdout.fileno())
            os.dup2(write.fileno(), sys.stderr.fileno())

        with open(self.pidfile, 'w') as f:
            f.write(str(os.getpid()))
        atexit.register(os.remove, self.pidfile)

        # 注册信号处理回调函数
        signal.signal(signal.SIGTERM, self.stop_handle)
        signal.signal(self.sig_pause, self.pause_action)
        signal.signal(self.sig_resume, self.resume_action)
        signal.signal(self.sig_reload, self.reload_action)
        signal.signal(self.sig_status, self.status_action)

    def send_signal(self, signum):
        """
        :param signum:  信号值
        :return:
            0： pid文件不存在，进程不存在
            1： pid文件存在，pid进程存在
            2： pid文件存在，pid进程不存在
            3： pid文件存在，pid进程存在但无权限
        """
        if not os.path.isfile(self.pidfile):
            return 0
        with open(self.pidfile) as f:
            pid = int(f.read())
        try:
            os.kill(pid, signum)
            return 1
        except OSError as e:
            if e.errno == errno.ESRCH:  # No such process
                self.sys_err("No such process, Daemon not running?")
                return 2
            elif e.errno == errno.EPERM:  # Deny access to
                self.sys_err("Deny access to, Daemon running in root?")
                return 3
            else:
                self.sys_err(e)
                return 0

    def stop_handle(self, signum, stack=None):
        """ 接收到退出信号的动作 """
        self.stop_action()
        sys.exit(0)

    def start(self):
        try:
            # signal 0 探测pid对应进程是否存在
            if self.send_signal(0) in [1, 3]:
                raise RuntimeError("Already running.\n")
            self.daemonize()
        except RuntimeError as e:
            self.sys_err(e)
            raise SystemExit(1)
        self.start_action()

    def stop(self):
        """ 发送SIGTERM信号给pid """
        if self.send_signal(signal.SIGTERM):
            try:
                os.remove(self.pidfile)
            except:
                pass

    def restart(self):
        self.stop()
        self.start()

    def pause(self):
        if self.send_signal(self.sig_pause) != 1:
            self.sys_err('Not running or permission deny')
            raise SystemExit(1)

    def resume(self):
        if self.send_signal(self.sig_resume) != 1:
            self.sys_err('Not running or permission deny')
            raise SystemExit(1)

    def reload(self, param=None):
        if self.send_signal(self.sig_reload) != 1:
            self.sys_err('Not running or permission deny')
            raise SystemExit(1)

    def status(self):
        if self.send_signal(self.sig_status) != 1:
            self.sys_err('Not running or permission deny')
            raise SystemExit(1)






