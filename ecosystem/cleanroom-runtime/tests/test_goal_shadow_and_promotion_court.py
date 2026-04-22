from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime
from cognition_services.goal_engine import GoalEngine
from lucifer_runtime.cli import main


def test_goal_compiler_adds_constraints_for_release():
    engine = GoalEngine()
    goal = engine.compile_goal('release production runtime with archive sync', priority=90)
    assert 'require promotion evidence bundle' in goal.constraints
    assert goal.archive_mode == 'early_mirror_then_retire'
    assert 'archive lineage metadata' in goal.evidence_requirements


def test_shadow_handle_records_prediction_vs_actual(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / 'events.db'), workspace_root=tmp_path)
    result = runtime.shadow_handle('list the current files', predicted_status='approve')
    assert result['status'] == 'ok'
    assert result['comparison']['actual_status'] == 'approve'
    assert result['comparison']['status_match'] is True


def test_promotion_review_requires_validation(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / 'events.db'), workspace_root=tmp_path)
    plan = runtime.plan_improvements()
    run_id = runtime.scaffold_improvement_run(plan['tasks'][0]['key'])['run']['run_id']
    review = runtime.review_improvement_run(run_id)
    assert review['status'] == 'error'
    assert review['reason'] == 'missing_validation'


def test_goal_and_shadow_cli_commands(tmp_path: Path, capsys):
    assert main(['--workspace', str(tmp_path), 'goal', 'release the runtime safely']) == 0
    out = capsys.readouterr().out
    assert 'archive_mode' in out
    assert main(['--workspace', str(tmp_path), 'shadow', 'list the current files']) == 0
    out = capsys.readouterr().out
    assert 'comparison' in out
