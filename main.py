import asyncio
import argparse
from modules.speedtest import SpeedTest
from modules.zitel import Zitel, CellInfo
from modules.helper import Helper
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
import json
import sys
import os

# init
console = Console()
helper = Helper()
os.system('cls' if os.name == 'nt' else 'clear')

# ---------------- Load config ----------------
async def load_config():
    console.print("[bold green][+] Loading configs...")
    config = helper.load_json(helper.resource_path("config.json"))
    command_codes = helper.load_json(helper.resource_path("command_codes.json"))
    if config and command_codes:
        console.print(Panel.fit(f"[bold green][+] Config Loaded:[/bold green]\n[magenta]{json.dumps(config, indent=2)}[/magenta]" +
                        f"\n[bold green][+] Loaded {len(command_codes)} Command Codes[/bold green]",
                    title="Welcome to Zitel Optimizer",
                    subtitle="Developed by @nimazerobit",
                    border_style="cyan"
        ))
        print()
        return config, command_codes
    else:
        sys.exit(1)

# ---------------- Check is modem reachable ----------------
async def is_modem_reachable(modem_ip):
    with console.status("[bold yellow] Checking connection to modem...") as status:
        result = helper.check_ping(modem_ip, 3)
        if result > -1:
            console.print(f"[green]Modem Latency: {result:.4f} ms[/green]")
        else:
            console.print("[red][-] Modem Unreachable: Disable your VPN and try again.[/red]")
            sys.exit(1)

# ---------------- Login to modem ----------------
async def login_to_modem(modem_ip, command_codes):
    with console.status("[bold yellow] Authenticating with the modem...") as _:
        zitel = Zitel(f"http://{modem_ip}/cgi-bin/http.cgi", command_codes)
        try:
            session_id = zitel.login("farabord", "farabord")
            if session_id:
                console.print("[green][+] Login successful.[/green]")
                console.print(f"[cyan][!] Session ID: [bold]{session_id}[/bold][/cyan]")
                return zitel, session_id
            else:
                console.print("[red][-] Login failed — please check your username and password and try again.[/red]")
                sys.exit(1)
        except ValueError as err:
            console.print(f"[red][-] {err}. Please try again.[/red]")
            sys.exit(1)
        except:
            console.print("[red][-] An unexpected error occurred. Please try again.[/red]")
            sys.exit(1)

# ---------------- Get current cell info ----------------
async def get_current_cell_info(zitel, session_id) -> CellInfo:
    with console.status("[bold yellow] Retrieving current cellular information from modem...") as _:
        current_cell_info = zitel.get_current_cell_info(session_id)
        if not (current_cell_info.cell_id == 0 and current_cell_info.earfcn == 0):
            console.print(Panel.fit(f"[green][+] Cell ID:[/green] {current_cell_info.cell_id}\n" +
                                    f"[green][+] EARFCN:[/green] {current_cell_info.earfcn}\n" +
                                    f"[green][+] Locked:[/green] {current_cell_info.locked}",
                                    title="Cell Info"))
            return current_cell_info
        else:
            console.print("[red][-] Invalid cellular information. Please try again.[/red]")
            sys.exit(1)

