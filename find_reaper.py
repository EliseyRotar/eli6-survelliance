import psutil
for p in psutil.process_iter(['name', 'cmdline', 'create_time', 'memory_info']):
    try:
        cmd = p.info['cmdline'] or []
        cmd_str = ' '.join(cmd)
        if 'cam_reaper' in cmd_str:
            print('  pid=%d start=%.0f rss=%.0fMB cmd=%s' % (p.pid, p.info['create_time'], p.info['memory_info'].rss/1e6, cmd_str[:150]))
    except:
        pass
