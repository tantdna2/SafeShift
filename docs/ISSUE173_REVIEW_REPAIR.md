# PR175 review continuation — 03/11/2026

Same Codex session, branch `verify/issue173-real-checkpoints`,
[Draft PR175](https://github.com/tantdna2/SafeShift/pull/175).
Basis: [ChatGPT review6584783261](https://github.com/tantdna2/SafeShift/pull/175#issuecomment-6584783261)
at `f801ae553355bdd1b843438c881dc212417a7346` and the Owner's direct A–D task.
Review remains CHANGES_REQUIRED until independently rechecked; merge and audit
are not claimed. This source revision is post-run terminal/preflight work,
not a re-attribution of the original v5 execution at `1e744d9`.

## A. Permanent terminal fence

The current `scripts/smoke_kaggle173.py` has no executable model load/generation
body. `launch`, `worker`, `once`, `scope`, Qwen constructor and old software
route raise PermissionError immediately, before paths/history/approval flags.
ACTIVE_KEYS is empty. The published `SafeShift_ISSUE173_SMOKE.ipynb` is replaced
with a terminal archival notebook: its sole code cell raises before imports,
payload extraction or I/O. Its generator cannot produce the old dispatch route.
Absent per-VM markers, v1–v4 history, a valid v5 seal or a forged approval cannot
reopen it. The original v5 notebook bytes remain at the original Git ref and
private staged submission, and all five original ZIPs/receipts remain immutable.
Historical copies are evidence, not current execution authority; no claim that
old code copies can be remotely revoked without a shared control service.

`safeshift/smoke173_history.py` rehashes all five original ZIPs against exact
published SHA256s plus sidecars/member seals. It reconciles actual native markers,
raw/result custody, same image and MiniCPM absence of call/load reservations.
The result is {Qwen:1, InternVL:1, MiniCPM:0}; a checksum is not a signature or
approval. Omitted, reordered or forged v5 evidence blocks history admission.
The new identity `issue173-minicpm-only-review-hold-20261103-v1` prepares only an
ordinal0/one-load/one-call MiniCPM request. Both its launch and worker are hard
REVIEW HOLD; no caller-provided approved flag or RAM receipt can enable them.

## B. Exact saved InternVL INVALID

Read-only diagnosis uses the original v5 ZIP SHA
`035c4d9b0216378e23ecc812e1221d68fe451ec25a9cbc3fd8977b5794690619`,
not another attempt. The model itself generated a Markdown JSON code fence
around an otherwise JSON object with a canonical safety_level value. Raw text,
the actual predicted value, generated IDs and input identities are kept private.

All14 generated IDs match native greedy argmax, including the fence tokens.
Native returned sequence exactly equals input prefix plus saved continuation;
an independent Rust tokenizer decode using the hash-locked tokenizer file
matches the raw response. Saved tokenizer replay also matched. C1 is present
once, has its exact original SHA, and expressly forbids code fences. The native
assistant template does not inject the output fence. Greedy/max64 config is
exact, no actual logits processors or capture errors, finite steps, EOS present
at token14: no truncation. Source implementation hashes match the locks; saved
pixel/tile/image-token dimensions and input length satisfy the original checks.

Supported cause: **generated output violates the frozen C1 format**, not a
demonstrated decode, prefix-slicing, capture or processor-contract bug. This
does not establish semantic image quality or rule out every unobserved model
failure. INVALID, original raw, consumed call and unavailable HNLO remain.
No technical change to native adapters is justified by these observations.
Stripping fences, accepting an inner JSON, changing the template/prompt, adding
constraints or changing max tokens would alter parser/generation/preprocessing
semantics and require a separately versioned scientific/comparability decision.
None is applied or authorized here; no InternVL rerun occurs.

Reproduce the sanitized diagnosis (requires the existing private ZIP and the
already downloaded public tokenizer; no model or image read):

```console
python -B -m scripts.diagnose_internvl173 --archive <private-v5.zip> --tokenizer <locked-tokenizer.json> --output data/processed/issue173-verification/new-invalid-diagnosis.json
```

The independent diagnostic tokenizer engine is0.22.2, separately identified from
the original pinned runtime. Its byte-identical decoded text agrees with the
original saved pinned-runtime/independent-decoder witness; it is not an inference
runtime migration. Only structural checks/checksums, no raw text/IDs, are exported.

## C. Fresh MiniCPM-only resource investigation — actual preflight PASS, native HOLD

The earlier shared VM retained InternVL's runtime and file pages. Its post-call
last available RAM was15,512,223,744 bytes, already below the unchanged16 GiB
pre-load floor. MiniCPM setup then left6,543,110,144 bytes; advisory reclaim raised
that to13,950,664,704. The old scan walked both model runtimes and stopped at
50,000 files. Its7,707,605,625 advised bytes include the prior5,381,544,449-byte
InternVL runtime, leaving incomplete coverage of the new MiniCPM tree. This
proves the scan was partial; the earlier receipt lacks a cgroup file/anonymous
breakdown and per-process RSS, so the exact source of every charged byte is
unknown. Do not call all remaining usage a model allocation or a checkpoint error.

`scripts/minicpm173_preflight.py` prepares a separate fresh MiniCPM-only Kaggle
VM, with no preceding Qwen/InternVL load and no real images attached. It reuses
existing checkpoint metadata/source and actual byte-verification evidence;
does not reread8 GiB shards or copy weights to create avoidable page pressure.
It attaches the five sealed history Outputs, checks exact count/custody, installs
only the unchanged pinned MiniCPM CPython3.11.9/cu124 software in owned scratch,
constructs the actual processor/tokenizer/config (not a model), tests synthetic
image packing and an isolated CUDA FP16 tensor, and stops before weights.
Original FP16/eager/resampler-FP32 identity stays pinned; no quantization or
precision/revision change and no model-load/fit claim.

Named memory receipts cover startup, setup start/end, cache before/after,
software import, processor construction, synthetic packing, immediately before
weight load, and after child exit. A bounded0.5s timeline records memory.current,
memory.max/peak/events/stat (file/anon/cache counters), host-constrained available
RAM, self RSS/PSS and owned child-tree RSS/PIDs. All subprocess trees use the
existing supervisor/group cleanup; post-exit observations expose any survivors.
Only this unique single-model scratch tree's regular, non-hardlinked large files
receive fsync/advisory eviction. No files are deleted, no global drop_caches,
Input/checkpoint/raw/history modification, threshold reduction or retry.
The bounded scan records complete/partial coverage and cannot stand in for the
actual gate. Before-load RAM must be >=17,179,869,184 bytes in the real pinned
worker; failure is saved with actual measured numbers. Max1500s internal/1800s
job; zero model calls, weights loads, production slots or consumption markers.

The new notebook is diagnostic only. Even a RAM/CUDA/processor PASS cannot open
the MiniCPM review hold. **Stop for ChatGPT's direct anti-replay/resource review
before consuming the remaining MiniCPM call.** Live measurements and final-source
Linux test receipts will be appended here after the authorized no-inference
preflight. The actual results follow; they are a resource/processor preflight,
not a model-load or inference PASS.

### Actual Kaggle evidence

Private [MiniCPM RAM review notebook](https://www.kaggle.com/code/nguynanhtn/safeshift-issue173-minicpm-ram-review),
version1, kernel142345684, COMPLETE. Executed runtime source
`3fd0b8a1c2beba386c4ede0577284045ae0e6394`; notebook SHA
`2c14cd203bc5c24f14532a503c0e32d33b06162f02d5db5e21d0eb6773060cdc`.
All remote cell sources match the submitted notebook after Kaggle normalization.
ZIP SHA256 `fee13e27fb4e9056284a6c11b8ac7dba84dcd654a909f8fe821450f21a8592f3`,
43 members, CRC/member hashes/outer sidecar independently checked locally.
[Sanitized RAM/processor evidence](research/evidence/issue173/review/minicpm-only-ram-preflight.json)
and [source/quota check](research/evidence/issue173/review/kaggle-source-and-quota.json).

| Stage (same fresh MiniCPM-only VM) | Available RAM, bytes | Cgroup anonymous, bytes | Cgroup file memory, bytes |
| --- | ---: | ---: | ---: |
| Startup | 31,769,190,400 | 228,421,632 | 187,879,424 |
| After setup child exits | 17,761,562,624 | 235,851,776 | 13,711,212,544 |
| After owned file-page advice | 25,173,176,320 | 234,409,984 | 6,502,432,768 |
| Actual processor constructed | 24,358,436,864 | 678,961,152 | 6,868,832,256 |
| Immediately before weights (after CUDA tensor) | **24,321,982,464** | 682,553,344 | 6,898,835,456 |
| After processor child exits | 24,736,821,248 | 234,467,328 | 6,936,788,992 |

The unchanged16 GiB floor (17,179,869,184 bytes) passed in the actual pinned
worker with about22.65 GiB available. Own-tree scan completed31,776 files;
32 large regular files/5,381,269,953 bytes advised; no errors, **zero file
deletions**, no Input/checkpoint/history changes. File memory fell by about
7.21 GB over reclamation while anonymous memory stayed nearly constant. This
supports setup file-cache charge as the dominant pressure in this new VM;
the measured total drop is not attributed exclusively to the advised bytes.
It does not reconstruct the missing old-v5 cgroup breakdown. The fresh VM also
removes the known preceding InternVL workload and the old partial-tree scan.

555 bounded memory/process observations retained. Both supervised children
exited0, process groups cleaned, no direct children/survivors observed after
each stage or at the end. Setup264.36s; processor/CUDA/pre-load checks8.45s.
Exact CPython3.11.9/cu124 software/ABI, actual locked processor and synthetic
image packing, driver580.178.04/T4 and FP16 tensor PASS. Original checkpoint
byte verification is reused; metadata/index/source/physical shard sizes checked
without reading/copying8 GiB weights into the page cache. No real images attached.

**Weights loaded=false; native calls=0; consumption=false.** The ZIP contains
no load reservation, native-call marker or consumption marker. Aggregate remains
Qwen1/InternVL1/MiniCPM0, total2/3. GPU reservation0 after the job. No native call
is authorized by this preflight. `smoke173_history.launch/worker` still raise
MINICPM173_NATIVE_CALL_BLOCKED_PENDING_CHATGPT_DIRECT_REVIEW, including with
this real PASS receipt. Model fit/load/inference and fresh campaign release
remain NOT_VERIFIED/BLOCKED until the requested direct review and later exact
activation, with current history rechecked. A new VM must repeat live resource
admission; this memory number is not a transferable guarantee.

Reproduce the closed sanitized export check (no model/raw payload export):

```console
python -B -m scripts.report_minicpm173_preflight --archive <private-preflight.zip> --output data/processed/issue173-verification/new-ram-review-receipt.json
```

## D. Validation and preservation

CPU regressions exercise fresh EMPTY directories/direct launch/CLI/worker and
archival notebook refusal; full five-seal vs missing/forged v5; no fake MiniCPM
SUCCESS; generated-fence INVALID/corrupted decoder/prefix/argmax; unchanged RAM
boundary, owned-only advice and protected production fence. Historical single-call
tests remain reproducible at their immutable executed Git refs; current tests
require terminal behavior instead of reactivating old model factories.
Both Linux suites ran from the **same immutable new snapshot**
`1c40ff8ae31b53967f0df415f2b58609026df30a`: [Issue17341/41 PASS](research/evidence/issue173/review/linux-issue173-1c40ff8.json)
and [fulltrain55/55 PASS](research/evidence/issue173/review/linux-fulltrain-1c40ff8.json),
no skips/failures/errors, including actual Linux supervisor/CLI tests and six
historical PREP payloads. Later review reporting/docs/evidence do not change
the tested dispatch/preflight source or protected production contracts; no full
HEAD CI run or independent audit is claimed. Windows development had a read-only
fsync-mocking mismatch in one advice test, corrected in the test before the
immutable Linux run; no real native call occurred. Original source/receipts and
the actual v5 notebook have been rehashed and preserved.
No old receipt is relabeled, no native calls are added, and private artifacts
remain outside Git. Same Draft PR175 only; no merge or audit PASS.
