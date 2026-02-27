import ipaddress
import os
import sys
import ping3
from rich import print
import json

class Helper():
    def __init__(self):
        pass

    def check_ping(self, ip: str, timeout: int = 3) -> float:
        try:
            ipaddress.ip_address(ip)
            delays_ms = []
            for _ in range(3):
                delay_sec = ping3.ping(ip, timeout=timeout)
                if delay_sec is None or delay_sec is False:
                    return -1
                delays_ms.append(delay_sec * 1000)
            return sum(delays_ms) / len(delays_ms)
        except Exception:
            return -1
        
    async def wait_for_internet(self, ip: str, timeout: int = 30):
        for _ in range(timeout):
            if ping3.ping(ip, timeout=1) is not None:
                return True
        return False
    
    def load_json(self,filename: str):
        try:
            with open(filename, 'r') as file:
                return json.load(file)

        except FileNotFoundError:
            print(f"[red][-] File not found: '[bold]{filename}[/bold]'[/red]")
            return None

        except json.JSONDecodeError:
            print(f"[red][-] File '[bold]{filename}[/bold]' contains invalid JSON.[/red]")
            return None

        except Exception as e:
            print(f"[red][-] An unexpected error occurred:[/red] {e}")
            return None
    
    def resource_path(self, relative_path):
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        return os.path.join(base_path, relative_path)