from rich.console import Console
from rich.prompt import Prompt
from .workflow import Workflow

MENU_OPTIONS = {
    "1": "Show current cell info",
    "2": "Scan and manually select best EARFCN",
    "3": "Scan and automatically select best EARFCN",
    "4": "Manually set EARFCN",
    "5": "Exit",
}

class Menu:
    def __init__(self, console: Console, workflow: Workflow):
        self.console = console
        self.workflow = workflow

    def _print_menu(self):
        self.console.print("\n[bold cyan]===== Zitel Optimizer =====[/bold cyan]")
        for key, label in MENU_OPTIONS.items():
            self.console.print(f"  [cyan]{key}[/cyan]. {label}")

    async def run(self):
        while True:
            self._print_menu()
            choice = Prompt.ask("Select an option", choices=list(MENU_OPTIONS.keys()), default="5")
            self.console.print()

            if choice == "1":
                self.workflow.print_cell_info()

            elif choice == "2":
                await self.workflow.scan_best_earfcn()
                await self._manual_select()

            elif choice == "3":
                await self.workflow.quick_optimize()

            elif choice == "4":
                await self._manual_select()

            elif choice == "5":
                return

    async def _manual_select(self):
        valid_earfcn = self.workflow.config["valid_earfcn"]
        selected = int(Prompt.ask("Enter EARFCN", choices=[str(e) for e in valid_earfcn]))
        await self.workflow.set_earfcn(selected)