"""Command-line entrypoint for the ARC Lucifer runtime and operational tooling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from dashboards.trace_viewer import render_trace

from .cli_handlers import (
    _compact_command,
    _config_command,
    _configure_model_runtime,
    _doctor,
    _export_command,
    _import_command,
    _info_command,
    _memory_command,
    _model_command,
    _print_json,
    _prompt_should_use_model,
    _train_command,
    runtime_from_args,
)
from .runtime import LuciferRuntime
from .cli_parser import build_parser
from robotics_bridge import RoboticsGateway
from robotics_mapping import MappingGateway
from spatial_truth import SpatialTruthEngine
from geo_overlay import GeoOverlayGateway
from bluetooth_bridge import BluetoothGateway


def _run_prompt(runtime: LuciferRuntime, args) -> int:
    if not _prompt_should_use_model(args):
        return _print_json(runtime.handle(args.text, confirm=args.confirm))

    _configure_model_runtime(runtime, args)
    context = {'system': args.system or ''}
    options: dict[str, object] = {}
    if args.temperature is not None:
        options['temperature'] = args.temperature
    if args.max_tokens is not None:
        options['max_tokens'] = args.max_tokens

    def on_chunk(payload: dict[str, object]) -> None:
        if payload.get('text'):
            print(payload['text'], end='', flush=True)

    result = runtime.prompt_model(
        args.text,
        context=context,
        options=options,
        stream=args.stream and not args.json_output,
        on_chunk=on_chunk if args.stream and not args.json_output else None,
    )
    if args.stream and not args.json_output:
        print()
    return _print_json(result)


COMMAND_LIST = [
    'read <path>',
    'write <path> <content>',
    'delete <path> [--confirm]',
    'shell <allowlisted command>',
    'prompt <text> [--stream] [--binary-path ...] [--model-path ...]',
    'approve <proposal_id>',
    'reject <proposal_id> [--reason ...]',
    'rollback <proposal_id>',
    'trace [--output trace.html]',
    'export [--jsonl path] [--sqlite-backup path]',
    'import --jsonl path',
    'compact',
    'info',
    'monitor [--watch seconds --iterations N]',
    'failures',
    'doctor [--json-output]',
    'config show|init',
    'model backends|profiles|show-profile|register-profile|activate-profile|compare-profiles',
    'train export-supervised|export-preferences',
    'state',
    'commands',
    'bench',
    'code index|verify|plan|replace-range|replace-symbol',
    'self-improve analyze|plan|scaffold|validate-run|promote|apply-patch|generate-candidates|score-candidates|best-candidate|execute-best|inject-fault|adversarial-cycle|execute-cycle|review-run',
    'goal <text> [--priority N]',
    'shadow <text> [--predicted-status ...] [--confirm]',
    'memory status|archive-now|sync|search',
    'fixnet register|embed|stats|sync-archive',
    'trust record|stats',
    'curriculum record|stats',
    'directive add|complete|stats',
    'continuity boot|heartbeat|status',
    'robot describe|state-template|safety-check|perform',
    'mapping describe|state-template|coverage|ingest-update|plan-route',
    'spatial describe|state-template|ingest-observation|ingest-bt-signal|upsert-anchor|summarize',
    'bt describe|device-template|trusted-list|register-device|inspect-device|signal-summary|signal-observation|policy-check|perform',
    'geo describe|anchor-template|register-anchor|nearest-anchor|tile-summary',
]


def _parse_csv_items(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(',') if item.strip()]


def _handle_basic_command(runtime, parser, args) -> int | None:
    if args.command == 'read':
        return _print_json(runtime.handle(f'read {args.path}'))
    if args.command == 'write':
        return _print_json(runtime.handle(f'write {args.path} :: {args.content}', confirm=args.confirm))
    if args.command == 'delete':
        return _print_json(runtime.handle(f'delete {args.path}', confirm=args.confirm))
    if args.command == 'shell':
        command_text = ' '.join(args.command_text).strip()
        if not command_text:
            parser.error('shell command requires command_text')
        return _print_json(runtime.handle(f'shell {command_text}'))
    if args.command == 'prompt':
        return _run_prompt(runtime, args)
    if args.command == 'approve':
        return _print_json(runtime.approve(args.proposal_id))
    if args.command == 'reject':
        return _print_json(runtime.reject(args.proposal_id, reason=args.reason))
    if args.command == 'rollback':
        return _print_json(runtime.rollback(args.proposal_id))
    return None


def _handle_ops_command(runtime, args) -> int | None:
    if args.command == 'trace':
        output = Path(args.output)
        render_trace(runtime.kernel, output)
        return _print_json({'status': 'ok', 'trace_path': str(output.resolve())})
    if args.command == 'export':
        return _print_json(_export_command(runtime, args))
    if args.command == 'import':
        return _print_json(_import_command(runtime, args))
    if args.command == 'compact':
        return _print_json(_compact_command(runtime))
    if args.command == 'info':
        return _print_json(_info_command(runtime, args))
    if args.command == 'doctor':
        return _print_json(_doctor(runtime, args))
    if args.command == 'config':
        return _print_json(_config_command(args))
    if args.command == 'model':
        return _model_command(runtime, args)
    if args.command == 'train':
        return _train_command(runtime, args)
    if args.command == 'state':
        return _print_json({'status': 'ok', 'state': runtime.kernel.state().__dict__})
    if args.command == 'commands':
        return _print_json({'status': 'ok', 'commands': COMMAND_LIST})
    if args.command == 'failures':
        state = runtime.kernel.state()
        return _print_json({'status': 'ok', 'failures': state.fallback_events, 'count': len(state.fallback_events)})
    if args.command == 'bench':
        return _print_json(runtime.run_benchmarks())
    if args.command == 'memory':
        return _memory_command(runtime, args)
    robotics = _handle_robotics_stack_command(args)
    if robotics is not None:
        return robotics
    return None


def _handle_code_command(runtime, args) -> int:
    handlers: dict[str, Callable[[], dict]] = {
        'index': lambda: runtime.code_index(args.path),
        'verify': lambda: runtime.code_verify(args.path),
        'plan': lambda: runtime.code_plan(args.path, args.instruction, symbol_name=args.symbol),
        'replace-range': lambda: runtime.code_replace_range(args.path, args.start_line, args.end_line, args.replacement_text, confirm=args.confirm, expected_hash=args.expected_hash, reason=args.reason),
        'replace-symbol': lambda: runtime.code_replace_symbol(args.path, args.symbol_name, args.replacement_text, confirm=args.confirm, expected_hash=args.expected_hash, reason=args.reason),
    }
    return _print_json(handlers[args.code_command]())


def _handle_directive_command(runtime, args) -> int:
    if args.directive_command == 'add':
        return _print_json(runtime.register_directive(
            title=args.title,
            instruction=args.instruction,
            priority=args.priority,
            scope=args.scope,
            constraints=_parse_csv_items(args.constraints),
            success_conditions=_parse_csv_items(args.success_conditions),
            abort_conditions=_parse_csv_items(args.abort_conditions),
            persistence_mode=args.persistence_mode,
            issuer=args.issuer,
            supersedes=args.supersedes,
        ))
    if args.directive_command == 'complete':
        return _print_json(runtime.complete_directive(args.directive_id, status=args.status))
    if args.directive_command == 'stats':
        return _print_json(runtime.directive_stats())
    return _print_json({'status': 'error', 'reason': f'unknown directive command: {args.directive_command}'})


def _handle_continuity_command(runtime, args) -> int:
    if args.continuity_command == 'boot':
        return _print_json(runtime.boot_continuity(fallback_available=args.fallback_available, notes=args.notes))
    if args.continuity_command == 'heartbeat':
        return _print_json(runtime.continuity_heartbeat(mode=args.mode, notes=args.notes))
    if args.continuity_command == 'status':
        return _print_json(runtime.continuity_status())
    return _print_json({'status': 'error', 'reason': f'unknown continuity command: {args.continuity_command}'})


def _handle_fixnet_command(runtime, args) -> int:
    if args.fixnet_command == 'register':
        return _print_json(runtime.fixnet_register(
            title=args.title,
            error_type=args.error_type,
            error_signature=args.error_signature,
            solution=args.solution,
            summary=args.summary,
            keywords=_parse_csv_items(args.keywords),
            context=json.loads(args.context_json),
            evidence=json.loads(args.evidence_json),
            linked_event_ids=args.linked_event_id,
            linked_run_ids=args.linked_run_id,
            linked_proposal_ids=args.linked_proposal_id,
            auto_embed=args.auto_embed,
            archive_branch_id=args.archive_branch_id,
        ))
    if args.fixnet_command == 'embed':
        return _print_json(runtime.fixnet_embed(args.fix_id, archive_branch_id=args.archive_branch_id))
    if args.fixnet_command == 'stats':
        return _print_json(runtime.fixnet_stats())
    if args.fixnet_command == 'sync-archive':
        return _print_json(runtime.fixnet_sync_archive(args.fix_id, status=args.status, retirement_at=args.retirement_at))
    return _print_json({'status': 'error', 'reason': f'unknown fixnet command: {args.fixnet_command}'})



def _handle_robotics_stack_command(args) -> int | None:
    if args.command == 'robot':
        gateway = RoboticsGateway()
        if args.robot_command == 'describe':
            return _print_json(gateway.describe())
        if args.robot_command == 'state-template':
            return _print_json(gateway.state_template())
        if args.robot_command == 'safety-check':
            return _print_json(gateway.safety_check(json.loads(args.state_json), action=args.action, subsystem=args.subsystem, params=json.loads(args.params_json)))
        if args.robot_command == 'perform':
            return _print_json(gateway.perform(json.loads(args.state_json), action=args.action, subsystem=args.subsystem, params=json.loads(args.params_json)))
    if args.command == 'mapping':
        gateway = MappingGateway()
        if args.mapping_command == 'describe':
            return _print_json(gateway.describe())
        if args.mapping_command == 'state-template':
            return _print_json(gateway.state_template())
        if args.mapping_command == 'coverage':
            return _print_json(gateway.coverage(json.loads(args.state_json)))
        if args.mapping_command == 'ingest-update':
            robot_position = json.loads(args.robot_position_json) if args.robot_position_json else None
            return _print_json(gateway.ingest_update(json.loads(args.state_json), json.loads(args.updates_json), robot_position=robot_position))
        if args.mapping_command == 'plan-route':
            return _print_json(gateway.plan_route(json.loads(args.state_json), json.loads(args.goal_json)))
    if args.command == 'spatial':
        engine = SpatialTruthEngine()
        if args.spatial_command == 'describe':
            return _print_json(engine.describe())
        if args.spatial_command == 'state-template':
            return _print_json(engine.state_template())
        if args.spatial_command == 'ingest-observation':
            return _print_json(engine.ingest_observation(json.loads(args.state_json), json.loads(args.observation_json)))
        if args.spatial_command == 'ingest-bt-signal':
            return _print_json(engine.ingest_bluetooth_signal(json.loads(args.state_json), json.loads(args.signal_json)))
        if args.spatial_command == 'upsert-anchor':
            return _print_json(engine.upsert_anchor(json.loads(args.state_json), json.loads(args.anchor_json)))
        if args.spatial_command == 'summarize':
            return _print_json(engine.summarize(json.loads(args.state_json)))
    if args.command == 'bt':
        gateway = BluetoothGateway()
        if args.bt_command == 'describe':
            return _print_json(gateway.describe())
        if args.bt_command == 'device-template':
            return _print_json(gateway.device_template())
        if args.bt_command == 'trusted-list':
            return _print_json(gateway.trusted_list(json.loads(args.devices_json)))
        if args.bt_command == 'register-device':
            return _print_json(gateway.register_device(json.loads(args.devices_json), json.loads(args.device_json)))
        if args.bt_command == 'inspect-device':
            return _print_json(gateway.inspect_device(json.loads(args.devices_json), args.device_id))
        if args.bt_command == 'signal-summary':
            return _print_json(gateway.signal_summary(json.loads(args.devices_json)))
        if args.bt_command == 'signal-observation':
            return _print_json(gateway.signal_observation(json.loads(args.devices_json), args.device_id))
        if args.bt_command == 'policy-check':
            return _print_json(gateway.policy_check(json.loads(args.devices_json), action=args.action, device_id=args.device_id, profile=args.profile, params=json.loads(args.params_json), operator_approved=args.operator_approved))
        if args.bt_command == 'perform':
            return _print_json(gateway.perform(json.loads(args.devices_json), action=args.action, device_id=args.device_id, profile=args.profile, params=json.loads(args.params_json), operator_approved=args.operator_approved))
    if args.command == 'geo':
        gateway = GeoOverlayGateway()
        if args.geo_command == 'describe':
            return _print_json(gateway.describe())
        if args.geo_command == 'anchor-template':
            return _print_json(gateway.anchor_template())
        if args.geo_command == 'register-anchor':
            return _print_json(gateway.register_anchor(json.loads(args.anchors_json), json.loads(args.anchor_json)))
        if args.geo_command == 'nearest-anchor':
            return _print_json(gateway.nearest_anchor(json.loads(args.anchors_json), args.lat, args.lon))
        if args.geo_command == 'tile-summary':
            return _print_json(gateway.tile_summary(json.loads(args.anchors_json), zoom=args.zoom))
    return None


def _handle_meta_command(runtime, args) -> int:
    if args.command == 'goal':
        return _print_json(runtime.compile_goal(args.text, priority=args.priority))
    if args.command == 'shadow':
        return _print_json(runtime.shadow_handle(args.text, predicted_status=args.predicted_status, confirm=args.confirm))
    if args.command == 'trust':
        if args.trust_command == 'record':
            return _print_json(runtime.record_tool_outcome(args.tool_name, succeeded=args.status == 'success', notes=args.notes, evidence=json.loads(args.evidence_json)))
        if args.trust_command == 'stats':
            return _print_json(runtime.tool_trust_stats())
    if args.command == 'curriculum':
        if args.curriculum_command == 'record':
            return _print_json(runtime.record_curriculum(theme=args.theme, skill=args.skill, failure_cluster=args.failure_cluster, outcome=args.outcome, notes=args.notes))
        if args.curriculum_command == 'stats':
            return _print_json(runtime.curriculum_stats())
    if args.command == 'code':
        return _handle_code_command(runtime, args)
    if args.command == 'directive':
        return _handle_directive_command(runtime, args)
    if args.command == 'continuity':
        return _handle_continuity_command(runtime, args)
    if args.command == 'fixnet':
        return _handle_fixnet_command(runtime, args)
    raise ValueError(f'Unsupported meta command: {args.command}')


def _handle_self_improve_command(runtime, args) -> int:
    handlers: dict[str, Callable[[], dict]] = {
        'analyze': lambda: runtime.analyze_improvements(),
        'plan': lambda: runtime.plan_improvements(target_key=args.target_key),
        'scaffold': lambda: runtime.scaffold_improvement_run(target_key=args.target_key),
        'validate-run': lambda: runtime.validate_improvement_run(args.run_id, timeout=args.timeout),
        'promote': lambda: runtime.promote_improvement_run(args.run_id, force=args.force),
        'apply-patch': lambda: runtime.apply_improvement_patch(
            args.run_id, path=args.path, replacement_text=args.replacement, symbol_name=args.symbol,
            start_line=args.start_line, end_line=args.end_line, expected_hash=args.expected_hash,
            rationale=args.reason, validation_requested=args.validate,
        ),
        'generate-candidates': lambda: runtime.generate_improvement_candidates(
            args.run_id, path=args.path, replacement_text=args.replacement, symbol_name=args.symbol,
            start_line=args.start_line, end_line=args.end_line, expected_hash=args.expected_hash,
            rationale=args.reason,
        ),
        'score-candidates': lambda: runtime.score_improvement_candidates(args.run_id, timeout=args.timeout),
        'best-candidate': lambda: runtime.choose_best_improvement_candidate(args.run_id),
        'execute-best': lambda: runtime.execute_best_improvement_candidate(
            args.run_id, timeout=args.timeout, promote=args.promote,
            force_promote=args.force_promote, quarantine_on_failure=not args.no_quarantine,
        ),
        'inject-fault': lambda: runtime.inject_improvement_fault(args.run_id, kind=args.kind, path=args.path, note=args.note),
        'adversarial-cycle': lambda: runtime.run_improvement_adversarial_cycle(
            args.run_id, kind=args.kind, path=args.path, replacement_text=args.replacement,
            symbol_name=args.symbol, start_line=args.start_line, end_line=args.end_line,
            expected_hash=args.expected_hash, rationale=args.reason, timeout=args.timeout,
        ),
        'execute-cycle': lambda: runtime.execute_improvement_cycle(
            args.run_id, path=args.path, replacement_text=args.replacement, symbol_name=args.symbol,
            start_line=args.start_line, end_line=args.end_line, expected_hash=args.expected_hash,
            rationale=args.reason, validate=not args.no_validate, timeout=args.timeout,
            promote=args.promote, force_promote=args.force_promote,
            quarantine_on_failure=not args.no_quarantine,
        ),
        'review-run': lambda: runtime.review_improvement_run(args.run_id),
    }
    return _print_json(handlers[args.self_command]())


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime = runtime_from_args(args)
    try:
        for handler in (_handle_basic_command, _handle_ops_command):
            result = handler(runtime, parser, args) if handler is _handle_basic_command else handler(runtime, args)
            if result is not None:
                return result
        if args.command == 'monitor':
            from .cli_handlers import _monitor_command
            return _monitor_command(runtime, args)
        if args.command == 'self-improve':
            return _handle_self_improve_command(runtime, args)
        return _handle_meta_command(runtime, args)
    finally:
        runtime.kernel.close()


if __name__ == '__main__':
    raise SystemExit(main())
