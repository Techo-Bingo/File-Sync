# -*- coding: UTF-8 -*-
"""
工作线程管理模块

本模块负责文件/目录的同步细节，以及管控等
"""
import fs_global as Global
from time import sleep
from fs_data import TaskQueue, RetryQueue
from fs_logger import Logger
from fs_data import ConfigWrapper
from fs_util import ThreadPool, MyThreading, Common, FileOP, Counter, Singleton


class WarnExcept(Exception):
    """ warn级别异常 """
    pass


class ErrorExcept(Exception):
    """ error级别异常 """
    pass


class Slaves(Singleton):
    """ 工作线程管理类 """

    def __init__(self, count):
        self.count = count
        self.pool = None
        self.curr_listen = None
        self.last_listen = None
        self.retry_period = 60
        self.check_period = 60
        self.worker_period = 1
        self.connect_list = []
        self.syncing = []
        self.ready_flag = False

    def init(self):
        """ 重写基类的init, 用于避免使用signal机制，统一由Master调度 """
        pass

    def find_listen(self, task):
        """
        找到task对应配置文件中监听的目录

        先从当前配置文件数据字典中找，
        如果没找到再到reload之前的配置文件数据中找，

        参数：
            1. 具体任务

        返回值：
            任务所在的监听目录;
            是否是上一次的配置文件数据
        """
        _contain = Common.is_contain

        for listen in self.curr_listen:
            if not _contain(listen, task):
                continue
            else:
                return listen, False

        # 继续从reload之前的配置中寻找
        for listen in self.last_listen:
            if not _contain(listen, task):
                continue
            else:
                return listen, True
        return None, None

    def combine(self, thread_id, task):
        """
        组合rsync同步参数

        通过task找到对应的监听目录后，找到该监听目录对应的其他配置参数

        参数：
            task: 具体任务

        返回值：
            rsync同步命令字符串
        """

        # 如果是临时目录或文件，同步可能会失败，需要判断一下目录或文件在不在
        if not Common.is_exists(task):
            raise WarnExcept("is not exist, ignore...")

        listen, last = self.find_listen(task)
        if not listen:
            raise ErrorExcept("not in config ini, ignore...")

        if last:
            Logger.warn('[thread%s] %s in last config section %s' % (thread_id, task, listen))

        _get_listen_value = ConfigWrapper.get_key_value
        remote_mkdir = _get_listen_value('make_remote_dir', last=last)
        remote_ips = _get_listen_value('remote_ip', listen, last).split(',')
        checksum = _get_listen_value('checksum', listen, last)
        compress = _get_listen_value('compress', listen, last)
        exclude = _get_listen_value('exclude', listen, last)
        param = "%s -a" % Global.G_RSYNC_TOOL
        task_dir, task_file = Common.split_path(task)

        if checksum == 'true':
            param += 'c'
        if compress == 'true':
            param += 'z'
        if exclude:
            # 只有一个过滤条件时，不能用{}，否则过滤会失效
            if len(exclude.split(',')) == 1:
                param += ' --exclude=%s' % exclude
            else:
                param += ' --exclude={%s}' % exclude

        cmd_dict = {}
        """ 判断IP是否可达 """
        for remote_ip in remote_ips:
            if remote_ip not in self.connect_list:
                Logger.warn("[thread%s] %s is unavailable IP, ignore %s" % (thread_id, remote_ip, task))
                continue

            # 注：任务可能是文件也可能是目录
            # 统一取上一层目录，进入后同步
            param += " --delete --rsh=ssh %s %s@%s:%s" % (task_file, Global.G_RSYNC_USER, remote_ip, task_dir)
            # 如果full_sync为false或者其他场景下，同步可能会因对端的目录不存在而报错
            # 这里根据make_remote_dir配置，判断是否先登录对端创建该目录，开启会影响同步性能
            prev_cmd = None
            if remote_mkdir == 'true':
                prev_cmd = "ssh %s@%s 'mkdir -p %s'" % (Global.G_RSYNC_USER, remote_ip, task_dir)
            cmd = "cd %s && %s" % (task_dir, param)
            if prev_cmd:
                cmd = ';'.join([prev_cmd, cmd])
            cmd_dict[remote_ip] = cmd
        return cmd_dict

    @Counter
    def rsync(self, cmd):
        """
        同步动作函数

        使用rsync同步文件或目录；
        使用Counter装饰器包装，用于计算耗时；

        返回值:(Counter中封装)
            ret:   退出值
            detail:命令执行结构详细输出信息
        """
        Logger.debug("[fs_slaves] exec: %s" % cmd)
        ret, out, err = Common.shell_cmd(cmd)
        return ret, err

    def doing(self, thread_id, task, is_retry):
        """ 先组装同步参数再执行同步 """
        ret, detail = -1, None
        self.syncing.append(task)
        try:
            cmd_dict = self.combine(thread_id, task)
            # 执行同步动作
            for ip, cmd in cmd_dict.items():
                ret, detail = self.rsync(cmd)
                detail = "To %s, %s" % (ip, detail)
        except WarnExcept as e:
            Logger.warn("[thread%s] WarnExcept %s %s" % (thread_id, task, e))
            cmd_dict = None
        except ErrorExcept as e:
            Logger.error("[thread%s] ErrorExcept %s %s" % (thread_id, task, e))
            cmd_dict = None
        finally:
            self.syncing.remove(task)
        if not cmd_dict:
            return
        # 0表示成功
        if not ret:
            Logger.info("[thread%s] sync success %s, %s" % (thread_id, task, detail))
        else:
            info = "[thread%s] sync failed %s, %s" % (thread_id, task, detail)
            if is_retry:
                Logger.error(info)
            else:
                Logger.warn(info)
                # 失败且不是失败重传任务时，放入失败队列进行重试
                RetryQueue.push_task(task)

    def deal(self, thread_id, task_list, is_retry=False):
        """
        同步任务处理函数

        在一些极端场景下会出现多个线程同时同步同一个文件或目录，
        因此任务消费时记录正在同步的任务，同步前判断该任务是否正在消费，
        有消费冲撞时，将任务暂存，待获取的所有任务消费完后再尝试一次，
        如果仍冲突，则该线程放弃该任务

        参数：
            1. thread_id: 线程id
            2. task_list: 该线程获取的任务列表

        返回值：None
        """

        # 用于暂存冲突的task
        collision = []
        for task in task_list:
            # Logger.info("[thread%s] deal %s" % (thread_id, task))
            if task not in self.syncing:
                self.doing(thread_id, task, is_retry)
                continue
            # task同步冲突时,暂存冲突的task，防止与其他线程重复同步
            Logger.debug("[thread%s] %s crash syncing" % (thread_id, task))
            collision.append(task)

        # 处理上一个循环中加入的冲突task
        for task in collision:
            if task not in self.syncing:
                self.doing(thread_id, task, is_retry)
                continue
            # 如果仍然冲突，那就直接丢弃
            Logger.debug("[thread%s] %s syncing still, ignored..."
                         % (thread_id, task))

    def require(self, args=None):
        """
        线程池处理函数

        请求同步任务并进行处理

        参数：
            args: 暂只包含线程id

        返回值: None
        """
        thread_id, = args
        task_list = TaskQueue.request_tesk()
        if not task_list:
            return
        Logger.info("[thread%s] got %s tasks:\n%s"
                    % (thread_id, len(task_list), '\n'.join(task_list)))
        self.set_config_data()
        self.deal(thread_id, task_list)

    def set_config_data(self):
        _curr = ConfigWrapper.get_listen_path(last=False)
        if self.curr_listen != _curr:
            self.curr_listen = _curr
            self.last_listen = ConfigWrapper.get_listen_path(last=True)

    def wait_for_ready(self):
        while 1:
            if self.ready_flag:
                return
            sleep(1)

    def retry_process(self, args=None):
        """
        失败重传线程处理函数

        小周期定时任务
        失败重传线程从失败重传队列中获取任务进行重传处理

        参数：None

        返回值：None
        """
        task_list = RetryQueue.request_task()
        if not task_list:
            return
        self.set_config_data()
        self.deal('Retry', task_list, True)

    def connect_check(self, args=None):
        """
        检验各个监听目录对应的对端IP是否可达
        使用fping 进行批量检测
        """
        _tmp_ip = []
        for last in [False, True]:
            for listen in ConfigWrapper.get_listen_path(last=last):
                ip_list = ConfigWrapper.get_key_value(key='remote_ip', section=listen, last=last).split(',')
                for ip in ip_list:
                    if not Common.is_ip(ip):
                        Logger.warn("[fs_slaves] IP of %s is invalid:%s, last:%s" % (listen, ip, last))
                        continue
                    if ip not in _tmp_ip:
                        _tmp_ip.append(ip)
        """ IP列表写入临时文件并执行fping """
        ip_list_ini = "%s/ip_list.ini" % Global.G_RUN_DIR
        check_cmd = "cat %s |sudo %s" % (ip_list_ini, Global.G_FPING_TOOL)
        FileOP.write_to_file(ip_list_ini, '\n'.join(_tmp_ip))
        out_info = Common.shell_cmd(check_cmd)[1]
        out_list = out_info.strip().split('\n')
        """ 保存正常连接的IP """
        for ip in _tmp_ip:
            ok_str = '%s is alive' % ip
            if ok_str not in out_list:
                Logger.warn('[fs_slaves] %s is disconnect' % ip)
                if ip in self.connect_list:
                    self.connect_list.remove(ip)
            elif ip not in self.connect_list:
                self.connect_list.append(ip)
        self.ready_flag = True
        # Logger.debug('[fs_slaves] connect_list=%s' % self._connect_list)

    def fully_sync(self, args=None):
        """
        大周期定时任务
        负责全量数据同步(只做当前配置文件的全量同步)

        注：首次启动时，需要等待IP检测（connect_check）完，
        否则首次全量数据同步会误认为对端IP不可用
        """
        self.wait_for_ready()

        task_list = []
        for listen in ConfigWrapper.get_listen_path():
            sync_all_switch = ConfigWrapper.get_key_value(key='full_sync',
                                                          section=listen
                                                          )
            if sync_all_switch == 'false':
                continue
            task_list.append(listen)
        self.set_config_data()
        # 全量同步不进行失败重传
        self.deal('Full', task_list, True)

    def start_worker(self):
        """ 启动任务处理工作线程 """
        self.pool = ThreadPool(func=self.require,
                               period=self.worker_period
                               )
        self.pool.init(self.count)
        self.pool.start()

    def start_retry(self):
        """ 启动失败重传任务线程 """
        MyThreading(func=self.retry_process,
                    period=self.retry_period
                    ).start()

    def start_checker(self):
        """ 启动链路状态检测任务线程 """
        MyThreading(func=self.connect_check,
                    period=self.check_period
                    ).start()

    def start_fullsync(self):
        """ 启动全量数据同步任务线程 """
        period = float(ConfigWrapper.get_key_value('fullsync_period'))
        MyThreading(func=self.fully_sync,
                    period=period
                    ).start()

    def start(self):
        self.start_checker()
        self.start_worker()
        self.start_retry()
        self.start_fullsync()

    def status(self):
        return self.syncing, self.connect_list

    def pause(self):
        if self.pool:
            self.pool.pause()

    def resume(self):
        if self.pool:
            self.pool.resume()
