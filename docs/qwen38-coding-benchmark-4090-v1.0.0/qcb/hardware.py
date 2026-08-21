from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class GPUSample:
    timestamp: float
    memory_used_mb: float
    utilization_gpu_pct: float
    power_w: float
    temperature_c: float


class GPUSampler:
    def __init__(self, interval_seconds: float = 0.5):
        self.interval_seconds = interval_seconds
        self.samples: list[GPUSample] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _read(self) -> GPUSample | None:
        command = [
            "nvidia-smi",
            "--query-gpu=memory.used,utilization.gpu,power.draw,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        try:
            output = subprocess.check_output(command, text=True, timeout=3).splitlines()[0]
            values = [float(part.strip()) for part in output.split(",")]
            return GPUSample(time.time(), values[0], values[1], values[2], values[3])
        except Exception:
            return None

    def _loop(self) -> None:
        while not self._stop.is_set():
            sample = self._read()
            if sample:
                self.samples.append(sample)
            self._stop.wait(self.interval_seconds)

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if not self.samples:
            return {"available": False, "samples": 0}
        return {
            "available": True,
            "samples": len(self.samples),
            "peak_memory_used_mb": max(x.memory_used_mb for x in self.samples),
            "average_gpu_utilization_pct": sum(x.utilization_gpu_pct for x in self.samples) / len(self.samples),
            "peak_power_w": max(x.power_w for x in self.samples),
            "peak_temperature_c": max(x.temperature_c for x in self.samples),
            "raw": [asdict(x) for x in self.samples],
        }
