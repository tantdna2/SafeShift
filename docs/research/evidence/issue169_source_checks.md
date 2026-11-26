# Issue169 — receipt kiểm nguồn và tài liệu

Ngày02/11/2026, Asia/Bangkok. BASE
`afc932b2a43cf829db12f53d6ac3d578c6123eec`; branch
`docs/issue169-fulltrain-source-decision`. Kiểm bởi Codex, không CI hoặc
independent audit. Hồ sơ: [T4 v2](../T4_O2_SELECTION_DOSSIER_20261101.md#issue169-successor-full-train).

## Phạm vi và kết quả

Chỉ đọc tài liệu/metadata tracked trực tiếp liên quan. Không mở local HANDOFF,
Downloads, private manifests, ZIP/report/raw/GT/ảnh, weights hoặc TEST. Không
Kaggle/GPU/inference, acquisition/annotation, metric recount hoặc grant mới.
`model_calls=0`; `private_data_accessed=false`; `TEST_accessed=false`.
Đọc tên/path/hash có sẵn trong receipt không là quyền mở artifact đó.

GitHub CLI chính thức đã đọc Issue169 (không comments lúc kiểm), Issue167
CLOSED, main đúng BASE, PR168 MERGED đúng BASE và
[hậu merge6570735120](https://github.com/tantdna2/SafeShift/pull/168#issuecomment-6570735120).
[Owner label-only6567502211](https://github.com/tantdna2/SafeShift/pull/166#issuecomment-6567502211)
đã đọc trực tiếp; đây là quyết định disposition, không O2 hoặc học vụ.
Nguồn Owner01/11 và các receipt trước được kế thừa từ DECISIONS/T0/T4;
không tự thực hiện lại audit của người khác.

Các lỗi harness đã thấy: network sandbox proxy từ chối, Git index không cho
ghi; đã dùng quyền công cụ để đọc GitHub/tạo branch. Một lần xem cấu trúc JSON
dùng index0 cho `shards` dạng object gây KeyError; đã đọc đúng key, không sửa
receipt để vượt lỗi. Checker đầu tiên còn nhận nhầm URL HTTPS
là drive path; đã thêm ranh giới chữ vào regex và bỏ ví dụ chuỗi gây cùng false
positive trong mô tả receipt, rồi chạy lại. Các lỗi này không
là model/data failure.

Kiểm toàn bộ snapshot tìm thấy anchor cũ không còn tồn tại ở target hiện tại;
checker báo riêng `historical_link_gaps` và không sửa snapshot để giấu lỗi.
Mọi link/anchor **mới** vẫn bắt buộc PASS. Harness Windows stdout ban đầu dùng
cp1252 không in được tiếng Việt; checker đã đặt UTF-8, không đổi dữ liệu nguồn.

## Tái lập offline từ repository root

Python3.11+, standard library; không import SafeShift hoặc cài dependency.
Lưu nguyên code fence dưới thành file mới ignored
`data/processed/issue169/check_metadata.py`, chạy
`python -B data/processed/issue169/check_metadata.py` từ root. Stdout là receipt
aggregate; có thể lưu dưới tên mới trong cùng thư mục. Checker không tự ghi
đè file, không network, không đọc private path, không đọc nội dung manifest
lịch sử/per-image. Các hash manifest/archive/member được **đối chiếu metadata**,
không rehash artifact thật. Không chạy checker T1 cũ vì nó đọc private inputs.

```python
import hashlib
import json
import platform
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE = 'afc932b2a43cf829db12f53d6ac3d578c6123eec'
T4 = 'docs/research/evidence/t4_o2_metadata_20261101.json'
T0 = 'docs/research/evidence/t0_false_safe_20261101/summary.json'
T1 = 'docs/research/evidence/t1_feasibility_20261101.json'
SRC = 'docs/SOURCE_FEASIBILITY_RECEIPT_20261024.json'
MCP = 'docs/research/evidence/issue165_hnlo/public_receipt.json'
DOS = 'docs/research/T4_O2_SELECTION_DOSSIER_20261101.md'
DEC = 'docs/research/DECISIONS.md'
STATE = 'docs/PROJECT_STATE.md'
SELF = 'docs/research/evidence/issue169_source_checks.md'
ALLOWED = {DOS, DEC, STATE, SELF}
checks = []
def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def git(*args):
    return subprocess.check_output(['git', *args])
def raw(path):
    # Every read must be a tracked BASE document or this receipt.
    if path != SELF:
        git('cat-file', '-e', BASE + ':' + path)
    return Path(path).read_bytes()
def obj(path):
    return json.loads(raw(path))
def txt(path):
    return raw(path).decode('utf-8')

pins = {
    T4: 'ddce41482c0c0e2a219caad0c8775d187b0455e905fc0c1ab7198b04bf6b6d16',
    T0: 'b1de3faaed3dd3040bc0e74d0b0fcaff6769f682e765ab74214e749128043a3b',
    T1: 'd29dded68e8af745e2260aec0b8bec9cf26f15f7f8a82e2fb75e6f7acff78794',
    SRC: '4670b92ba67d1e4c24bfaf85a2fde19cbaa71a56af2927f379611682d610c0d3',
    MCP: 'dc96898caa4543c62c05554f8a4577b3a9e89e5402ca6a03189d10d902230209',
    'docs/research/SEMINAR_PROTOCOL.md': '54c5be6b67e768f8d4819193c5d06867edf02e2008db258731f6e5947ed06dc1',
    'docs/research/seminar_analysis_config.v1.json': 'dd3b86660f0795dba099abac0d8a3b8bd3498e625e49b128aa9c50e72639e5ff',
}
for path, expected in pins.items():
    check('pin:' + path, sha(raw(path)) == expected)
    check('base_bytes:' + path, raw(path) == git('show', BASE + ':' + path))
t4, t0, t1, src, mcp = map(obj, (T4, T0, T1, SRC, MCP))
for path in (T0, T1, SRC):
    check('t4_input:' + path, t4['input_sha256'][path] == pins[path])
total = Counter()
for q, t in zip(t4['qwen_original_shards'], t0['saved_report_recount']['shards']):
    s = src['original_qwen3_v4']['shards'][str(q['shard'])]
    unit = s['unit']
    check('qwen_identity:' + str(q['shard']), all([
        q['shard'] == t['shard'] == unit['shard'],
        q['run_id'] == unit['run_id'], q['attempt_id'] == unit['attempt_id'],
        q['model'] == unit['id'], q['revision'] == unit['revision'],
        q['implementation_commit'] == s['source']['implementation_commit'],
        q['source_payload_sha256'] == s['source']['payload_sha256'],
        q['authority_commit'] == s['source']['authority_commit'],
        q['series_id'] is None]))
    check('qwen_seals:' + str(q['shard']), all([
        q['archive_sha256'] == t['archive_sha256'] == s['archive_sha256'],
        q['planned_manifest_sha256'] == t['manifest_sha256'] == unit['inference_sha256'],
        q['archive_manifest_sha256'] == s['manifest_sha256'],
        q['report_sha256'] == t['samples_sha256'] == s['members'][q['report_member']]['sha256'],
        q['result_member_sha256'] == s['members']['evidence/result.json']['sha256'],
        q['binding_member_sha256'] == s['members']['evidence/binding.json']['sha256']]))
    check('qwen_counts:' + str(q['shard']),
          q['counts'] == t['status'] == s['status_counts'] and
          q['planned'] == t['planned'] == s['planned_n'] == sum(q['counts'].values()))
    total.update(q['counts'])
check('qwen_four_only', [q['shard'] for q in t4['qwen_original_shards']] == [0, 1, 2, 3])
check('qwen_total', dict(total) == {'SUCCESS': 3539, 'TECHNICAL_ERROR': 1, 'NOT_ATTEMPTED': 223}
      and dict(total) == t0['saved_report_recount']['status'] == src['original_qwen3_v4']['status_counts']
      and sum(total.values()) == 3763)
check('qwen_config_unknown', t4['qwen_authority']['standalone_effective_configuration_sha256'] is None)
for name in ('internvl35', 'minicpm4'):
    peer, old = t4['peers'][name], t0['official160_receipt_projections'][name]
    keys = ('run_id', 'attempt_id', 'series_id', 'run_kind', 'archive_sha256',
            'counts', 'native_calls', 'numeric_hnlo_count', 'receipt_path', 'receipt_sha256')
    check('peer_projection:' + name, all(peer[k] == old[k] for k in keys))
    check('peer_receipt_pin:' + name, peer['receipt_sha256'] == t1['input_sha256'][peer['receipt_path']])
    check('peer_coverage:' + name, sum(peer['counts'].values()) == 160 and 160 + 3603 == 3763)
    check('peer_report_unknown:' + name, peer['report_member_sha256'] is None)
check('manifest160', t4['official160_manifest_sha256'] == t0['official160_manifest']['sha256'])
check('internvl_kind', t4['peers']['internvl35']['run_kind'] == 'RECOVERY')
check('minicpm_derivation_binding', all(mcp[k] == t4['peers']['minicpm4'][k] for k in
      ('run_id', 'series_id', 'attempt_id', 'run_kind', 'archive_sha256',
       'source_sha256', 'configuration_sha256', 'descriptor_sha256')))
check('minicpm_negative', mcp['hnlo_valid'] == 0 and mcp['original_success'] == 155
      and mcp['original_invalid'] == 5 and mcp['planned'] == 160)
check('pending_preserved', t4['decision_status'] == 'PROPOSED_NOT_APPROVED'
      and all(v is None for v in t4['approval'].values()) and mcp['scientific_selection'] == 'PENDING')

new_sections = {}
for path, marker in ((DOS, '## Owner successor scope'), (STATE, '## Issue #167')):
    old, new = git('show', BASE + ':' + path), raw(path)
    head, tail = old.split(b'\n\n', 1)
    check('snapshot_bytes:' + path, new.startswith(head + b'\n\n') and new.endswith(tail))
    new_sections[path] = new.decode('utf-8').split(marker, 1)[0]
old_dec = git('show', BASE + ':' + DEC)
check('decisions_append_only', raw(DEC).startswith(old_dec))
new_sections[DEC] = raw(DEC)[len(old_dec):].decode('utf-8')
new_sections[SELF] = txt(SELF).split('```python', 1)[0]
for prefix, count in (('O', 6), ('L', 4), ('B', 6)):
    check('matrix:' + prefix, all('| ' + prefix + str(i) + ' ' in new_sections[DOS]
          for i in range(1, count + 1)))
check('proposal_status', 'PROPOSED_FOR_OWNER_REVIEW' in new_sections[DOS]
      and 'EXECUTION=BLOCKED' in new_sections[DOS])
known_hashes = set(re.findall(r'\b[0-9a-f]{40,64}\b', txt(T4) + txt(MCP))) | {BASE}
check('new_dossier_hash_literals', set(re.findall(r'\b[0-9a-f]{40,64}\b', new_sections[DOS])) <= known_hashes)

def anchor(heading):
    text = re.sub(r'[`*_]', '', heading).lower()
    return ''.join(c for c in text if c in '-_ ' or unicodedata.category(c)[0] in 'LN').replace(' ', '-')
link_count = 0
historical_link_gaps = []
for path in (DOS, DEC, STATE, SELF):
    content = txt(path)
    check('utf8_no_bom:' + path, not raw(path).startswith(b'\xef\xbb\xbf'))
    check('fences:' + path, len(re.findall(r'^```', content, re.M)) % 2 == 0)
    # Validate local links in entire changed docs, excluding executable receipt fence.
    prose = re.sub(r'```.*?```', '', content, flags=re.S)
    for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', prose):
        if link.startswith(('https://', 'http://')):
            continue
        destination, _, fragment = unquote(link).partition('#')
        target = (Path(path).parent / destination).resolve() if destination else Path(path).resolve()
        relative = target.relative_to(Path.cwd().resolve()).as_posix()
        check('link:' + path + ':' + link, target.is_file())
        if relative != SELF:
            git('cat-file', '-e', BASE + ':' + relative)
        if fragment:
            headings = re.findall(r'^#+ (.+)$', txt(relative), re.M)
            exists = fragment in {anchor(h) for h in headings}
            if not exists and '(' + link + ')' not in new_sections[path]:
                historical_link_gaps.append({'path': path, 'link': link})
            else:
                check('anchor:' + path + ':' + fragment, exists)
        link_count += 1
    section = new_sections[path]
    check('privacy_patterns:' + path, not re.search(
        r'(?i)((?<![A-Za-z0-9])[A-Z]:[\\/]|gh[pousr]_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|point_\d+)', section))
    for line in section.splitlines():
        if line.startswith('|'):
            check('table_row:' + path + ':' + str(len(checks)), line.endswith('|'))

changed = set(git('diff', '--name-only', BASE).decode().splitlines())
check('tracked_scope', changed <= ALLOWED and {DOS, DEC, STATE} <= changed)
subprocess.run(['git', 'diff', '--check', BASE], check=True)
check('diff_check', True)
print(json.dumps({'base': BASE, 'python': platform.python_version(),
    'platform': platform.platform(), 'dependencies': [], 'seed': None,
    'PASS': len(checks), 'FAIL': 0, 'local_links': link_count,
    'historical_link_gaps': historical_link_gaps,
    'input_sha256': pins, 'dossier_sha256': sha(raw(DOS)),
    'decisions_sha256': sha(raw(DEC)), 'project_state_sha256': sha(raw(STATE)),
    'model_calls': 0, 'private_data_accessed': False, 'TEST_accessed': False,
    'scope': 'TRACKED_METADATA_NOT_ARTIFACT_REPLAY', 'checks': checks}, ensure_ascii=False, indent=2))
```

## Giới hạn kiểm chứng

Lượt thành công: Windows10 build26200 AMD64, CPython3.11.9, stdlib, seed=null;
**215 assertions PASS,0 FAIL**, không phải215 unit tests. Đã kiểm103 local
links và anchors có trong bốn tài liệu thay đổi. Một historical gap:
`docs/PROJECT_STATE.md` trỏ `CANDIDATE160_KAGGLE.md#checklist-bàn-giao-duy-nhất`;
heading đó không còn trong target tại BASE. Link cũ giữ nguyên trong snapshot,
không tính là anchor PASS; các link/anchor mới đều PASS. M1/M2 và năm receipts
nguồn đúng hash, T4/PROJECT_STATE giữ nguyên suffix lịch sử, DECISIONS
append-only, diff chỉ tài liệu và `git diff --check` PASS.

Hashes nội dung được kiểm (SHA256 bytes; không hash archive thật):

| Đối tượng | SHA256 |
| --- | --- |
| T4 dossier có v2 | `c803c8c1932f7327dd83a6019c3dbd065df84cabbad203958adc7c6411758fff` |
| DECISIONS sau append | `fc0f20dbf06f0f2f3e4a581dceb193af08ed9031d503bc591c3fee7cc0e39f2c` |
| PROJECT_STATE | `0964eec8deb748cd4d317c9b5ea102c8f49655672887415c5ece743ee4e22b87` |
| Checker fence UTF-8/LF + một newline cuối | `e6b41beb0d421ba75f2255be209efb52b6195b37d5fb8d47c9e3050b02a22c08` |
| Stdout local `data/processed/issue169/check_final.stdout.json` | `605d5810e26d21586e0fe23d585bb443969d4f5dc1e2d88e40288da83fa5fa66` |

Stdout có môi trường/hash/check names, không per-image data. Bản Markdown này
không tự hash chính nó; commit HEAD/BASE và SHA của receipt nằm ở PR handoff.
Thêm phần kết quả này không đổi checker hoặc ba tài liệu có hashes phía trên.

PASS của checker chứng minh consistency của các nguồn đã pin, không xác minh
archive/member bytes thật, exact ID join3763/160, lịch sử ancestors hoặc quyền
đã ký. Private/local inputs T4/T1 và snapshot source/runtime/checkpoint thật
không đọc lại: **INHERITED/REPORTED/UNKNOWN như dossier**, không checksum PASS
mới. Không kiểm số liệu bằng ảnh/GT; không tạo predictions/score table.
Privacy còn được review diff thủ công; regex không chứng minh mọi dạng secret.
Full unit/native/GPU suite **NOT_RUN**: chỉ tài liệu, không thay runtime/code.
External links không được crawl hàng loạt; GitHub sources liệt kê ở đầu đã
đọc bằng CLI, các link lịch sử khác giữ nguyên và không nhận HTTP PASS mới.
L1–L4/B1–B6 và O2–O6 vẫn chưa được đóng bởi checks này.
