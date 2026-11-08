"""Actual fresh kernels exercise rejection paths; no mocked proof receipts."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from config import BUILD
from prover import run_session,ProofInfrastructureError


class DriverChecks(unittest.TestCase):
    def test_checked_statement_and_hypotheses(self):
        body='''
let reject expected theorem =
 let rejected = try ve_check "invalid" expected theorem; false with Failure _ -> true in
 if not rejected then failwith "bad theorem accepted";;
reject `T` (ASSUME `T`);;
reject `F` TRUTH;;
reject `x:bool = x` (REFL `x:bool`);;
ve_check "truth" `T` TRUTH;;
'''
        self.assertEqual(run_session('driver-closed',body,['truth'],load_arm=False)['checks'],['truth'])

    def test_exception_after_success_cannot_leave_receipt(self):
        with self.assertRaises(ProofInfrastructureError):
            run_session('driver-exception','ve_check "truth" `T` TRUTH;;\nfailwith "deliberate error";;',['truth'],load_arm=False)
        self.assertFalse((BUILD/'proof-driver-exception.json').exists())

    def test_old_receipt_and_missing_check(self):
        BUILD.mkdir(exist_ok=True)
        (BUILD/'proof-driver-stale.json').write_text('{"checks":["missing"]}')
        with self.assertRaises(ProofInfrastructureError):
            run_session('driver-stale','exit 0;;',['missing'],load_arm=False)
        self.assertFalse((BUILD/'proof-driver-stale.json').exists())

    def test_extra_axiom_is_rejected_in_isolated_kernel(self):
        with self.assertRaises(ProofInfrastructureError):
            run_session('driver-axiom','let forbidden_axiom = new_axiom `F`;;',[],load_arm=False)
        self.assertFalse((BUILD/'proof-driver-axiom.json').exists())

    def test_unbound_theorem_and_missing_file(self):
        with self.assertRaises(ProofInfrastructureError):
            run_session('driver-unbound','ve_check "missing" `T` VE_MISSING_BINDING;;\nloadt "/this-file-does-not-exist.ml";;',['missing'],load_arm=False)
        self.assertFalse((BUILD/'proof-driver-unbound.json').exists())


if __name__=='__main__': unittest.main()
