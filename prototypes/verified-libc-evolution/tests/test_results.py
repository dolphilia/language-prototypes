import sys
import json
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from results import Result,admissible,validate_concrete_input


class ResultChecks(unittest.TestCase):
    def test_saved_evidence_can_be_audited_without_type_changes(self):
        result=Result('x','copy','proved','hol_closed_theorem','checked',
                      ('receipt.json','copy:public'),'0'*64)
        registry={'contracts':[result.as_json()]}
        self.assertEqual(json.loads(json.dumps(registry)),registry)

    def test_unknown_is_neither_proof_nor_counterexample(self):
        r=Result('research','copy','unknown','unsupported','instruction not yet supported')
        self.assertFalse(admissible([r],['copy']))
        with self.assertRaises(ValueError):
            Result('x','copy','counterexample','unfinished_proof','tactic failed',('log',))

    def test_partial_contracts_and_infrastructure(self):
        r=Result('x','copy','proved','hol_closed_theorem','checked',('receipt',),'0'*64)
        self.assertFalse(admissible([r],['copy','access']))
        e=Result('x','access','infrastructure_error','missing_input','object absent')
        with self.assertRaises(RuntimeError): admissible([r,e],['copy','access'])

    def test_cannot_combine_different_code_identities(self):
        a=Result('x','copy','proved','hol_closed_theorem','checked',('receipt',),'0'*64)
        b=Result('x','access','proved','hol_closed_theorem','checked',('receipt',),'1'*64)
        with self.assertRaises(ValueError): admissible([a,b],['copy','access'])

    def test_contract_outside_is_not_a_counterexample(self):
        good=dict(pc=4096,code_size=32,dst=8192,src=12288,n=1)
        self.assertTrue(validate_concrete_input(**good))
        for change in [dict(dst=0),dict(src=8192),dict(n=2**64),dict(src=2**64-1,n=2),dict(dst=4096)]:
            with self.assertRaises(ValueError): validate_concrete_input(**(good|change))


if __name__=='__main__': unittest.main()
