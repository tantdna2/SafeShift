"""PROPOSED diagnostic-only closed JSON language; no official parser change.

All four labels remain possible. Conditioning logits on this language changes
generation semantics; no HNLO or scientific comparability is claimed.
"""
from safeshift.candidates.source import require
from safeshift.pilot.contract import LEVELS,parse_label,digest


class CanonicalJSONGrammar:
    def __init__(self,tokenizer,eos):
        self.texts=['{"safety_level":"'+level+'"}' for level in LEVELS]
        self.paths=[tuple(tokenizer.encode(text,add_special_tokens=False)) for text in self.texts]
        self.eos=tuple(eos if isinstance(eos,list) else [eos])
        require(len(set(self.paths))==4 and all(0<len(p)<64 for p in self.paths),'GRAMMAR_FOUR_DISTINCT_BOUNDED_PATHS')
        require(self.eos and all(type(i) is int and 0<=i<len(tokenizer) for i in self.eos),'GRAMMAR_EOS')
        for text,path in zip(self.texts,self.paths):
            require(all(type(i) is int and 0<=i<len(tokenizer) and i not in self.eos for i in path),'GRAMMAR_CONTENT_TOKEN')
            decoded=tokenizer.decode(list(path),skip_special_tokens=True,clean_up_tokenization_spaces=False)
            require(decoded==text and parse_label(decoded) in LEVELS,'GRAMMAR_EXACT_NATIVE_TOKENIZER_REPLAY')

    def allowed(self,prefix):
        prefix=tuple(prefix)
        next_ids=set()
        for path in self.paths:
            if path[:len(prefix)]!=prefix: continue
            if len(prefix)==len(path): next_ids.update(self.eos)
            else: next_ids.add(path[len(prefix)])
        require(bool(next_ids),'GRAMMAR_PREFIX_OUTSIDE_LANGUAGE')
        return sorted(next_ids)

    def callback(self,input_prefix):
        input_prefix=list(input_prefix)
        def choose(batch_id,ids):
            received=ids.tolist()
            require(batch_id==0 and received[:len(input_prefix)]==input_prefix,'GRAMMAR_EXACT_BATCH_INPUT_PREFIX')
            return self.allowed(received[len(input_prefix):])
        return choose

    def receipt(self):
        return {'id':'issue173-internvl-canonical-json-trie-v1','status':'PROPOSED_NON_EQUIVALENT',
            'language':self.texts,'paths_sha256':digest([list(p) for p in self.paths]),
            'path_lengths':list(map(len,self.paths)),'complete_eos_only':True,
            'all_four_labels_possible':True,'posthoc_cleanup':False,
            'constraint':'PrefixConstrainedLogitsProcessor masks non-language next tokens',
            'hnlo':'NOT_COMPUTED_NOT_COMPARABLE_WITH_FROZEN_GENERATION'}
