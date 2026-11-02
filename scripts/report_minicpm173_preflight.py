from pathlib import Path
import json,zipfile,sys
import argparse
p=argparse.ArgumentParser(description="Verify the closed MiniCPM-only no-inference RAM preflight export.")
p.add_argument('--archive',required=True); p.add_argument('--output',required=True)
a=p.parse_args()
from safeshift.pilot.artifacts import sha,verify_archive,read,write
archive=Path(a.archive)
assert sha(archive)==read(Path(str(archive)+'.sha256.json'))['sha256']=='fee13e27fb4e9056284a6c11b8ac7dba84dcd654a909f8fe821450f21a8592f3'
members=verify_archive(archive)
assert not any(n.endswith(('native_call.json','consumption.json','model-load-reservation.json','loaded-environment.json')) for n in members)
with zipfile.ZipFile(archive) as bundle:
    get=lambda n:json.loads(bundle.read(n))
    result=get('result.json'); gate=get('preload-ram-gate.json'); advice=get('owned-cache-advice.json')
    assert result['status']=='PREFLIGHT_PASS_NATIVE_REVIEW_HOLD'
    assert result['model_calls']==0 and result['weights_loaded'] is False and result['consumption_created'] is False
    assert gate['available_bytes']>=gate['required_bytes']==17179869184 and gate['status']=='PASS'
    assert advice['scan_complete'] and advice['deleted_files']==0 and not advice['input_or_checkpoint_bytes_changed']
    stages={}
    for name in members:
        if name.endswith('-memory.json'):
            value=get(name)
            stages[name]={'available_bytes':value['available_bytes'],'cgroup_current_bytes':int(value['memory.current']),
                'cgroup_max_bytes':int(value['memory.max']),'cgroup_stat':value['memory.stat'],
                'cgroup_events':value['memory.events'],'self_memory_kib':value['self_smaps_rollup_kib'],
                'owned_process_count':len(value['owned_process_tree']),
                'direct_child_count':len(value['direct_children']),'process_tree_bound_reached':value['process_tree_bound_reached']}
    for name in ('setup-after-child-exit-memory.json','processor-after-child-exit-memory.json','final-memory.json'):
        assert stages[name]['direct_child_count']==0 and stages[name]['owned_process_count']==1
    supervisors={n:get(n) for n in members if n.endswith('-supervisor.json')}
    assert len(supervisors)==2 and all(v['status']=='EXITED' and v['returncode']==0 and v['group_kill_sent'] and not v['automatic_retry'] for v in supervisors.values())
    timeline=get('memory-timeline.json')
    assert len(timeline)>100
    receipt={'schema':'issue173-review-minicpm-only-ram-evidence-v1','result':result,
        'archive_sha256':sha(archive),'verified_members':len(members)+1,'timeline_samples':len(timeline),
        'memory_stages':stages,'ram_gate':gate,'owned_cache_advice':advice,'supervisors':supervisors,
        'processor':get('processor-result.json'),'cuda':get('cuda.json'),
        'driver':get('worker-driver-diagnostic.json'),'driver_binding':get('driver-library-binding.json'),
        'native_load_reservations':0,'native_markers':0,'consumption_markers':0,
        'history_consistency':get('history.json'),'prepared_continuation':get('prepared-mini-only-request.json'),
        'no_child_survivors_observed_after_stages':True,
        'software_identity':get('software.json')['identity'],
        'no_inference_ready_claim':True,'model_fit':'NOT_VERIFIED',
        'inference_activation':'BLOCKED_PENDING_CHATGPT_DIRECT_REVIEW'}
    # Runtime identity contains only portable machine/runtime facts but absolute
    # unique scratch paths are unnecessary in public review evidence.
    identity=receipt['software_identity']
    receipt['software_identity']={k:v for k,v in identity.items() if k not in ('executable','prefix','base_prefix','site_packages','sys_path','site_package_paths')}
write(Path(a.output),receipt)
print(json.dumps({'status':result['status'],'ram_gate':gate,'model_calls':0,'weights_loaded':False,
    'verified_members':len(members)+1,'timeline_samples':len(timeline),'native_dispatch':'BLOCKED_PENDING_CHATGPT_REVIEW'},indent=2))
