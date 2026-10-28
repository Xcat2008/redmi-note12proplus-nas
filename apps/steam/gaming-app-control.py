#!/usr/bin/python3
"""Fixed native app controls. No account, library or content metadata is read."""
from pathlib import Path
import json,subprocess,sys,time,os,signal,re

STEAM='redmi-steam-trial.service'
RETROARCH='redmi-retroarch-native.service'
PREFIX=['docker','exec','-u','abc','-e','DISPLAY=:1','retroarch']

def run(args,timeout=15):
    return subprocess.run(args,capture_output=True,text=True,timeout=timeout)

def status():
    r=run(['systemctl','show',STEAM,'-p','ActiveState','-p','UnitFileState','-p','LoadState'])
    d=dict(l.split('=',1) for l in r.stdout.splitlines() if '=' in l)
    r=run(['systemctl','is-active',RETROARCH])
    return dict(installed=Path('/DATA/AppData/custom-steam/bin/start-steam').exists(),running=d.get('ActiveState')=='active',startupEnabled=d.get('UnitFileState')=='enabled',retroarchInstalled=Path('/usr/bin/retroarch').exists(),retroarchRunning=r.stdout.strip()=='active')

def focus(app,wait=0):
    pattern='steam' if app=='steam' else '^retroarch$'
    end=time.monotonic()+wait
    while True:
        r=run(PREFIX+['xdotool','search','--onlyvisible','--name','[Bb]ig [Pp]icture'],10) if app=='steam' else run(PREFIX+['xdotool','search','--onlyvisible','--class',pattern],10)
        if not r.stdout.strip():r=run(PREFIX+['xdotool','search','--onlyvisible','--class',pattern],10)
        if not r.stdout.strip():r=run(PREFIX+['xdotool','search','--class',pattern],10)
        windows=[]
        for value in r.stdout.split():
            if not value.isdigit():continue
            result=run(PREFIX+['xdotool','getwindowgeometry','--shell',value],5)
            d=dict(l.split('=',1) for l in result.stdout.splitlines() if '=' in l)
            w=int(d.get('WIDTH','0'));h=int(d.get('HEIGHT','0'))
            if w>=300 and h>=180:windows.append((w*h,value))
        if windows:
            window=max(windows)[1]
            other='^retroarch$' if app=='steam' else 'steam'
            found=run(PREFIX+['xdotool','search','--onlyvisible','--class',other],10)
            for other_window in found.stdout.split():
                if other_window.isdigit():run(PREFIX+['xdotool','windowminimize',other_window],5)
            run(PREFIX+['xdotool','windowmap',window],5)
            if app=='steam':
                display=run(PREFIX+['xdotool','getdisplaygeometry'],5)
                dimensions=display.stdout.split()
                if len(dimensions)==2 and all(x.isdigit() and 16<=int(x)<=16384 for x in dimensions):
                    run(PREFIX+['xdotool','windowsize','--sync',window,*dimensions],5)
                    run(PREFIX+['xdotool','windowmove','--sync',window,'0','0'],5)
            return run(PREFIX+['xdotool','windowactivate','--sync',window],10).returncode==0
        if time.monotonic()>=end:return False
        time.sleep(.5)

def action(name):
    if name=='status':return status()
    if os.geteuid()!=0:raise RuntimeError('Administrator access required.')
    if name=='steam-start':
        if status()['retroarchRunning']:
            try:state=json.loads(Path('/run/redmi-gaming/gaming-idle-state.json').read_text())
            except (OSError,ValueError):state={}
            if state.get('content_state')!='empty':raise RuntimeError('Close the current RetroArch content before switching to Steam.')
            r=run(['systemctl','stop',RETROARCH],25)
            if r.returncode:raise RuntimeError('RetroArch could not close cleanly.')
        # Clear the previous app's backdrop before showing the independent Steam client.
        run(PREFIX+['xsetroot','-solid','#101827'],5)
        r=run(['systemctl','start',STEAM],30)
        if r.returncode:raise RuntimeError('Steam could not start. Check that the gaming session is running.')
        focused=focus('steam',30)
        if focused:
            ready=run(PREFIX+['xdotool','search','--onlyvisible','--name','[Bb]ig [Pp]icture'],5)
            if ready.stdout.strip():return dict(**status(),focused=True)
            pid=run(['docker','inspect','-f','{{.State.Pid}}','retroarch']).stdout.strip()
            if pid.isdigit() and int(pid)>1:
                try:run(['nsenter','-t',pid,'-n','-i','runuser','-u','nas','--','/DATA/AppData/custom-steam/bin/start-steam','steam://open/bigpicture'],5)
                except subprocess.TimeoutExpired:pass
                focused=focus('steam',10)
        return dict(**status(),focused=focused)
    if name=='steam-stop':
        r=run(['systemctl','disable','--now',STEAM],25)
        if r.returncode:raise RuntimeError('Steam could not stop cleanly.')
        return status()
    if name=='retroarch-focus':
        r=run(['systemctl','start',RETROARCH],25)
        if r.returncode:raise RuntimeError('RetroArch could not start.')
        return dict(**status(),focused=focus('retroarch',20))
    if name=='retroarch-stop':
        r=run(['systemctl','stop',RETROARCH],25)
        if r.returncode:raise RuntimeError('RetroArch could not stop cleanly.')
        return status()
    raise RuntimeError('Unknown application operation.')

if __name__=='__main__':
    try:
        if len(sys.argv)!=2:raise RuntimeError('Choose one application operation.')
        print(json.dumps(dict(data=action(sys.argv[1]))))
    except Exception as e:
        print(json.dumps(dict(error=str(e) if isinstance(e,RuntimeError) else 'The application operation failed.')));sys.exit(1)
