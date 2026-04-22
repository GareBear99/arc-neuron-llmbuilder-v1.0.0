"""Shared handler helpers for the ARC Lucifer CLI."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from pathlib import Path
import sys
from typing import Any

from arc_kernel.engine import KernelEngine
from dashboards.monitor import render_monitor_panel
from memory_subsystem import MemoryManager, RetentionConfig
from model_services import ModelProfileStore
from self_improve import TrainingCorpusExporter

from .config import CONFIG_ENV, default_config_path, default_runtime_dir, load_config, merge_settings, save_config
from .runtime import LuciferRuntime

def resolve_config_path(args: argparse.Namespace) -> Path:
    explicit = args.config or os.getenv(CONFIG_ENV)
    if explicit:
        return Path(explicit).expanduser().resolve()
    return default_config_path(args.workspace)


def load_runtime_config(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    config_path = resolve_config_path(args)
    return config_path, load_config(config_path)


def default_db_path(workspace: str | Path) -> Path:
    runtime_dir = default_runtime_dir(workspace)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / 'events.sqlite3'


def effective_settings(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    cli = {
        'workspace': args.workspace,
        'db': args.db,
    }
    return merge_settings(config, cli)


def runtime_from_args(args: argparse.Namespace) -> LuciferRuntime:
    _config_path, config = load_runtime_config(args)
    settings = effective_settings(args, config)
    db_raw = settings.get('db')
    db_path = Path(db_raw).expanduser().resolve() if db_raw else default_db_path(settings.get('workspace', args.workspace))
    kernel = KernelEngine(db_path=db_path)
    return LuciferRuntime(kernel=kernel, workspace_root=settings.get('workspace', args.workspace))




def _repo_root_from_workspace(workspace: str | Path) -> Path:
    workspace_path = Path(workspace).expanduser().resolve()
    for candidate in [workspace_path, *workspace_path.parents]:
        if (candidate / 'pyproject.toml').exists() and (candidate / 'README.md').exists() and (candidate / 'src').exists():
            return candidate
    return workspace_path


def _release_gate_checks(repo_root: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str, level: str = 'error') -> None:
        checks.append({'name': name, 'ok': ok, 'detail': detail, 'level': level})

    pyproject = repo_root / 'pyproject.toml'
    readme = repo_root / 'README.md'
    docs_prod = repo_root / 'docs' / 'production_readiness.md'
    scripts_dir = repo_root / 'scripts'
    workflow_ci = repo_root / '.github' / 'workflows' / 'ci.yml'
    workflow_release = repo_root / '.github' / 'workflows' / 'release-gate.yml'

    add('repo_root_detected', pyproject.exists(), f'repo_root={repo_root}')
    add('readme_present', readme.exists(), f'readme={readme}')
    add('production_docs_present', docs_prod.exists(), f'production_docs={docs_prod}', level='warn')
    add('smoke_script_present', (scripts_dir / 'smoke.sh').exists(), f'smoke={scripts_dir / "smoke.sh"}')
    add('release_check_present', (scripts_dir / 'release_check.sh').exists(), f'release_check={scripts_dir / "release_check.sh"}')
    add('version_audit_present', (scripts_dir / 'version_audit.py').exists(), f'version_audit={scripts_dir / "version_audit.py"}')
    add('ci_workflow_present', workflow_ci.exists(), f'ci_workflow={workflow_ci}', level='warn')
    add('release_workflow_present', workflow_release.exists(), f'release_workflow={workflow_release}', level='warn')

    if pyproject.exists():
        add('pyproject_has_project_name', 'name = ' in pyproject.read_text(encoding='utf-8'), f'pyproject={pyproject}')

    return checks

def _print_json(data: dict[str, Any]) -> int:
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0 if data.get('status') not in {'denied', 'error', 'not_found', 'not_pending'} else 1


def _env_or_default(cli_value: Any, env_name: str, default: Any = None) -> Any:
    if cli_value is not None:
        return cli_value
    return os.getenv(env_name, default)


def _model_settings_from_args(args: argparse.Namespace) -> dict[str, Any]:
    config_path, config = load_runtime_config(args)
    model_config = dict(config.get('model', {}))
    active_profile = ModelProfileStore(default_runtime_dir(args.workspace)).active_profile() or {}
    profile_settings = {
        'binary_path': active_profile.get('binary_path'),
        'model_path': active_profile.get('model_path'),
        'model_name': active_profile.get('name'),
        'endpoint': active_profile.get('endpoint'),
        'backend_type': active_profile.get('backend_type'),
    }
    return merge_settings(model_config, profile_settings, {
        'binary_path': getattr(args, 'binary_path', None),
        'model_path': getattr(args, 'model_path', None),
        'model_name': getattr(args, 'model_name', None),
        'host': getattr(args, 'host', None),
        'port': getattr(args, 'port', None),
        'startup_timeout': getattr(args, 'startup_timeout', None),
        'idle_timeout': getattr(args, 'idle_timeout', None),
        'keep_alive': getattr(args, 'keep_alive', False) if getattr(args, 'keep_alive', False) else None,
        'temperature': getattr(args, 'temperature', None),
        'max_tokens': getattr(args, 'max_tokens', None),
        'use_model': None,
        'config_path': str(config_path),
    })


def _prompt_should_use_model(args: argparse.Namespace) -> bool:
    settings = _model_settings_from_args(args)
    return any([
        settings.get('binary_path') or _env_or_default(None, 'ARC_LUCIFER_LLAMAFILE_BINARY'),
        settings.get('model_path') or _env_or_default(None, 'ARC_LUCIFER_LLAMAFILE_MODEL'),
        settings.get('endpoint'),
        settings.get('use_model') or _env_or_default(None, 'ARC_LUCIFER_USE_MODEL'),
    ])


def _configure_model_runtime(runtime: LuciferRuntime, args: argparse.Namespace) -> None:
    settings = _model_settings_from_args(args)
    binary_path = _env_or_default(settings.get('binary_path'), 'ARC_LUCIFER_LLAMAFILE_BINARY')
    model_path = _env_or_default(settings.get('model_path'), 'ARC_LUCIFER_LLAMAFILE_MODEL')
    host = _env_or_default(settings.get('host'), 'ARC_LUCIFER_LLAMAFILE_HOST', '127.0.0.1')
    port = _env_or_default(settings.get('port'), 'ARC_LUCIFER_LLAMAFILE_PORT')
    startup_timeout = float(_env_or_default(settings.get('startup_timeout'), 'ARC_LUCIFER_LLAMAFILE_STARTUP_TIMEOUT', 20.0))
    idle_timeout_raw = _env_or_default(settings.get('idle_timeout'), 'ARC_LUCIFER_LLAMAFILE_IDLE_TIMEOUT', 120.0)
    idle_timeout = None if str(idle_timeout_raw).lower() == 'none' else float(idle_timeout_raw)
    runtime.configure_llamafile(
        binary_path=binary_path,
        model_path=model_path,
        host=str(host),
        port=int(port) if port not in (None, '') else None,
        startup_timeout=startup_timeout,
        idle_timeout=idle_timeout,
        keep_alive=bool(settings.get('keep_alive') or str(os.getenv('ARC_LUCIFER_LLAMAFILE_KEEP_ALIVE', '')).lower() in {'1', 'true', 'yes'}),
        model_name=settings.get('model_name'),
    )


def _run_prompt(runtime: LuciferRuntime, args: argparse.Namespace) -> int:
    if not _prompt_should_use_model(args):
        return _print_json(runtime.handle(args.text, confirm=args.confirm))

    _configure_model_runtime(runtime, args)
    context = {'system': args.system or ''}
    options: dict[str, Any] = {}
    if args.temperature is not None:
        options['temperature'] = args.temperature
    if args.max_tokens is not None:
        options['max_tokens'] = args.max_tokens

    def on_chunk(payload: dict[str, Any]) -> None:
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




def _doctor(runtime: LuciferRuntime, args: argparse.Namespace) -> dict[str, Any]:
    config_path, config = load_runtime_config(args)
    db_path = runtime.kernel.db_path
    runtime_dir = default_runtime_dir(args.workspace)
    model_settings = _model_settings_from_args(args)
    binary_path = _env_or_default(model_settings.get('binary_path'), 'ARC_LUCIFER_LLAMAFILE_BINARY')
    model_path = _env_or_default(model_settings.get('model_path'), 'ARC_LUCIFER_LLAMAFILE_MODEL')
    checks: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, detail: str, level: str = 'error') -> None:
        checks.append({'name': name, 'ok': ok, 'detail': detail, 'level': level})

    workspace_path = Path(args.workspace).expanduser().resolve()
    add_check('python_version', tuple(map(int, platform.python_version_tuple()[:2])) >= (3, 11), f'Python {platform.python_version()}')
    add_check('workspace_exists', workspace_path.exists(), f'workspace={workspace_path}')
    runtime_dir.mkdir(parents=True, exist_ok=True)
    add_check('runtime_dir_writable', os.access(runtime_dir, os.W_OK), f'runtime_dir={runtime_dir}')
    stats = runtime.kernel.stats()
    add_check('db_configured', db_path is not None, f'db_path={db_path}')
    if db_path is not None:
        db_parent = Path(db_path).parent
        db_parent.mkdir(parents=True, exist_ok=True)
        add_check('db_parent_writable', os.access(db_parent, os.W_OK), f'db_parent={db_parent}')
    add_check('config_present', config_path.exists(), f'config_path={config_path}', level='warn')
    if binary_path and str(binary_path).startswith('/absolute/path/'):
        add_check('llamafile_binary_placeholder', True, f'binary_path={binary_path}', level='info')
    elif binary_path:
        binary_resolved = Path(str(binary_path)).expanduser()
        add_check('llamafile_binary', binary_resolved.exists(), f'binary_path={binary_path}', level='warn')
        if binary_resolved.exists():
            add_check('llamafile_executable', os.access(binary_resolved, os.X_OK), f'binary_path={binary_path}', level='warn')
    else:
        add_check('llamafile_binary_unset', True, 'No local model binary configured; deterministic runtime remains available.', level='info')
    if model_path and str(model_path).startswith('/absolute/path/'):
        add_check('llamafile_model_placeholder', True, f'model_path={model_path}', level='info')
    elif model_path:
        model_resolved = Path(str(model_path)).expanduser()
        add_check('llamafile_model', model_resolved.exists(), f'model_path={model_path}', level='warn')
    else:
        add_check('llamafile_model_unset', True, 'No GGUF model configured; model prompt path remains optional.', level='info')
    lucifer_bin = shutil.which('lucifer')
    add_check('lucifer_on_path', bool(lucifer_bin), f'lucifer={lucifer_bin}', level='warn')

    repo_root = _repo_root_from_workspace(workspace_path)
    if getattr(args, 'release_gate', False):
        checks.extend(_release_gate_checks(repo_root))

    warnings = sum(1 for check in checks if not check['ok'] and check['level'] == 'warn')
    errors = sum(1 for check in checks if not check['ok'] and check['level'] == 'error')
    strict_failures = warnings if getattr(args, 'strict', False) else 0
    summary = {
        'ok': errors == 0 and strict_failures == 0,
        'errors': errors + strict_failures,
        'warnings': warnings,
        'strict': bool(getattr(args, 'strict', False)),
    }
    return {
        'status': 'ok' if summary['ok'] else 'error',
        'summary': summary,
        'checks': checks,
        'paths': {
            'workspace': str(workspace_path),
            'runtime_dir': str(runtime_dir),
            'db_path': str(db_path) if db_path is not None else None,
            'config_path': str(config_path),
            'repo_root': str(repo_root),
        },
        'db_stats': stats,
        'config': config,
        'python_executable': sys.executable,
    }


def _config_command(args: argparse.Namespace) -> dict[str, Any]:
    config_path, config = load_runtime_config(args)
    if args.config_command == 'show':
        payload = {'status': 'ok', 'config_path': str(config_path), 'config': config}
        if args.resolved:
            payload['resolved'] = merge_settings(config, {'workspace': args.workspace, 'db': str(default_db_path(args.workspace))})
        return payload
    if args.config_command == 'init':
        if config_path.exists() and not args.force:
            return {'status': 'exists', 'config_path': str(config_path), 'reason': 'Config already exists. Use --force to overwrite.'}
        starter = {
            'workspace': str(Path(args.workspace).expanduser().resolve()),
            'db': str(default_db_path(args.workspace)),
            'model': {
                'binary_path': '/absolute/path/to/llamafile',
                'model_path': '/absolute/path/to/model.gguf',
                'host': '127.0.0.1',
                'port': 8080,
                'startup_timeout': 20.0,
                'idle_timeout': 120.0,
                'keep_alive': False,
            },
        }
        written = save_config(config_path, starter)
        return {'status': 'ok', 'config_path': str(written), 'config': starter}
    return {'status': 'error', 'reason': f'Unsupported config command: {args.config_command}'}


def _export_command(runtime: LuciferRuntime, args: argparse.Namespace) -> dict[str, Any]:
    if not args.jsonl and not args.sqlite_backup:
        return {'status': 'error', 'reason': 'Provide --jsonl and/or --sqlite-backup.'}
    payload: dict[str, Any] = {'status': 'ok'}
    if args.jsonl:
        payload['jsonl_path'] = str(runtime.kernel.export_events_jsonl(args.jsonl).resolve())
    if args.sqlite_backup:
        payload['sqlite_backup_path'] = str(runtime.kernel.backup_sqlite(args.sqlite_backup).resolve())
    payload['db_stats'] = runtime.kernel.stats()
    return payload


def _import_command(runtime: LuciferRuntime, args: argparse.Namespace) -> dict[str, Any]:
    imported = runtime.kernel.import_events_jsonl(args.jsonl)
    return {'status': 'ok', 'imported_events': imported, 'db_stats': runtime.kernel.stats()}


def _compact_command(runtime: LuciferRuntime) -> dict[str, Any]:
    result = runtime.kernel.compact()
    return {'status': 'ok', **result}


def _info_command(runtime: LuciferRuntime, args: argparse.Namespace) -> dict[str, Any]:
    config_path, _config = load_runtime_config(args)
    return {
        'status': 'ok',
        'paths': {
            'workspace': str(Path(args.workspace).expanduser().resolve()),
            'runtime_dir': str(default_runtime_dir(args.workspace)),
            'db_path': str(runtime.kernel.db_path) if runtime.kernel.db_path else None,
            'config_path': str(config_path),
        },
        'db_stats': runtime.kernel.stats(),
    }


def _monitor_command(runtime: LuciferRuntime, args: argparse.Namespace) -> int:
    import time

    def build_payload() -> dict[str, Any]:
        info = _info_command(runtime, args)
        state = runtime.kernel.state().__dict__
        return {'status': 'ok', 'panel': render_monitor_panel(info, state), 'info': info, 'state': state}

    if args.watch and args.watch > 0:
        iterations = max(1, int(args.iterations))
        for idx in range(iterations):
            payload = build_payload()
            print(payload['panel'])
            if idx < iterations - 1:
                print('\n' + '=' * 72 + '\n')
                time.sleep(args.watch)
        return 0
    return _print_json(build_payload())



def _memory_manager(args: argparse.Namespace, runtime: LuciferRuntime) -> MemoryManager:
    runtime_dir = default_runtime_dir(args.workspace)
    retention_cfg = load_runtime_config(args)[1].get('retention', {})
    config = RetentionConfig(
        hot_days=int(retention_cfg.get('hot_days', 30)),
        warm_days=int(retention_cfg.get('warm_days', 180)),
        access_grace_days=int(retention_cfg.get('access_grace_days', 45)),
    )
    return MemoryManager(runtime.kernel, runtime_dir / 'memory', config)


def _memory_command(runtime: LuciferRuntime, args: argparse.Namespace) -> int:
    manager = _memory_manager(args, runtime)
    if args.memory_command == 'status':
        return _print_json(manager.memory_status())
    if args.memory_command == 'archive-now':
        return _print_json(manager.archive_now_but_keep_live(args.event_id, reason=args.reason, archive_branch_id=args.archive_branch_id))
    if args.memory_command == 'sync':
        return _print_json(manager.sync_live_mirrors(event_id=args.event_id))
    if args.memory_command == 'search':
        return _print_json(manager.search_memory(args.query, limit=args.limit))
    return _print_json({'status': 'error', 'reason': f'unknown memory command: {args.memory_command}'})


def _model_profile_store(args: argparse.Namespace) -> ModelProfileStore:
    return ModelProfileStore(default_runtime_dir(args.workspace))


def _parse_kv_pairs(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        if '=' not in item:
            raise ValueError(f'Expected key=value pair, got: {item}')
        key, value = item.split('=', 1)
        result[key.strip()] = value.strip()
    return result


def _model_command(runtime: LuciferRuntime, args: argparse.Namespace) -> int:
    store = _model_profile_store(args)
    if args.model_command == 'backends':
        return _print_json({'status': 'ok', 'backends': runtime.backends.names()})
    if args.model_command == 'profiles':
        return _print_json(store.list_profiles())
    if args.model_command == 'show-profile':
        return _print_json(store.show_profile(args.name))
    if args.model_command == 'register-profile':
        extra = _parse_kv_pairs(args.param)
        profile = {
            'backend_type': args.backend_type,
            'binary_path': args.binary_path,
            'model_path': args.model_path,
            'endpoint': args.endpoint,
            'notes': args.notes,
            'intended_use': args.intended_use,
            'training_ready': args.training_ready,
            'metadata': extra,
        }
        return _print_json(store.register_profile(args.name, profile, activate=args.activate))
    if args.model_command == 'activate-profile':
        return _print_json(store.activate_profile(args.name))
    if args.model_command == 'compare-profiles':
        return _print_json(store.compare_profiles(args.names))
    return _print_json({'status': 'error', 'reason': f'unknown model command: {args.model_command}'})


def _train_command(runtime: LuciferRuntime, args: argparse.Namespace) -> int:
    exporter = TrainingCorpusExporter()
    state = runtime.kernel.state()
    if args.train_command == 'export-supervised':
        return _print_json(exporter.export_supervised(state, args.output))
    if args.train_command == 'export-preferences':
        return _print_json(exporter.export_preferences(state, args.output))
    return _print_json({'status': 'error', 'reason': f'unknown train command: {args.train_command}'})

