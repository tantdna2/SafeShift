"""Conservative admission arithmetic, including live evidence and uncompressed archive."""
from .inputs import TrainInputError

GIB = 2**30
PRIMARY_PER_SAMPLE = 2 * 2**20
SIDECARS_PER_SAMPLE = 2**20
FILES_PER_SAMPLE = 192
RUN_RESERVE = 256 * 2**20
OUTPUT_CAP = 18 * GIB  # Internal budget, not an assertion about a venue quota.


def admit_gpu(model, observation):
    rows = [line.split(',') for line in observation.strip().splitlines()]
    try:
        free = [int(row[2].strip()) * 2**20 for row in rows]
    except (IndexError, ValueError) as error:
        raise TrainInputError('GPU_BUDGET_OBSERVATION_UNREADABLE') from error
    selected = [0, 1] if model == 'qwen3' else [0]
    # Qwen's observed pilot peak is ~13.44 GiB. Keep additional headroom;
    # this is an admission estimate, never a worst-case TRAIN guarantee.
    minimum = (14 if model == 'qwen3' else 6) * GIB
    if len(free) != 2 or any(free[i] < minimum for i in selected):
        raise TrainInputError('GPU_FREE_BUDGET_INSUFFICIENT', selected_devices=selected,
            required_free_bytes_per_device=minimum, observed_free_bytes=free)
    return {'selected_devices': selected, 'required_free_bytes_per_device': minimum,
            'observed_free_bytes': free, 'all_image_peak_verified': False}


def estimate(count, staging_bytes):
    live = count * (PRIMARY_PER_SAMPLE + SIDECARS_PER_SAMPLE) + RUN_RESERVE
    archive = live + count * FILES_PER_SAMPLE * 2048 + RUN_RESERVE
    return {'planned': count, 'staging_bytes': staging_bytes, 'live_evidence_bytes': live,
        'archive_and_tar_headers_bytes': archive, 'output_required_bytes': live + archive + GIB,
        'scratch_required_bytes': 50 * GIB + staging_bytes + GIB,
        'ram_required_bytes': 24 * GIB, 'output_cap_bytes': OUTPUT_CAP,
        'sidecars_per_sample_bytes': SIDECARS_PER_SAMPLE, 'files_per_sample_bound': FILES_PER_SAMPLE,
        'full_vocab_replay': False, 'estimate_only': True}


def admit(plan, *, output_free, scratch_free, same_device=False, existing_output=0):
    required_output = plan['output_required_bytes']
    if required_output + existing_output > plan['output_cap_bytes']:
        raise TrainInputError('OUTPUT_CAP_INSUFFICIENT', required_bytes=required_output,
            existing_bytes=existing_output, cap_bytes=plan['output_cap_bytes'])
    if output_free < required_output:
        raise TrainInputError('OUTPUT_FREE_INSUFFICIENT', required_bytes=required_output, free_bytes=output_free)
    required_scratch = plan['scratch_required_bytes'] + (required_output if same_device else 0)
    if scratch_free < required_scratch:
        raise TrainInputError('SCRATCH_FREE_INSUFFICIENT', required_bytes=required_scratch,
            free_bytes=scratch_free, shared_output_device=same_device)
    return {**plan, 'output_free_bytes': output_free, 'scratch_free_bytes': scratch_free,
            'shared_output_device': same_device, 'existing_output_bytes': existing_output}
