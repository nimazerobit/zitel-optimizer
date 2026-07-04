import asyncio
import sys
from rich.console import Console
from .speedtest import SpeedTest

class Workflow:
    def __init__(self, console: Console, helper, zitel_cls):
        self.console = console
        self.helper = helper
        self.zitel_cls = zitel_cls

        self.config = None
        self.command_codes = None
        self.zitel = None
        self.session_id = None
        self.current_cell_info = None

    # ---------------- Config ----------------
    async def load_config(self):
        self.config = self.helper.load_json(self.helper.resource_path("config.json"))
        self.command_codes = self.helper.load_json(self.helper.resource_path("command_codes.json"))

        if not (self.config and self.command_codes):
            sys.exit(1)

        self.console.print(
            f"[green][+] Config Loaded[/green]"
            f"\n[green][+] Loaded {len(self.command_codes)} Command Codes[/green]"
            f"\n[green][+] Modem IP is {self.config["modem_ip"]}[/green]"
        )

    # ---------------- Connectivity ----------------
    async def check_modem_reachable(self):
        with self.console.status("[bold yellow] Checking connection to modem...") as _:
            result = self.helper.check_ping(self.config["modem_ip"], 3)
            if result > -1:
                self.console.print(f"[green][+] Modem Latency: {result:.4f} ms[/green]")
            else:
                self.console.print("[red][-] Modem Unreachable.[/red]")
                sys.exit(1)

    # ---------------- Auth ----------------
    async def login(self):
        with self.console.status("[bold yellow] Authenticating with the modem...") as _:
            self.zitel = self.zitel_cls(
                f"http://{self.config['modem_ip']}/cgi-bin/http.cgi", self.command_codes
            )
            try:
                self.session_id = self.zitel.login(self.config["username"], self.config["password"])
                if self.session_id:
                    self.console.print("[green][+] Login successful.[/green]")
                    self.console.print(f"[green][+] Session ID: [bold]{self.session_id[:8]}{'*' * (len(self.session_id) - 8)}[/bold][/green]")
                else:
                    self.console.print(
                        "[red][-] Login failed — please check your username and password and try again.[/red]"
                    )
                    sys.exit(1)
            except ValueError as e:
                self.console.print(f"[red][-] {e}. Please try again.[/red]")
                sys.exit(1)
            except Exception as e:
                self.console.print(f"[red][-] An unexpected error occurred: {e}[/red]")
                sys.exit(1)

    # ---------------- Cell info ----------------
    async def refresh_cell_info(self) -> dict:
        with self.console.status("[bold yellow] Retrieving current cell info from modem...") as _:
            info = self.zitel.get_current_cell_info(self.session_id)
            if info["cell_id"] == 0 and info["earfcn"] == 0:
                self.console.print("[red][-] Invalid cell info. Please try again.[/red]")
                sys.exit(1)
            self.current_cell_info = info
        return self.current_cell_info

    def print_cell_info(self):
        info = self.current_cell_info
        self.console.print(
            f"[cyan][*] Cell ID:[/cyan] {info['cell_id']}\n"
            f"[cyan][*] EARFCN:[/cyan] {info['earfcn']}\n"
            f"[cyan][*] Locked:[/cyan] {info['locked']}"
        )

    # ---------------- EARFCN scan/apply ----------------
    async def scan_best_earfcn(self):
        speedtest = SpeedTest()
        speedtest_results = {}
        cell_id = self.current_cell_info["cell_id"]

        try:
            with self.console.status("[bold yellow] Scanning for best EARFCN...") as status:

                for earfcn in self.config["valid_earfcn"]:

                    if not self.zitel.set_earfcn(earfcn, cell_id, self.session_id):
                        self.console.print(
                            f"\n[red][-] Failed to set EARFCN [cyan]{earfcn}[/cyan][/red]"
                        )
                        continue

                    self.console.print(
                        f"\n[green][+] EARFCN set to [cyan]{earfcn}[/cyan][/green]"
                    )

                    status.update("[bold yellow] Waiting for internet connection...")
                    await asyncio.sleep(3)

                    if not await self.helper.wait_for_internet(self.config["ping_check_ip"]):
                        self.console.print("\n[red][-] Internet connection failed.[/red]")
                        continue

                    status.update("[bold yellow] Running speedtest...")
                    results = await speedtest.run()

                    if results:
                        self.console.print(
                            f"[green][+] Speedtest -> "
                            f"Ping [cyan]{results.ping}[/cyan] | "
                            f"Down [cyan]{results.download} Mbps[/cyan] | "
                            f"Up [cyan]{results.upload} Mbps[/cyan][/green]"
                        )
                        speedtest_results[earfcn] = results

        except KeyboardInterrupt:
            self.console.print("\n\n[yellow][!] Scan interrupted by user.[/yellow]")

        if not speedtest_results:
            return None, {}

        fastest = max(speedtest_results, key=lambda x: speedtest_results[x].download)

        self.console.print(
            f"\n[green][+] Fastest EARFCN: [cyan]{fastest}[/cyan] ({speedtest_results[fastest].download} Mbps)[/green]"
        )

        return fastest, speedtest_results

    async def set_earfcn(self, target_earfcn):
        async def _apply():
            with self.console.status("[bold yellow] Setting modem EARFCN...") as status:
                if not self.zitel.set_earfcn(
                    target_earfcn,
                    self.current_cell_info["cell_id"],
                    self.session_id,
                ):
                    self.console.print("\n[red][-] Failed to set modem EARFCN.[/red]")
                    return

                self.console.print(
                    f"\n[green][+] EARFCN set to [cyan]{target_earfcn}[/cyan][/green]"
                )

                status.update("[bold yellow] Waiting for internet connection...")
                await asyncio.sleep(3)

                if not await self.helper.wait_for_internet(self.config["ping_check_ip"]):
                    self.console.print("\n[red][-] Internet connection failed.[/red]")
                    return

                ping = self.helper.check_ping(self.config["ping_check_ip"])

                if ping > 0:
                    self.console.print(
                        f"[green][+] Ping to [cyan]{self.config["ping_check_ip"]}[/cyan] is [cyan]{ping:.2f} ms[/cyan][/green]"
                    )
        try:
            await asyncio.shield(_apply())
        except KeyboardInterrupt:
            # ignored intentionally
            pass
                
    async def quick_optimize(self):
        fastest_earfcn, scan_results = await self.scan_best_earfcn()

        if not scan_results:
            self.console.print("\n[red][-] No valid EARFCN results found.[/red]")
            return

        self.console.print(
            f"\n[green][+] Auto-selected fastest EARFCN: [cyan]{fastest_earfcn}[/cyan][/green]"
        )

        await self.set_earfcn(fastest_earfcn)