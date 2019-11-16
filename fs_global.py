# -*- coding: UTF-8 -*-
G_LOG_LEVEL = 'info'
G_LOG_LIMIT = 20971520
G_LOG_PERIOD = 1800
G_LOG_DIR = '/home/ubp/logs/filesync'
G_LOGLEVEL_INI = 'loglevel.ini'
G_LOCAL_DIR = ''
G_CACHE_DIR = ''
G_RUN_DIR = ''
G_CONF_FILE = 'filesync.ini'
G_STATUS_FLAG = ''
G_RELOAD_FLAG = ''
G_RSYNC_USER = 'ubp'
G_INOTIFY_EVENT_MSGID = 'inotify_event_message_id'
G_STATUS_INFO = """[PIDS]
   host pid: %s
inotify pid: %s

[CONNECTED]
%s

[COUNT]
syncing: %s
waiting: %s
  retry: %s

[TASKS]
syncing: %s
  retry: %s

[TOP-N]
%s
"""