# ---------------- Scan for best EARFCN ----------------
async def scan_best_earfcn(zitel, session_id, current_cell_info, config):
    speedtest = SpeedTest(config['speedtest_cli_path'])
    speedtest_results = dict()
    try:
        with console.status("[bold yellow] Scanning for best EARFCN...") as status:
            for earfcn in config["valid_earfcn"]:
                console.print(f"[yellow][!] Setting EARFCN to [cyan]{earfcn}[/cyan] on Cell ID [cyan]{current_cell_info.cell_id}[/cyan][/yellow]")
                result = zitel.set_earfcn(earfcn, current_cell_info.cell_id, session_id)
                if result:
                    console.print("[green][+] EARFCN set successfully.[/green]")
                    status.update("[bold yellow] Waiting for internet connection...")
                    await asyncio.sleep(3)
                    if await helper.wait_for_internet(config["ping_check_ip"]):
                        status.update("[bold yellow] Testing connection speed...")
                        results = await speedtest.run()
                        if results:
                            console.print(f"[cyan][+] Speedtest result: Ping -> [green]{results.ping}[/green] | Downlink: [green]{results.download} Mbps[/green] | Uplink: [green]{results.upload} Mbps[/green][/cyan]")
                            speedtest_results[earfcn] = results
                        else:
                            console.print("[red][-] Failed to run speedtest.[/red]")
                    else:
                        console.print("[red][-] Failed to connect to the Internet.[/red]")

    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n[bold yellow][!] Scan interrupted by user.[/bold yellow]")
        if not speedtest_results:
            raise

    if not speedtest_results:
        return None, {}

    fastest_earfcn = max(
        speedtest_results,
        key=lambda x: speedtest_results[x].download
    )

    console.print(
        f"\n[bold green][+] Fastest EARFCN Found:[/bold green] "
        f"[cyan]{fastest_earfcn}[/cyan] with Download Speed -> "
        f"[cyan]{speedtest_results[fastest_earfcn].download} Mbps[/cyan]"
    )

    return fastest_earfcn, speedtest_results

async def set_earfcn(zitel, session_id, current_cell_info, config, target_earfcn):
    with console.status("[bold yellow] Setting modem to the fastest EARFCN...") as status:
        result = zitel.set_earfcn(target_earfcn, current_cell_info.cell_id, session_id)
        if result:
            console.print(f"[green][+] EARFCN set to [cyan]{target_earfcn}[/cyan] successfully.[/green]")
            status.update("[bold yellow] Waiting for internet connection...")
            await asyncio.sleep(3)
            if await helper.wait_for_internet(config["ping_check_ip"]):
                status.update(f"[bold yellow] Checking ping time to [cyan]{config["ping_check_ip"]}[/cyan]...")
                ping = helper.check_ping(config["ping_check_ip"])
                if ping > 0:
                    console.print(f"[green][+] Average ping to [cyan]{config["ping_check_ip"]}[/cyan] -> [cyan]{ping:.4f} ms[/cyan][/green]")
                else:
                    console.print("[red][-] Failed to connect to the Internet.[/red]")
            else:
                console.print("[red][-] Failed to connect to the Internet.[/red]")
        else:
            console.print("[red][-] Failed to set modem to the fastest EARFCN.[/red]")
            sys.exit(1)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--yes", action="store_true")
    parser.add_argument("--info", action="store_true")
    args = parser.parse_args()

    config, command_codes = await load_config()
    await is_modem_reachable(config["modem_ip"])
    zitel, session_id = await login_to_modem(config["modem_ip"], command_codes)
    current_cell_info = await get_current_cell_info(zitel, session_id)

    if args.info:
        return

    selected_earfcn = None

    if not args.yes:
        if Confirm.ask("Do you want to manually select EARFCN from valid list?"):
            valid_earfcn = config["valid_earfcn"]
            selected_earfcn = Prompt.ask("Enter EARFCN", choices=[str(e) for e in valid_earfcn])

    if selected_earfcn is None:
        if not args.yes:
            if not Confirm.ask("Do you want to scan for best EARFCN?"):
                return
        fastest_earfcn, scan_results = await scan_best_earfcn(zitel, session_id, current_cell_info, config)
        if not scan_results:
            console.print("[red][-] No valid EARFCN results found.[/red]")
            return

        if Confirm.ask("Do you want to manually select EARFCN from scan results?"):
            selected_earfcn = int(
                Prompt.ask(
                    "Enter EARFCN",
                    choices=[str(e) for e in scan_results.keys()]
                )
            )
        else:
            selected_earfcn = fastest_earfcn
            console.print(
                f"[bold green][+] Auto-selected fastest EARFCN: "
                f"[cyan]{selected_earfcn}[/cyan][/bold green]"
            )

    if not args.yes:
        if not Confirm.ask(f"Do you want to set EARFCN to {selected_earfcn}?"):
            return

    await set_earfcn(zitel, session_id, current_cell_info, config, selected_earfcn)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n[bold yellow][!] Interrupted by user. [/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold yellow][!] An unexpected error occurred: {e} [/bold yellow]")
    finally:
        console.print("[cyan][!] Goodbye :)[/cyan]")