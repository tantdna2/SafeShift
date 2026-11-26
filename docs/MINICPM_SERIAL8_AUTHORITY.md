# MiniCPM Serial 7 incident and Serial 8 source transition

## Serial 7 evidence

The Owner reported job `nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-7`,
version 1, as `COMPLETE` on Kaggle. GitHub independently confirmed the
Serial 7 release's Owner login, account ID, PR association and body SHA256.
[PR205 release](https://github.com/tantdna2/SafeShift/pull/205#issuecomment-6999442629).

| Checked locally | Evidence |
| --- | --- |
| Supervisor | `f92e03d5da344a9bab1baf16a1643ced.zip`, SHA256 `e189abc6e6df39804c2bd2ddf3bdd52f8d8a1485845ea136ee58068abd6daf56`. Sidecar, 60 members including the checksum manifest, member bytes and extracted copies checked. |
| Source and ticket | Source manifest `3bd387e15d62934a396c61af71d4519c0f71df73b4bdf806d17e3de8fb09a46e`. RSA ticket `ff86f3644cc315823dd44e4fee6c2a618ff3dbb6fece96f472454b20304370a9` binds the exact request and capsule. Both archived notebooks and capsule pairs agree with the signed reservation. |
| Terminal stage | `admit`, `setup` and `reclaim` returned successfully. `cpu-process.json` records exit 1, `CHILD_FAILURE`, a group kill and no surviving process. `release.json` records `BLOCKED`, `NO_ATTEMPT` and `SUPERVISED_CHILD_FAILURE`. |
| RAM | Advice covered 30,333 job-owned files and 5,952,947,062 bytes. Available memory was 20,100,947,968 bytes before advice and 25,758,027,776 bytes after it. The fresh reclaim gate measured 25,758,027,776 bytes against the signed 17,179,869,184-byte floor. |
| Result custody | Claims end at `reclaim`. CPU failed before the CPU claim and before `admission.stage` could create `cpu/failure.json`. No GPU, native, load or call claim appears. The downloaded inventory has no attempt ZIP and retention lists no attempt. Local disposition is 0 native loads, 0 native calls and 3,763 `NOT_ATTEMPTED`. |
| Holds | Both journals have reservation event `28379c3e4589f84a114461c7ff707a2d8b27044783378aebdfc73f1b9de3eb9c` and the registration matches the original fence. Total holds are 10,726 calls / 7 jobs / 201,600 physical GPU-seconds, including the full Serial 7 increment of 100 calls and 28,800 GPU-seconds. |

The traceback identifies the inherited V4-4 release comment lookup as the
failure point. PR205 combined HTTP errors, transport failures and malformed
responses in one exception. A counted replay with a clean 60-GET budget
rejects the 61st GET at that exact lookup. The historical HTTP status and
the starting balance of the real bucket are unavailable. The local evidence
is `LOCAL_DOWNLOAD_ONLY` until the read-only provider check verifies the
terminal job and exhaustive remote inventory.
[GitHub REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).

## GitHub GET budget

| Stage | PR205 successful path | Serial 8 successful path |
| --- | ---: | ---: |
| Launch (parent) | 21 | 22 |
| Admit | 10 | 2 |
| Setup | 10 | 2 |
| Reclaim | 10 | 2 |
| CPU | 10 | 2 |
| GPU | 10 | 2 |
| Native | 10 | 2 |
| **Total** | **81** | **34** |

PR205 counts came from replaying the exact archived source against recorded
GitHub responses with a counter. CPU tests exercise that request shape and
the new child CLI. The 22 launch GETs assume the runtime commit equals the
reviewed HEAD, with two distinct tree references. A third distinct tree
adds one launch GET. A simulated denial on the second CPU GET stops after 30
GETs and before the CPU claim. Earlier failures stop at the failing GET.
The transport issues one bounded request per call. HTTP 429 and 403 with
`X-RateLimit-Remaining: 0` or `Retry-After` carry a rate-limit code.
Unmarked 403, 404, timeouts, connection failures and malformed content have
separate codes. Logs omit response bodies and credentials.

## Authority contract

- The new release marker is `SAFESHIFT_MINICPM_OFFLINE_RELEASE_V4`. The
  approval map carries `authority_proof_sha256`, the canonical SHA256 of
  supporting GitHub responses. The grant subject excludes the approval map,
  so the four approvals can bind the subject before the final release
  records their locators and the proof digest. The signed ticket binds the
  entire grant.
- The parent reads the release and PR live and checks all four approval
  records, historical authority and rights, and exact runtime/review/merge
  tree blobs. It reads each distinct supporting endpoint once, verifies the
  canonical digest and writes the proof create-only. The proof contains
  public comment bodies and identity fields plus sorted Git tree rows.
- Every child reads the release and PR live and repeats the supporting
  checks on the digest-pinned bytes, including approval author and subject,
  complete trees and local runtime blob matches. Withdrawal or modification
  of the live release blocks later stages. Supporting records are fixed for
  that release. To revoke it during a job, withdraw the live release itself.
  A running stage remains bounded by the signed deadline, call gates and
  supervisor timeout. Kaggle GitHub reads are anonymous.
- The child checks the RSA ticket, exact request, launch window, predecessor
  claim and clean supervised predecessor return. Create-only claims block
  local replay. Serial 8 requires a fresh ticket and its own slug/version 1.
  Cross-VM control depends on the single original Operator, the historical
  fences and the fresh Owner gate covering quota, Inputs and absent jobs.

## After direct review, independent audit and separately authorized merge

1. The Owner runs the read-only verifier with
   `python -B -m scripts.owner_verify_minicpm_offline --owner-performs-network --serial7-closure --output data/processed/<new-directory>`.
   It checks the exact terminal version, notebook source and Input identities,
   private capsule bytes, exhaustive paginated Output inventory, supervisor
   ZIP and sidecar. It preserves a fresh provider closure in the specified
   directory. An extra or ambiguous output blocks the transition.
2. On the final reviewed source, use `scripts.minicpm_offline_continuation`
   with `--directory data/processed/<future-primary> serial8-spec --output <spec>`
   to build the unsigned spec from the frozen cohort and resource policy.
   Use `serial8-release-template --initial <spec> --serial7-closure <closure> --output <proposal>`.
   Fill the exact source refs, release window and approval locators. The
   Owner verifier with `--serial8-proof-proposal <proposal>` and a new
   `--output` file calculates the proof digest from GitHub. Put that digest
   into the final Owner release. Obtain the exports using
   `--authority-locator` after publication.
3. The original Operator uses a distinct primary/mirror pair and adds
   `--serial7-closure <closure>` to the existing `init` arguments. The
   new create-only fence and both registrations record the verified
   technical closure. They carry forward all 10,726 calls / 7 jobs /
   201,600 GPU-seconds. Serial 8 starts with empty result history, ordinal 0
   and all 3,763 `NOT_ATTEMPTED`. A fresh Owner quota/Inputs/no-active-job
   gate and live GitHub checks are required before the original Operator
   can stage the new signed ticket. The Owner performs the eventual run.

The original Serial 7 reservation stays in its original journal. The new
registration resolves it for continuation as
`FAILED_PRE_NATIVE_NO_USABLE_RESULTS` with zero calls, zero imported results
and zero refund. Result ingestion through `accept` requires an attempt ZIP.
Kaggle connectivity, the anonymous bucket available to a future job and
final-source GPU/model fit remain unverified.
