import argparse
import asyncio
import os
from rich.console import Console
from modules.helper import Helper
from modules.menu import Menu
from modules.workflow import Workflow
from modules.zitel import Zitel

console = Console()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quick", action="store_true"
    )
    parser.add_argument(
        "--info", action="store_true"
    )
    parser.add_argument(
        "--set", type=int, metavar="EARFCN", help="Manually set EARFCN without the menu"
    )
    return parser.parse_args()

async def bootstrap(workflow: Workflow) -> None:
    await workflow.load_config()
    await workflow.check_modem_reachable()
    await workflow.login()
    await workflow.refresh_cell_info()
    workflow.print_cell_info()

async def run_quick_mode(workflow: Workflow) -> None:
    fastest_earfcn, scan_results = await workflow.scan_best_earfcn()
    if not scan_results:
        console.print("[red][-] No valid EARFCN results found.[/red]")
        return

    console.print(
        f"[bold green][+] Quick mode selected fastest EARFCN: [cyan]{fastest_earfcn}[/cyan][/bold green]"
    )
    await workflow.set_earfcn(fastest_earfcn)

async def main() -> None:
    os.system("cls" if os.name == "nt" else "clear")
    args = parse_args()

    workflow = Workflow(console, Helper(), Zitel)
    await bootstrap(workflow)

    if args.info:
        return

    if args.quick:
        await workflow.quick_optimize()
        return

    if args.set is not None:
        valid_earfcn = workflow.config["valid_earfcn"]
        if args.set not in valid_earfcn:
            console.print(
                f"[red][-] Invalid EARFCN: [cyan]{args.set}[/cyan]. Valid options: {valid_earfcn}[/red]"
            )
            return
        if workflow.current_cell_info["earfcn"] == args.set:
            console.print(
                f"[yellow][!] EARFCN is already set to [cyan]{args.set}[/cyan]. Nothing to do.[/yellow]"
            )
            return
        await workflow.set_earfcn(args.set)
        return

    await Menu(console, workflow).run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError, EOFError):
        console.print("\n[bold yellow][!] Interrupted by user. [/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold yellow][!] An unexpected error occurred: {e} [/bold yellow]")
    finally:
        console.print("[cyan][!] Goodbye :)[/cyan]")
