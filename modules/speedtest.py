import subprocess
import json
from dataclasses import dataclass
from rich import print

# NOTE:
# Download and upload speeds are in Mbps (megabits per second)
# Ping is in ms (milliseconds)
@dataclass
class SpeedTestResult:
    download: float
    upload: float
    ping: float
    server: str

class SpeedTest:
    def __init__(self, speedtest_cli_path: str):
        self.speedtest_cli_path = speedtest_cli_path

    async def run(self) -> SpeedTestResult | None:
        try:
            result = subprocess.run(
                [self.speedtest_cli_path, "-f", "json"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                print(f"[red][-] Speedtest error: {result.stderr}[/red]")
                return None

            data = json.loads(result.stdout)
            return self._parse_result(data)

        except Exception as e:
            print(f"[red][-] An exception occurred while running speedtest:[/red] {e}")
            return None

    @staticmethod
    def _parse_result(data: dict) -> SpeedTestResult:
        download_mbps = data["download"]["bandwidth"] * 8 / 1_000_000
        upload_mbps = data["upload"]["bandwidth"] * 8 / 1_000_000
        ping_ms = data["ping"]["latency"]

        server_info = data["server"]
        server_name = f'{server_info["name"]} ({server_info["location"]}, {server_info["country"]})'

        return SpeedTestResult(
            download=round(download_mbps, 2),
            upload=round(upload_mbps, 2),
            ping=round(ping_ms, 2),
            server=server_name
        )
