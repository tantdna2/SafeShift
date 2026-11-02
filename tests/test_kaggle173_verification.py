"""Tiny synthetic checkpoint bytes only; never model weights or dataset fixtures."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch, Mock

from safeshift.fulltrain import verification173 as v
from safeshift.candidates.fulltrain_run import synthetic_cohort
from safeshift.candidates.fulltrain import validate_cohort
from safeshift.pilot.contract import digest
from safeshift.pilot.artifacts import write, sha


class ByteVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.weight=self.root/'tiny.safetensors'
        self.index=self.root/'model.safetensors.index.json'
        self.header={'x':{'dtype':'F16','shape':[2],'data_offsets':[0,4]}}
        self.put(self.header)
        write(self.index,{'metadata':{'total_size':4},'weight_map':{'x':self.weight.name}})

    def put(self,header,body=b'\x00'*4):
        data=json.dumps(header).encode()
        self.weight.write_bytes(struct.pack('<Q',len(data))+data+body)

    def spec(self):
        return {'model':{'id':'SYNTHETIC','revision':'a'*40},'index':self.index.name,'tensor_count':1,
            'files':{p.name:{'size':p.stat().st_size,'sha256':sha(p)} for p in (self.weight,self.index)}}

    def test_complete_stream_hash_header_and_index_without_model(self):
        spec=self.spec()
        with patch.dict('sys.modules',{'torch':None,'transformers':None,'safetensors':None}):
            result=v.verify_files(self.root,spec)
        self.assertEqual(result['status'],'CHECKPOINT_BYTES_AND_HEADERS_PASS')
        self.assertEqual(result['headers'][self.weight.name]['tensor_bytes'],4)
        self.assertFalse(result['weights_loaded']); self.assertEqual(result['model_calls'],0)

    def test_same_size_changed_shard_rejected(self):
        spec=self.spec(); data=self.weight.read_bytes(); self.weight.write_bytes(data[:-1]+b'X')
        with self.assertRaisesRegex(ValueError,'CHECKPOINT_SHA256'): v.verify_files(self.root,spec)

    def test_truncated_shard_rejected_before_hash(self):
        spec=self.spec(); self.weight.write_bytes(b'partial')
        with self.assertRaisesRegex(ValueError,'CHECKPOINT_SIZE'): v.verify_files(self.root,spec)

    def test_index_wrong_shard_rejected(self):
        self.index.write_text(json.dumps({'metadata':{'total_size':4},'weight_map':{'x':'wrong.safetensors'}}))
        with self.assertRaisesRegex(ValueError,'CHECKPOINT_INDEX_SHARDS'): v.verify_files(self.root,self.spec())

    def test_duplicate_json_index_keys_rejected(self):
        self.index.write_bytes(b'{"weight_map":{},"weight_map":{}}')
        with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'): v.verify_files(self.root,self.spec())

    def test_tensor_not_in_index_rejected(self):
        with self.assertRaisesRegex(ValueError,'INDEX_MEMBERSHIP'): v.safetensors_header(self.weight,{'other'})

    def test_huge_header_rejected_without_allocation(self):
        self.weight.write_bytes(struct.pack('<Q',2**60))
        with self.assertRaisesRegex(ValueError,'HEADER_BOUND'): v.safetensors_header(self.weight,{'x'})

    def test_shape_offset_and_trailing_bytes_rejected(self):
        for shape,offsets,body in [([3],[0,4],b'1234'),([2],[1,5],b'12345'),([2],[0,4],b'12345')]:
            with self.subTest(shape=shape,offsets=offsets,body=body):
                self.put({'x':{'dtype':'F16','shape':shape,'data_offsets':offsets}},body)
                with self.assertRaises(ValueError): v.safetensors_header(self.weight,{'x'})

    def test_duplicate_header_keys_rejected(self):
        raw=b'{"x":{},"x":{}}'; self.weight.write_bytes(struct.pack('<Q',len(raw))+raw)
        with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'): v.safetensors_header(self.weight,{'x'})

    def test_inventory_extra_partial_rejected(self):
        spec=self.spec(); (self.root/'extra.part').write_bytes(b'')
        with self.assertRaisesRegex(ValueError,'EXACT_INVENTORY'): v.verify_files(self.root,spec)

    def test_combined_download_temporary_and_reserve_budget(self):
        v.storage_budget(100,60,temporary_bytes=30,reserve_bytes=10)
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_DISK'): v.storage_budget(99,60,temporary_bytes=30,reserve_bytes=10)
        qwen=v.checkpoint_spec('qwen3')
        total=sum(r['size'] for r in qwen['files'].values())
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_DISK'):
            v.storage_budget(int(19.5*2**30),total,temporary_bytes=4209365519)

    def test_byte_receipt_cannot_dispatch_or_unlock_production(self):
        with self.assertRaisesRegex(ValueError,'SMOKE_NOT_IMPLEMENTED_OR_AUTHORIZED'):
            v.dispatch_smoke(approved=True,weights_verified=True)
        from safeshift.fulltrain import contract
        with self.assertRaises(PermissionError): contract.authorize({'approved':True})

    def test_master_hash_checked_before_schema_or_paths(self):
        master=self.root/'master.json'; master.write_bytes(b'not JSON')
        with self.assertRaisesRegex(ValueError,'ORIGINAL_MASTER_CHECKSUM'): v.verify_train(master,self.root)

    def test_duplicate_plan_id_rejected(self):
        c=synthetic_cohort(); c['samples'][1]['sample_id']=c['samples'][0]['sample_id']
        with self.assertRaisesRegex(ValueError,'DUPLICATE_SAMPLE_ID'): validate_cohort(c,digest(c))

    def test_original_locator_hash_order_missing_image_and_no_sidecars(self):
        master=self.root/'master.json'
        originals=[{'image_locator':'DATA_PATH/train/Annotations/a.jpg'},
                   {'image_locator':'DATA_PATH/train/Annotations/b.jpg'}]
        master.write_text(json.dumps({'samples':originals}))
        rows=[{'ordinal':i,'sample_id':str(i),'image_sha256':hashlib.sha256(bytes([i])).hexdigest()} for i in range(2)]
        projection={'samples':rows}
        image=self.root/'train/Annotations/a.jpg'; image.parent.mkdir(parents=True); image.write_bytes(b'\x00')
        with patch.object(v,'cohort',return_value=projection),patch.object(v,'validate_cohort',return_value=rows):
            with self.assertRaisesRegex(ValueError,'MISSING_1_CHANGED_0'): v.verify_train(master,self.root)
            image.with_name('b.jpg').write_bytes(b'\x01')
            image.with_suffix('.json').write_bytes(b'THIS SIDECAR MUST NEVER BE READ')
            result,p,mapping=v.verify_train(master,self.root)
            self.assertEqual(result['verified_images'],2)
            self.assertEqual([r['ordinal'] for r in mapping],[0,1]); self.assertEqual(p,projection)


if __name__=='__main__': unittest.main()
