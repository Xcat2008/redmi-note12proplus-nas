#!/usr/bin/python3
"""Local, descriptor-only bridge to the Android hardware video services."""
import array, json, os, select, signal, socket, stat, struct, subprocess, threading

SOCKET = '/usr/local/lib/redmi-nas/mediatek/run/transcode.sock'
PROGRAM = '/data/local/tmp/redmi-nas-video/surface-transcode'
slots = threading.BoundedSemaphore(2)

def handle(conn):
    proc = None
    acquired = False
    try:
        _, uid, _ = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid not in (0, 911, 32011): raise ValueError('Unauthorized local user')
        conn.settimeout(15)
        request, anc, flags, _ = conn.recvmsg(4096, socket.CMSG_SPACE(4))
        descriptors = array.array('i')
        for level, kind, data in anc:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS: descriptors.frombytes(data[:len(data)//4*4])
        if len(descriptors) != 1:
            for fd in descriptors: os.close(fd)
            raise ValueError('Exactly one input descriptor required')
        fd = descriptors[0]
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode): raise ValueError('Regular media file required')
            cfg = json.loads(request)
            width, height, bitrate, seek, gop = [int(cfg[k]) for k in ('width','height','bitrate','seek_us','gop')]
            fps_num,fps_den=int(cfg.get('fps_num',30)),int(cfg.get('fps_den',1))
            if not (1 <= fps_num <= 1000000 and 1 <= fps_den <= 1000000 and 1 <= fps_num/fps_den <= 120): raise ValueError('Unsupported frame rate')
            if not (64 <= width <= 3840 and 64 <= height <= 2160 and width%2 == height%2 == 0 and 64000 <= bitrate <= 80000000 and 0 <= seek <= 86400000000 and 1 <= gop <= 1200): raise ValueError('Unsupported video parameters')
            acquired = slots.acquire(blocking=False)
            if not acquired: raise ValueError('Hardware sessions busy')
            init_pid = int(subprocess.check_output(['/usr/bin/lxc-info','-n','android','-pH'],text=True,timeout=3).strip())
            # lxc-attach chmods/chowns stdio descriptors; nsenter preserves the
            # read-only media descriptor and its owner's file permissions.
            command = ['/usr/bin/nsenter','--target',str(init_pid),'--mount','--pid','--root','--wd=/','--',PROGRAM,'-','-',str(width),str(height),str(bitrate),str(seek),'0',str(gop),format(fps_num/fps_den,'.12g')]
            proc = subprocess.Popen(command, stdin=fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        finally: os.close(fd)
        def report():
            try:
                for line in proc.stderr:
                    print('video: '+line.decode('utf-8','replace').rstrip()[:2500],flush=True)
            except (OSError,ValueError): pass
        threading.Thread(target=report,daemon=True).start()
        conn.settimeout(30)
        ready,_,_=select.select([proc.stdout,conn],[],[],15)
        if conn in ready or proc.stdout not in ready: raise RuntimeError('Hardware video startup cancelled or timed out')
        first=os.read(proc.stdout.fileno(),4096)
        if not first: raise RuntimeError('Hardware video initialization failed')
        conn.sendall(b'OK\n'+first)
        conn.settimeout(None)
        while True:
            readable,_,_=select.select([proc.stdout,conn],[],[],60)
            if conn in readable: break
            if proc.stdout not in readable: raise RuntimeError('Hardware video stopped producing output')
            data=os.read(proc.stdout.fileno(),65536)
            if not data: break
            conn.sendall(data)
    except Exception as exc:
        try: conn.sendall(('ERROR '+str(exc)+'\n').encode())
        except OSError: pass
        print('video: '+str(exc),flush=True)
    finally:
        conn.close()
        if proc is not None:
            if proc.poll() is None:
                try: os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=3)
                except (ProcessLookupError,subprocess.TimeoutExpired):
                    try: os.killpg(proc.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
            proc.stdout.close();proc.stderr.close()
        if acquired: slots.release()

os.makedirs(os.path.dirname(SOCKET),exist_ok=True)
try: os.unlink(SOCKET)
except FileNotFoundError: pass
server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
server.bind(SOCKET);os.chown(SOCKET,0,911);os.chmod(SOCKET,0o660)
server.listen(4)
print('Local hardware-video broker ready',flush=True)
while True:
    conn,_=server.accept()
    threading.Thread(target=handle,args=(conn,),daemon=True).start()
