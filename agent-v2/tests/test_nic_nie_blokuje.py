"""Style observations stay advisory; factual eligibility is an explicit decision."""
import sys
sys.path.insert(0,'agent-v2')
import gates
for findings in ([], [{'gate':'DLUGOSC','detail':'short'}], [{'gate':'FORMA','detail':'quiet opening'}]):
    status, reason = gates.verdict(findings)
    assert status == 'SAVED', (status, reason)
# Factual rejection and recovery are exercised through real functions in the
# dedicated quality contract, instead of counting assignments in source text.
import unittest
from test_quality_contract import QualityContract
result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(QualityContract))
raise SystemExit(not result.wasSuccessful())
