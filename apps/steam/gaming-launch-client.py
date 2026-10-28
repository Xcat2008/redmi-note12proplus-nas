#!/usr/bin/python3
import socket,json,sys
action={'steam':'steam-start','retroarch':'retroarch-focus'}.get(sys.argv[1] if len(sys.argv)==2 else '')
if action is None:raise SystemExit(2)
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
    s.settimeout(65);s.connect('/config/.XDG/gaming-app-launch.sock')
    s.sendall(json.dumps({'action':action}).encode())
    result=json.loads(s.recv(8192))
if 'error' in result:
    print(result['error'],file=sys.stderr);raise SystemExit(1)
if action=='retroarch-focus' and not result.get('data',{}).get('focused'):raise SystemExit(1)
