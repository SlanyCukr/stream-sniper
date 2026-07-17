"""Render collected health snapshots into the JSON and Prometheus contracts."""

from .health_contracts import (
    ComponentHealthPayload,
    DetailedHealthPayload,
    ExternalApisPayload,
    HealthSnapshot,
    HealthStatus,
    iso_z,
    overall_health_status,
)

MILLISECONDS_PER_SECOND = 1_000

_PROMETHEUS_STATUS = {
    HealthStatus.HEALTHY: 1,
    HealthStatus.DEGRADED: 0.75,
    HealthStatus.UNHEALTHY: 0.5,
    HealthStatus.CRITICAL: 0,
    HealthStatus.UNKNOWN: -1,
}


def detailed_health_payload(snapshot: HealthSnapshot) -> DetailedHealthPayload:
    """Render the detailed JSON contract from an already-collected snapshot."""
    component_payloads = {name: component.to_dict() for name, component in snapshot.components.items()}
    twitch = component_payloads.pop("twitch_api", None)
    serialized: dict[str, ComponentHealthPayload | ExternalApisPayload] = dict(component_payloads)
    if twitch is not None:
        serialized["external_apis"] = {"twitch": twitch}
    return {
        "status": overall_health_status(snapshot.components).value,
        "timestamp": iso_z(snapshot.checked_at),
        "version": snapshot.version,
        "uptime_seconds": snapshot.application_uptime_seconds,
        "components": serialized,
        "system": {
            "platform": snapshot.platform_name,
            "python_version": snapshot.python_version,
            "cpu_count": snapshot.cpu_count,
            "resources": snapshot.resources.to_dict(),
        },
    }


def render_prometheus(snapshot: HealthSnapshot) -> str:
    """Render one snapshot in Prometheus text exposition format."""
    timestamp_ms = int(snapshot.checked_at.timestamp() * MILLISECONDS_PER_SECOND)
    lines = [
        "# HELP stream_sniper_component_health Health status of system components",
        "# TYPE stream_sniper_component_health gauge",
    ]
    for name, component in snapshot.components.items():
        lines.append(
            f'stream_sniper_component_health{{component="{name}"}} '
            f"{_PROMETHEUS_STATUS[component.status]} {timestamp_ms}"
        )
    lines.extend(
        [
            "",
            "# HELP stream_sniper_component_response_time_ms Component health-check duration",
            "# TYPE stream_sniper_component_response_time_ms gauge",
        ]
    )
    for name, component in snapshot.components.items():
        lines.append(
            f'stream_sniper_component_response_time_ms{{component="{name}"}} '
            f"{component.response_time_ms} {timestamp_ms}"
        )
    resources = snapshot.resources
    lines.extend(
        [
            "",
            "# HELP stream_sniper_system_cpu_percent Current CPU usage percentage",
            "# TYPE stream_sniper_system_cpu_percent gauge",
            f"stream_sniper_system_cpu_percent {resources.cpu_percent} {timestamp_ms}",
            "",
            "# HELP stream_sniper_system_memory_percent Current memory usage percentage",
            "# TYPE stream_sniper_system_memory_percent gauge",
            f"stream_sniper_system_memory_percent {resources.memory_percent} {timestamp_ms}",
            "",
            "# HELP stream_sniper_system_memory_mb Memory usage in megabytes",
            "# TYPE stream_sniper_system_memory_mb gauge",
            f'stream_sniper_system_memory_mb{{type="available"}} {resources.memory_available_mb} {timestamp_ms}',
            f'stream_sniper_system_memory_mb{{type="used"}} {resources.memory_used_mb} {timestamp_ms}',
            f'stream_sniper_system_memory_mb{{type="total"}} {resources.memory_total_mb} {timestamp_ms}',
            "",
            "# HELP stream_sniper_system_disk_percent Current disk usage percentage",
            "# TYPE stream_sniper_system_disk_percent gauge",
            f"stream_sniper_system_disk_percent {resources.disk_percent} {timestamp_ms}",
            "",
            "# HELP stream_sniper_system_disk_gb Disk usage in gigabytes",
            "# TYPE stream_sniper_system_disk_gb gauge",
            f'stream_sniper_system_disk_gb{{type="free"}} {resources.disk_free_gb} {timestamp_ms}',
            f'stream_sniper_system_disk_gb{{type="total"}} {resources.disk_total_gb} {timestamp_ms}',
            "",
            "# HELP stream_sniper_uptime_seconds Application uptime in seconds",
            "# TYPE stream_sniper_uptime_seconds gauge",
            f"stream_sniper_uptime_seconds {snapshot.application_uptime_seconds} {timestamp_ms}",
        ]
    )
    if resources.load_average is not None:
        lines.extend(
            [
                "",
                "# HELP stream_sniper_system_load_average System load average",
                "# TYPE stream_sniper_system_load_average gauge",
                f'stream_sniper_system_load_average{{period="1m"}} {resources.load_average[0]} {timestamp_ms}',
                f'stream_sniper_system_load_average{{period="5m"}} {resources.load_average[1]} {timestamp_ms}',
                f'stream_sniper_system_load_average{{period="15m"}} {resources.load_average[2]} {timestamp_ms}',
            ]
        )
    return "\n".join(lines) + "\n"
