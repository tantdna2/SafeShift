# Owner continuous technical retry — PR177

Authority: [Owner comment6626498951](https://github.com/tantdna2/SafeShift/pull/177#issuecomment-6626498951),
authenticated as `tantdna2`; UTF-8 body SHA256
`03407e1981f90a7b03f7ddcd0baacdec32b0f204d7a2afaf040bb17fae76240b`.
Starting branch HEAD `24db08d005e2ea884ad86e0943f0035a9c075468`;
main `4578c175e0011783c3573d0003fc5341eaf3ef72`.

This append-only operational decision supersedes the three-job/3600-GPU-second
cap and pre-result audit hold ONLY for new namespace `internvl-v2-6626498951`.
Historical `internvl-v2-6622148168` j1/j2, twelve refs, failed archives and charged
2400 reserved GPU-seconds remain immutable. No historical PASS or refund.
INDEPENDENT_AUDIT=PENDING_POST_RESULT; SCIENTIFIC_QUALIFICATION=NOT_ESTABLISHED.

Each new sequential job has a fresh authenticated Owner release bound to clean
HEAD, committed notebook, source manifest, request and ordinal0 identity. Reserve
one load and one generation per attempt, with create-only nonce permits and
external ledger. Reconcile every predecessor's terminal state and sealed outcome
before another submission; unknown consumption/state blocks. Stop after verified
native success. No fixed attempt count; provider quota is checked before each
submission, no concurrent reservation, optional explicit cumulative quota cap.

Per job: 1800 server wall seconds, conservative two-T4 reservation3600 physical
GPU-seconds, no refund. Setup remains bounded900s; worker up to remaining budget,
including a bounded180s synthetic processor child. Coordinator/release window
3600s allows queue and export; it does not extend server/runtime execution.
New namespace uses two ordered phases in one job: complete source/checkpoint,
CPU/ABI, GPU, allocation and unchanged16GiB RAM checks; persist positive internal
preflight before reading original image or reserving model load. Then same
native FP16/eager/grammarV2/C1/strict parser/HNLO N/A and one ordinal0 call.

Repair hypothesis: Job2 checkpoint hashing increased cgroup file accounting by
9,552,867,328 bytes. Stream every locked shard through bounded aligned buffers,
SHA256 all actual bytes, and issue file-descriptor-local POSIX_FADV_DONTNEED for
already-read clean ranges. Recheck descriptor/path identity, size, timestamps,
exact allowlist and final SHA256. Never modify Input bytes, global drop_caches,
skip hashes, subtract file cache from RAM accounting or lower the16GiB floor.
Repeat this verification at the real loader boundary, with bounded snapshots
and receipts. Advice is not a reclaim guarantee: fresh cgroup/RSS and unchanged
resource checks decide admission. See [Linux syscall contract](https://man7.org/linux/man-pages/man2/posix_fadvise.2.html).

CPU tests must establish hash equivalence, exact byte coverage, tamper/alias/
size/advice failures, bounds, ordered preflight, per-attempt exclusivity, terminal
reconciliation, quota and historical-policy isolation. Linux synthetic cache
measurements are software evidence only. Actual T4 load/forward/export remains
NOT_VERIFIED until a sealed real result is independently replayed.

No new science decision, model/checkpoint/revision/prompt/token policy/label/
parser/HNLO changes; no GT rescue, TEST/full TRAIN, scientific pooling or merge.
Final result, evidence, PROJECT_STATE and tests stay in existing Draft PR177 for
ChatGPT review and independent Antigravity audit after technical outcome.
