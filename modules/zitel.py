import hashlib
import random
import time
import requests
from typing import Dict, Optional, Any

class Zitel:
    def __init__(self, address: str, command_codes: Dict[str, int]):
        self._address = address
        self._codes = command_codes
        self._session = requests.Session()
        self._session.trust_env = False
        self._session.proxies = {}
        
        referer = address.split("/cgi-bin")[0] + "/"
        self._session.headers.update({
            "Content-Type": "application/json",
            "Referer": referer
        })

    def _generate_session_id(self) -> str:
        # Generates a random SHA256 hash for the session ID
        random_number = str(random.randint(0, 2147483647)) # max int32
        return self._generate_sha256(random_number)

    def _generate_sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode('utf-8')).hexdigest().lower()

    def _generate_md5(self, value: str) -> str:
        return hashlib.md5(value.encode('utf-8')).hexdigest().lower()

    def _build_payload(self, cmd: int, method: str, session_id: str = "", **kwargs) -> Dict[str, Any]:
        payload = {
            "cmd": int(cmd),
            "method": method,
            "sessionId": session_id,
            "language": "EN"
        }
        payload.update(kwargs)
        return payload

    def _post_request(self, payload: Dict[str, Any], retries: int = 3) -> Dict[str, Any]:
        for attempt in range(retries):
            try:
                response = self._session.post(self._address, json=payload, timeout=10)
                response.raise_for_status()
               
                if not response.text.strip():
                    if attempt < retries - 1:
                        time.sleep(1)
                        continue
                    raise ValueError("No response from modem")
                
                return response.json()
            except (requests.exceptions.JSONDecodeError, ValueError):
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                raise ValueError("No response from modem")
            except Exception:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                raise

    def get_salt(self) -> str:
        payload = self._build_payload(self._codes["CREATE_RANDOM_SALT"], "GET")
        response = self._post_request(payload)
        return response.get("message", response.get("Message", ""))

    def login(self, username: str, password: str) -> str:
        session_id = self._generate_session_id()
        salt = self.get_salt()

        hashed_password = self._generate_sha256(salt + self._generate_md5(password))

        payload = self._build_payload(
            self._codes["LOGIN"],
            "POST",
            session_id,
            username=username,
            passwd=hashed_password
        )

        response = self._post_request(payload)

        if response.get("success", response.get("Success", False)):
            return response.get("sessionId", response.get("SessionId", session_id))

        raise PermissionError(f"Authentication failed: {response}")

    def set_earfcn(self, earfcn: int, cell_id: int, session_id: str) -> bool:
        payload = self._build_payload(
            self._codes["LOCK_ONE_CELL"],
            "POST",
            session_id,
            freqPoint=earfcn,
            phyCellId=cell_id,
            lockedStatus=1
        )
        response = self._post_request(payload)
        return response.get("success", response.get("Success", False))

    def get_lte_status(self, session_id: str) -> Dict[str, str]:
        payload = self._build_payload(self._codes["GET_LTE_STATUS"], "POST", session_id)
        response = self._post_request(payload)
       
        final_result = {}
        message = response.get("message", response.get("Message", ""))
        if message:
            items = message.split('$')
            for item in items:
                if '@' in item:
                    parts = item.split('@')
                    if len(parts) >= 2:
                        key = parts[0]
                        value = parts[1]
                        final_result[key] = value
       
        return final_result

    def get_current_cell_info(self, session_id: str) -> Dict[str, Any]:
        payload = self._build_payload(self._codes["LOCK_ONE_CELL"], "QUERY", session_id)
        response = self._post_request(payload)
       
        freq_point = response.get("freqPoint", response.get("FreqPoint"))
        phy_cell_id = response.get("phyCellId", response.get("PhyCellId"))
        locked_status = response.get("lockedStatus", response.get("LockedStatus"))

        if locked_status == "0" or str(locked_status) == "0":
            lte_status = self.get_lte_status(session_id)
            freq_point = lte_status.get("EARFCN/ARFCN", "0")
            phy_cell_id = lte_status.get("Physical CellID", "0")

        return {
            "earfcn": int(freq_point) if freq_point else 0,
            "cell_id": int(phy_cell_id) if phy_cell_id else 0,
            "locked": (str(locked_status) == "1")
        }