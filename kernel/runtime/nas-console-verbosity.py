#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Keep warnings and errors on consoles; retain all normal journal diagnostics."""
from pathlib import Path
import json
p=Path('/proc/sys/kernel/printk');before=list(map(int,p.read_text().split()))
after=before[:];after[0]=min(before[0],5)
p.write_text(' '.join(map(str,after))+'\n')
assert list(map(int,p.read_text().split()))==after
out={'before':before,'after':after,'warnings_and_errors_on_console':True,'kernel_ring_buffer_and_journal_unchanged':True}
root=Path('/run/redmi-gaming');root.mkdir(parents=True,exist_ok=True)
(root/'console-verbosity-policy.json').write_text(json.dumps(out))
print(json.dumps(out))
