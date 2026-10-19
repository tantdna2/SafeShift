"""CPU-only bounded original TRAIN input admission, after grant and consumption."""
import errno
import os
from pathlib import Path
import shutil
import time

from safeshift.pa3.native.journal import Journal, no_alias
from ..one_click.artifacts import sha256, write
from ..resource_pilot.orchestrate import (TrainInputError, discover_train, train_image,
                                         error_report as _pilot_error_report, TRAIN_LAYOUTS, MAX_DISCOVERY_ENTRIES)
from .cohort import opaque_rows, validate_opaque


def error_report(error, phase):
    report = _pilot_error_report(error, phase)
    report.setdefault("reason", str(error)[:512] or type(error).__name__)
    return report


def check_images(dataset, rows):
    validate_opaque(opaque_rows(rows), len(rows))
    if len({r['image_locator'] for r in rows}) != len(rows):
        raise TrainInputError('DISTINCT_SHARD_IMAGES_REQUIRED')
    metadata = []
    for i, row in enumerate(rows):
        try:
            source = train_image(dataset, row)
            size = source.stat().st_size
            if size <= 0:
                raise TrainInputError('TRAIN_IMAGE_EMPTY', image_locator=row['image_locator'])
            metadata.append({'ordinal': i, 'size_bytes': size, 'image_sha256': row['image_sha256']})
        except OSError as error:
            raise TrainInputError('TRAIN_IMAGE_METADATA_UNREADABLE', ordinal=i,
                image_locator=row['image_locator'], metadata_errno=error.errno) from error
        except TrainInputError as error:
            error.details['ordinal'] = i
            raise
    return metadata


def stage_images(dataset, rows, dest, receipt_root):
    dest = no_alias(dest)
    dest.mkdir(parents=True, exist_ok=False)
    journal, i = Journal(receipt_root, create=True), None
    try:
        for i, row in enumerate(rows):
            start = time.monotonic()
            journal.write(f'image-{i:06d}.read-start', {'ordinal': i,
                'exposure': 'SUPERVISOR_IMAGE_READ_STARTED', 'image_sha256': row['image_sha256']})
            try:
                source = train_image(dataset, row)
                size, actual = source.stat().st_size, sha256(source)
                journal.write(f'image-{i:06d}.hash', {'ordinal': i, 'size_bytes': size,
                    'expected_sha256': row['image_sha256'], 'actual_sha256': actual})
                if actual != row['image_sha256']:
                    raise TrainInputError('TRAIN_IMAGE_HASH_MISMATCH_NO_SKIP', ordinal=i,
                        image_locator=row['image_locator'], expected_sha256=row['image_sha256'], actual_sha256=actual)
                target = dest / f'{i:06d}.image'
                with source.open('rb') as reader, target.open('xb') as writer:
                    shutil.copyfileobj(reader, writer)
                    writer.flush()
                    os.fsync(writer.fileno())
                # Recheck both metadata and bytes after copying, before worker access.
                train_image(dataset, row)
                copied, copied_size = sha256(target), target.stat().st_size
                journal.write(f'image-{i:06d}.copy', {'ordinal': i, 'size_bytes': copied_size,
                    'expected_sha256': row['image_sha256'], 'actual_sha256': copied})
                if copied != row['image_sha256'] or copied_size != size:
                    raise TrainInputError('STAGED_COPY_HASH_OR_SIZE_MISMATCH', ordinal=i,
                        image_locator=row['image_locator'], expected_sha256=row['image_sha256'],
                        actual_sha256=copied, expected_size_bytes=size, actual_size_bytes=copied_size)
            except OSError as error:
                reason = 'TRAIN_STAGING_NO_SPACE' if error.errno == errno.ENOSPC else 'TRAIN_STAGING_COPY_OR_READ_FAILED'
                raise TrainInputError(reason, ordinal=i, image_locator=row['image_locator'],
                    io_errno=error.errno) from error
            finally:
                journal.write(f'image-{i:06d}.timing', {'ordinal': i, 'seconds': time.monotonic() - start})
        write(dest / 'request.json', opaque_rows(rows))
        journal.write('finish', {'count': len(rows)})
    except BaseException as error:
        journal.write('failure', {'ordinal': i, 'type': type(error).__name__,
            'error': error_report(error, 'image_staging')})
        raise
    finally:
        journal.seal()
