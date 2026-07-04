import asyncio
from dataclasses import dataclass
from rich import print
import speedtest

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
    async def run(self) -> SpeedTestResult | None:
        try:
            return await asyncio.to_thread(self._run_speedtest)

        except Exception as e:
            print(f"[red][-] Exception while running speedtest:[/red] {e}")
            return None

    @staticmethod
    def _run_speedtest() -> SpeedTestResult:
        st = speedtest.Speedtest(secure=True)

        st.get_best_server()

        download_bps = st.download()
        upload_bps = st.upload()

        results = st.results.dict()
        return SpeedTest._parse_result(results)

    @staticmethod
    def _parse_result(data: dict) -> SpeedTestResult:
        download_mbps = data["download"] / 1_000_000
        upload_mbps = data["upload"] / 1_000_000
        ping_ms = data["ping"]

        server_info = data["server"]
        server_name = (
            f'{server_info["name"]} '
            f'({server_info["country"]})'
        )

        return SpeedTestResult(
            download=round(download_mbps, 2),
            upload=round(upload_mbps, 2),
            ping=round(ping_ms, 2),
            server=server_name,
        )