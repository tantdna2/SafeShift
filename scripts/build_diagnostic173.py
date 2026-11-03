"""Embed an exact committed, synthetic-only diagnostic; no TRAIN path."""
import argparse
import json
from pathlib import Path
from scripts.diagnostic173 import admit


def build(ref,identity):
    plan=admit(identity)
    if len(ref)!=40 or any(c not in '0123456789abcdef' for c in ref): raise ValueError('EXACT_COMMIT')
    return {'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
        'safeshift':{'historical_source_commit':ref,'identity':identity,'max_model_calls':0,
            'status':'TERMINAL_ARCHIVE_NO_REPLAY','model_key':plan['key']}},
        'cells':[{'cell_type':'markdown','id':'archive','metadata':{},'source':[
            '# Archived diagnostic â€” NO EXECUTION\n',
            'Original submitted notebook and source are preserved at the historical Git commit and private Kaggle version.\n',
            'The completed diagnostic cannot be replayed using this current notebook. See Issue173 diagnostic evidence.\n']},
            {'cell_type':'code','id':'terminal','metadata':{},'outputs':[],'execution_count':None,
             'source':["raise PermissionError('ISSUE173_DIAGNOSTIC_CAMPAIGN_TERMINAL_NO_REPLAY')\n"]}]}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--source-commit',required=True); p.add_argument('--identity',required=True)
    p.add_argument('--output',required=True); a=p.parse_args()
    with Path(a.output).open('xb') as stream: stream.write((json.dumps(build(a.source_commit,a.identity),indent=1)+'\n').encode())
