# Zitel Optimizer

This project scans all valid frequencies, checks the bandwidth of each, and finally recommends the best frequency to you.

> [!WARNING]
> There is no guarantee of increased bandwidth. This script simply checks the different frequency bands and checks the bandwidth of each and finally based on your decision you can either manually select one of the frequencies or let the script automatically lock the fastest frequency on the modem.

## Quick Start

If you're using Windows OS, you can use executable file available in [release section](https://github.com/nimazerobit/zitel-optimizer/releases). Also, if your operating system is not Windows or you want to run from source code, you can use [this section](#how-to-run-from-source).

1. Download **zitel optimizer** executable from <a href="https://github.com/nimazerobit/zitel-optimizer/releases">release section</a>.
2. Open **CMD** or **PowerShell** then run executable. (You can also use the script by double-clicking it, but it is not recommended.)
3. Follow instructions in script.

> [!NOTE]
> You can also use the script by double-clicking it, but it is not recommended.

## How to run from source?

> [!TIP]
> Before proceeding, make sure you have Python installed on your computer. You can download Python from its official website via [python.org](https://www.python.org/downloads/).

1. Clone from repository
```bash
git clone https://github.com/nimazerobit/zitel-optimizer
cd zitel-optimizer
```
2. Install required packages
```bash
pip install -r requirements.txt
```
3. If necessary, change the config file [(How to?)](#how-to-modify-configjson-file)
4. RUN [(Available arguments here)](#arguments)
```bash
python main.py
```

## How to Modify config.json file?

```json
{
    "modem_ip": "192.168.0.254",            // Your Zi-Tel modem IP
    "username": "farabord",                 // MOST OF THE TIME THERE IS NO NEED TO CHANGE THIS
    "password": "farabord",                 // MOST OF THE TIME THERE IS NO NEED TO CHANGE THIS
    "valid_earfcn": [42490, 42690, 42890],  // DON'T TOUCH THIS
    "ping_check_ip": "8.8.8.8",             // IP used to check internet connectivity
    "speedtest_cli_path": "speedtest.exe"   // Path to SpeedTest CLI
}
```

## Arguments

| Argument  | Description |
| :-------------- | :------------- |
| `-y` or `--yes` | Use yes as default answer to prompts |
| `--info` | Just show Cell Info |

> I know they are few :)

## Watch on YouTube
<a href="https://www.youtube.com/watch?v=VnXP6QOyI80"><img src="https://i.ytimg.com/vi_webp/VnXP6QOyI80/maxresdefault.webp" alt="Buy Me A Coffee" style="border-radius: 20px;"/></a>

## Donate ❤️
<a href="https://daramet.com/nimazerobit"><img src="https://panel.daramet.com/static/media/daramet-coffee-donate.91915073278a21c30769.png" alt="Buy Me A Coffee" style="height: 60px !important;"/></a>
