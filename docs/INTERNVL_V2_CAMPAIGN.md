# PR177: exact-release technical campaign

Authority: [Owner/ChatGPT 6622148168](https://github.com/tantdna2/SafeShift/pull/177#issuecomment-6622148168).
This supersedes the earlier CPU-only task only for this new campaign. Issue173
remains closed. Implementation stays on `feat/internvl-grammar-v2-native`, PR177.

The next stopping point is a committed HEAD for ChatGPT review and independent
Antigravity audit. No Kaggle API activity, submission, GPU or private image read
is part of this implementation pass. A separate machine-readable release must
bind that HEAD, committed notebook, runtime manifest, request and job before
preflight. This document is a design contract, not that release.

Limits: three private jobs cumulatively (including preflight), sequential,
1800 seconds/job, one planned weight load and **one native generation call for
the entire campaign**. Preflight has zero image reads, loads and calls. Original
master TRAIN ordinal0 is the only native target. Its master checksum and original
InternVL smoke archive checksum establish identity; the private request also pins
sample, locator and image digests. No GT selection, TEST or full TRAIN execution.

GitHub annotated tags in a dedicated campaign namespace are create-only ledger
records. Creating a tag ref is atomic; existing refs, lost responses and conflicts
stop. Records do not advance the reviewed PR HEAD or require another branch.
Each submitted job reserves a slot before Kaggle POST. Fresh per-process nonces
and ordered launch/setup/worker/load/call permits prevent replay across VMs.
The single campaign load and call refs never expire or reset. Credentials remain
only in the local coordinator; workers use bounded public GitHub reads.

Every later job requires a fresh exact job-specific release, all earlier jobs
terminal, and complete private sealed ZIP/log evidence reconciled with external
ledger records. A missing call record alone never proves zero calls. A reserved
call blocks the campaign permanently, including INVALID and technical failure.
Uncertain push/SDK/log/terminal/archive state stops without resubmission. A source
change invalidates release and requires fresh review/audit before another job.

Checkpoint, C1, parser, approved grammar bytes, FP16/eager/greedy policy and four
labels remain unchanged. Raw forward logits, mask/processors, returned token IDs
and exact response are persisted before parsing. HNLO stays null with
`HNLO_NA_GRAMMAR_POLICY_V2`. Historical predictions are never imported or pooled.

Public receipts contain hashes, counts and sanitized errors only. Native raw,
request, paths and logs stay in private output archives. Final trial status must
be SUCCESS, INVALID or TECHNICAL_ERROR; CPU tests cannot establish GPU/model PASS.
