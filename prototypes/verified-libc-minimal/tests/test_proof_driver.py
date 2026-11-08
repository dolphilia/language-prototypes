"""Real HOL Light sessions exercise failure cases; no mocked success markers."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from run_proof import run_session


class ProofDriverChecks(unittest.TestCase):
    def test_actual_closed_and_open_theorems(self):
        # Deliberately caught failures do not leak an unchecked theorem into
        # the accepted set. Ordinary HOL hypotheses are not extra axioms.
        body = '''
vp_check_closed `T` TRUTH;;
let reject_check expected theorem =
  let rejected = try vp_check_closed expected theorem; false with Failure _ -> true in
  if not rejected then failwith "VP: bad theorem accepted";;
reject_check `T` (ASSUME `T`);;
reject_check `F` TRUTH;;
'''
        result = run_session('driver-closed', body, ['TRUTH'])
        self.assertEqual(result['theorems'], ['TRUTH'])

    def test_toplevel_exception_even_if_result_was_written(self):
        with self.assertRaises(RuntimeError):
            run_session('driver-exception', 'failwith "VP deliberate proof error";;', [])
        # OCaml may continue and emit a result. The driver must reject anyway.
        self.assertIn('Exception:', (ROOT / 'build/proof-driver-exception.log').read_text())

    def test_missing_theorem_result_is_rejected(self):
        with self.assertRaises(RuntimeError):
            run_session('driver-missing', 'exit 0;;', ['MISSING'])
        self.assertFalse((ROOT / 'build/proof-driver-missing.json').exists())

    def test_missing_theorem_binding_is_rejected(self):
        with self.assertRaises(RuntimeError):
            run_session('driver-unbound', 'vp_check_closed `T` VP_MISSING_THEOREM;;',
                        ['VP_MISSING_THEOREM'])

    def test_additional_axiom_is_rejected(self):
        with self.assertRaises(RuntimeError):
            run_session('driver-axiom', 'let vp_bad = new_axiom `F`;;', [])
        self.assertIn('check_axioms:', (ROOT / 'build/proof-driver-axiom.log').read_text())


if __name__ == '__main__':
    unittest.main()
