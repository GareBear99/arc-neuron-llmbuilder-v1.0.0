from arc_kernel.budgets import BudgetManager, BudgetPolicy
from arc_kernel.schemas import Capability, Proposal, RiskLevel
from lucifer_runtime.cli import main
from lucifer_runtime.runtime import LuciferRuntime
from arc_kernel.engine import KernelEngine


class DummyState:
    def __init__(self):
        self.proposals = []
        self.policy_decisions = []
        self.executions = []


def test_high_risk_budget_counts_only_high_risk_approvals():
    budgets = BudgetManager(BudgetPolicy(max_high_risk_approvals_per_session=1))
    state = DummyState()
    state.proposals = [
        {"proposal_id": "low-1", "capability": {"risk": "low"}},
        {"proposal_id": "high-1", "capability": {"risk": "high"}},
    ]
    state.policy_decisions = [{"proposal_id": "low-1", "decision": "approve"}]

    high_risk_proposal = Proposal(
        action="delete_file",
        capability=Capability("filesystem.delete", "delete", RiskLevel.HIGH, requires_confirmation=True),
        params={"path": "x.txt"},
        proposed_by="test",
        rationale="test",
    )

    allowed, reason = budgets.assess(high_risk_proposal, state)
    assert allowed is True
    assert reason is None


def test_cli_commands_output(capsys, tmp_path):
    exit_code = main(["--workspace", str(tmp_path), "commands"])
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert 'read <path>' in captured
    assert 'rollback <proposal_id>' in captured


def test_cli_trace_writes_html(tmp_path):
    db_path = tmp_path / 'events.sqlite3'
    kernel = KernelEngine(db_path=db_path)
    runtime = LuciferRuntime(kernel=kernel, workspace_root=tmp_path)
    runtime.handle('write notes.txt :: hello world')
    runtime.kernel.close()

    output = tmp_path / 'trace.html'
    exit_code = main(["--workspace", str(tmp_path), "--db", str(db_path), "trace", "--output", str(output)])
    assert exit_code == 0
    assert output.exists()
    html = output.read_text(encoding='utf-8')
    assert 'ARC Lucifer Trace' in html


def test_cli_persists_state_across_invocations(tmp_path, capsys):
    assert main(["--workspace", str(tmp_path), "write", "notes.txt", "hello world"]) == 0
    capsys.readouterr()

    assert main(["--workspace", str(tmp_path), "read", "notes.txt"]) == 0
    capsys.readouterr()

    assert main(["--workspace", str(tmp_path), "state"]) == 0
    state_output = capsys.readouterr().out
    assert 'write_file' in state_output
    assert 'read_file' in state_output
    assert 'completed_proposals' in state_output
    assert '.arc_lucifer' in str((tmp_path / '.arc_lucifer' / 'events.sqlite3'))


def test_cli_uses_default_workspace_db_for_trace(tmp_path):
    assert main(["--workspace", str(tmp_path), "write", "notes.txt", "hello world"]) == 0
    output = tmp_path / 'trace.html'
    assert main(["--workspace", str(tmp_path), "trace", "--output", str(output)]) == 0
    html = output.read_text(encoding='utf-8')
    assert 'write_file' in html
    assert 'ARC Lucifer Trace' in html


def test_cli_export_import_and_info(tmp_path, capsys):
    assert main(["--workspace", str(tmp_path), "write", "notes.txt", "hello world"]) == 0
    capsys.readouterr()

    export_path = tmp_path / 'events.jsonl'
    assert main(["--workspace", str(tmp_path), "export", "--jsonl", str(export_path)]) == 0
    export_out = capsys.readouterr().out
    assert 'jsonl_path' in export_out
    assert export_path.exists()

    clone = tmp_path / 'clone'
    clone.mkdir()
    assert main(["--workspace", str(clone), "import", "--jsonl", str(export_path)]) == 0
    import_out = capsys.readouterr().out
    assert 'imported_events' in import_out

    assert main(["--workspace", str(clone), "state"]) == 0
    state_out = capsys.readouterr().out
    assert 'write_file' in state_out

    assert main(["--workspace", str(clone), "info"]) == 0
    info_out = capsys.readouterr().out
    assert 'db_stats' in info_out
    assert '.arc_lucifer' in info_out


def test_cli_compact(tmp_path, capsys):
    assert main(["--workspace", str(tmp_path), "write", "notes.txt", "hello world"]) == 0
    capsys.readouterr()
    assert main(["--workspace", str(tmp_path), "compact"]) == 0
    compact_out = capsys.readouterr().out
    assert 'before' in compact_out
    assert 'after' in compact_out
