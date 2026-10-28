#!/usr/bin/python3
"""Local Sunshine launcher; only root and the NAS user may invoke fixed actions."""
import socket,struct,json,subprocess,os,signal
from pathlib import Path

path=Path('/DATA/AppData/custom-retroarch/config/.XDG/gaming-app-launch.sock')
server=None
bound_inode=None

def bind_server():
    global server,bound_inode
    if server is not None:server.close()
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and not path.is_socket():raise RuntimeError('Launcher path is not a socket')
    path.unlink(missing_ok=True)
    server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    server.bind(str(path));os.chown(path,0,32011);path.chmod(0o660)
    bound_inode=path.stat().st_ino
    server.listen(4);server.settimeout(1)

def binding_exists():
    try:return path.is_socket() and path.stat().st_ino==bound_inode
    except OSError:return False
def stop(*_):
    if server is not None:server.close()
    if binding_exists():path.unlink(missing_ok=True)
    raise SystemExit()
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
while True:
    try:
        # The container reinitializes XDG runtime files on cold startup.
        # Rebind rather than keeping a live descriptor to an unlinked socket.
        if not binding_exists():bind_server()
        connection,_=server.accept()
    except socket.timeout:continue
    except OSError:
        import time
        time.sleep(1);continue
    with connection:
        connection.settimeout(3)
        _,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if uid not in (0,32011):
            connection.sendall(b'{"error":"Access denied"}\n');continue
        try:
            raw=connection.recv(512);request=json.loads(raw)
            name=request.get('action')
            if name not in ('steam-start','retroarch-focus'):raise ValueError()
            result=subprocess.run(['/usr/local/lib/redmi-nas/steam/gaming-app-control.py',name],capture_output=True,timeout=65)
            response=result.stdout[:8192] if result.stdout else b'{"error":"Application launch failed"}'
        except Exception:response=b'{"error":"Application launch failed"}'
        try:connection.sendall(response+b'\n')
        except OSError:pass
