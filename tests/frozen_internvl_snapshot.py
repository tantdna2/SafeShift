"""Verify frozen InternVL assertions at their exact Git snapshot, not Mini HEAD.

The fulltrain inventory is dynamic: new MiniCPM files deliberately produce a
different source identity. Historical Operator bytes must be checked at BASE.
Only the bounded runtime inventory is materialized in a disposable CPU fixture.
"""
from functools import lru_cache
from pathlib import Path
import json
import subprocess
import sys
import tempfile

from safeshift.candidates.source import ROOT
from safeshift import internvl3763 as runtime

BASE = "341ab626ff2af7ef79ced0d9c3119794eea4a820"


@lru_cache(maxsize=2)
def observed(ref=BASE):
    names = runtime.source_spec()["manifest"]
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        for name in names:
            result = subprocess.run(["git", "show", ref + ":" + name], cwd=ROOT, capture_output=True)
            if result.returncode:
                # New Mini-only modules did not exist in the frozen tree.
                if name not in ("safeshift/fulltrain/minicpm_notebook.py", "safeshift/fulltrain/original_inputs.py",
                                "safeshift/fulltrain/minicpm_ui.py", "safeshift/fulltrain/minicpm_execution.py",
                                "safeshift/fulltrain/minicpm_release.py", "safeshift/fulltrain/minicpm_sizing.py"):
                    raise AssertionError("MISSING_FROZEN_RUNTIME_FILE:" + name)
                continue
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(result.stdout)
        code = """import json,sys
sys.path.insert(0,sys.argv[1])
from safeshift import internvl3763 as r, internvl3763_campaign as c
from safeshift.pilot.contract import digest
print(json.dumps({'source':digest(r.source_spec()), 'science':digest(c.science()),
    'manifest':r.source_spec()['manifest'], 'configuration':r.configuration(),
    'native':c.science()['native']}))
"""
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(target)],
            cwd=target, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)
