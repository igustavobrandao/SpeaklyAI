from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass

import psutil

try:
    import pynvml as nvml

    _NVML_AVAILABLE = True
except ImportError:
    _NVML_AVAILABLE = False


@dataclass
class Metrics:
    ram_mb: float
    vram_mb: float
    vram_total_mb: float
    gpu_percent: float
    cpu_percent: float


class MetricsCollector:
    _BYTES_PER_MB: float = 1024.0 ** 2

    def __init__(self) -> None:
        self._process = psutil.Process(os.getpid())
        self._gpu_handle = None

        if _NVML_AVAILABLE:
            try:
                nvml.nvmlInit()
                self._gpu_handle = nvml.nvmlDeviceGetHandleByIndex(0)
            except Exception:
                self._gpu_handle = None

    def get_metrics(self) -> Metrics:
        mem_info = self._process.memory_info()
        ram_mb = mem_info.rss / self._BYTES_PER_MB
        cpu = self._process.cpu_percent(interval=None)

        if self._gpu_handle is not None:
            try:
                vram = nvml.nvmlDeviceGetMemoryInfo(self._gpu_handle)
                util = nvml.nvmlDeviceGetUtilizationRates(self._gpu_handle)
                vram_mb = vram.used / self._BYTES_PER_MB
                vram_total_mb = vram.total / self._BYTES_PER_MB
                gpu_percent = float(util.gpu)
            except Exception:
                vram_mb, vram_total_mb, gpu_percent = 0.0, 0.0, 0.0
        else:
            vram_mb, vram_total_mb, gpu_percent = 0.0, 0.0, 0.0

        return Metrics(
            ram_mb=ram_mb,
            vram_mb=vram_mb,
            vram_total_mb=vram_total_mb,
            gpu_percent=gpu_percent,
            cpu_percent=cpu,
        )

    def __del__(self) -> None:
        if _NVML_AVAILABLE and self._gpu_handle is not None:
            with suppress(Exception):
                nvml.nvmlShutdown()


if __name__ == "__main__":
    collector = MetricsCollector()
    m = collector.get_metrics()
    print(f"RAM:       {m.ram_mb:.1f} MB")
    print(f"VRAM:      {m.vram_mb:.1f} / {m.vram_total_mb:.1f} MB")
    print(f"GPU:       {m.gpu_percent:.1f}%")
    print(f"CPU:       {m.cpu_percent:.1f}%")
