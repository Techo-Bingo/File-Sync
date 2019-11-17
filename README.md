# File-Sync
__双机海量文件实时同步方案__


***
python3适配
***

* fs_inotify.py:            event_line = str(_readline(), encoding='utf-8').strip()
* fs_util.py:        return p.returncode, str(out, encoding='utf-8'), str(err, encoding='utf-8')
* fs_util.py:import configparser as ConfigParser

***
* fping编译安装后适配路径
  * fs_slaves.py:        out_info = Common.shell_cmd("cat %s |/usr/local/fping/sbin/fping"

***
* inotify编译安装后适配路径
 * filesync.ini:inotify_path = /usr/local/inotify/bin/inotifywait
