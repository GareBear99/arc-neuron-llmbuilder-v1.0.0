from __future__ import annotations

import shutil
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class ManagedLlamafile:
    binary_path: Path
    model_path: Path | None
    host: str
    port: int
    process: subprocess.Popen | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class LlamafileProcessManager:
    def __init__(
        self,
        binary_path: str | Path | None = None,
        model_path: str | Path | None = None,
        host: str = '127.0.0.1',
        port: int | None = None,
        startup_timeout: float = 20.0,
        keep_alive: bool = True,
        extra_args: Iterable[str] | None = None,
    ) -> None:
        self.binary_path = self._resolve_binary(binary_path)
        self.model_path = Path(model_path).expanduser().resolve() if model_path else None
        self.host = host
        self.port = port or self._find_free_port(host)
        self.startup_timeout = startup_timeout
        self.keep_alive = keep_alive
        self.extra_args = list(extra_args or [])
        self._managed: ManagedLlamafile | None = None

    def ensure_running(self) -> ManagedLlamafile:
        if self._managed and self._managed.process and self._managed.process.poll() is None:
            return self._managed
        cmd = [str(self.binary_path), '--host', self.host, '--port', str(self.port)]
        if self.model_path:
            cmd.extend(['-m', str(self.model_path)])
        cmd.extend(self.extra_args)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        managed = ManagedLlamafile(binary_path=self.binary_path, model_path=self.model_path, host=self.host, port=self.port, process=proc)
        self._wait_until_ready(managed.base_url)
        self._managed = managed
        return managed

    def stop(self) -> None:
        if not self._managed or not self._managed.process:
            return
        proc = self._managed.process
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        self._managed = None

    def _resolve_binary(self, binary_path: str | Path | None) -> Path:
        candidates = []
        if binary_path:
            candidates.append(Path(binary_path).expanduser())
        env_found = shutil.which('llamafile')
        if env_found:
            candidates.append(Path(env_found))
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.exists():
                return resolved
        if binary_path:
            return Path(binary_path).expanduser().resolve()
        return Path('llamafile').resolve()

    def _wait_until_ready(self, base_url: str) -> None:
        deadline = time.time() + self.startup_timeout
        urls = [f"{base_url}/health", f"{base_url}/v1/models", base_url]
        last_error: Exception | None = None
        while time.time() < deadline:
            for url in urls:
                try:
                    with urllib.request.urlopen(url, timeout=1.0) as resp:  # nosec - loopback only
                        if resp.status < 500:
                            return
                except Exception as exc:  # pragma: no cover - exercised via timeout path
                    last_error = exc
            time.sleep(0.1)
        raise RuntimeError(f'llamafile failed to become ready on {base_url}') from last_error

    @staticmethod
    def _find_free_port(host: str) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])
