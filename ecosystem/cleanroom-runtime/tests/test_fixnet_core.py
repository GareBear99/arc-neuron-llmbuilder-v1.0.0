from pathlib import Path

from fixnet.integration import FixNet


def test_novelty_duplicate_detection(tmp_path: Path):
    fx = FixNet(str(tmp_path))
    a, novelty_a = fx.register_fix(
        title='A',
        error_type='x',
        error_signature='sig-1',
        solution='sol-1',
    )
    b, novelty_b = fx.register_fix(
        title='B',
        error_type='x',
        error_signature='sig-1',
        solution='sol-1',
    )
    assert novelty_a['decision'] == 'novel'
    assert novelty_b['decision'] in {'duplicate', 'variant'}


def test_consensus_outcomes(tmp_path: Path):
    fx = FixNet(str(tmp_path))
    fix, _ = fx.register_fix(title='A', error_type='x', error_signature='sig', solution='sol')
    fix_id = fix['fix_id']
    fx.record_outcome(fix_id, succeeded=False)
    fx.record_outcome(fix_id, succeeded=True)
    rec = fx.consensus.get(fix_id)
    assert rec is not None
    assert rec['usage_count'] == 2
