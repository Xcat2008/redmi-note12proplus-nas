#!/usr/bin/python3
"""Read cached Wi-Fi lists for dashboard metrics; keep explicit scans available."""
import os
import sys
args=sys.argv[1:]
words=[arg.lower() for arg in args]
listing=any(words[i:i+3] in (['device','wifi','list'],['dev','wifi','list']) for i in range(max(0,len(words)-2)))
explicit=any(arg=='--rescan' or arg.startswith('--rescan=') for arg in words)
metrics_fields='active,ssid,bssid,mode,chan,freq,signal,security,wpa-flags,rsn-flags'
metrics=any(args[i] in ('--fields','-f') and args[i+1]==metrics_fields for i in range(max(0,len(args)-1)))
if listing and metrics and not explicit:
    args+=['--rescan','no']
os.execv('/usr/bin/nmcli',['/usr/bin/nmcli',*args])
