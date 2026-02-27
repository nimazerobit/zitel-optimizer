import hashlib
import random
import requests
from dataclasses import dataclass
from typing import Dict, Optional, Any

# Request Models

@dataclass
class ZitelRequest():
    cmd: int
    method: str
    session_id: str = ""
    language: str = "EN"

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "cmd": int(self.cmd),
            "method": self.method
        }
        if self.session_id or self.session_id == "":
            payload["sessionId"] = self.session_id
        if self.language:
            payload["language"] = self.language

        # optional fields for subclasses
        if hasattr(self, "username"):
            payload["username"] = getattr(self, "username")
        if hasattr(self, "passwd"):
            payload["passwd"] = getattr(self, "passwd")
        if hasattr(self, "freq_point"):
            payload["freqPoint"] = getattr(self, "freq_point")
        if hasattr(self, "phy_cell_id"):
            payload["phyCellId"] = getattr(self, "phy_cell_id")
        if hasattr(self, "locked_status"):
            payload["lockedStatus"] = getattr(self, "locked_status")

        return payload

@dataclass
class LoginRequest(ZitelRequest):
    username: str = ""
    passwd: str = ""

    def __init__(self, cmd: int, username: str, password: str, session_id: str):
        self.cmd = int(cmd)
        self.method = "POST"
        self.session_id = session_id
        self.language = "EN"
        self.username = username
        self.passwd = password

@dataclass
class SetEARFCNRequest(ZitelRequest):
    freq_point: int = 0
    phy_cell_id: int = 0
    locked_status: int = 1

    def __init__(self, cmd: int, earfcn: int, cell_id: int, session_id: str):
        self.cmd = int(cmd)
        self.method = "POST"
        self.session_id = session_id
        self.language = "EN"
        self.freq_point = earfcn
        self.phy_cell_id = cell_id
        self.locked_status = 1

# Response Models

@dataclass
class CellInfo:
    earfcn: int
    cell_id: int
    locked: bool

@dataclass
class ZitelResponse:
    success: bool = False
    message: str = ""
    session_id: str = ""
    freq_point: Optional[str] = None
    phy_cell_id: Optional[str] = None
    locked_status: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        mapping = {
            "success": "success",
            "message": "message",
            "sessionId": "session_id",
            "freqPoint": "freq_point",
            "phyCellId": "phy_cell_id",
            "lockedStatus": "locked_status"
        }
        
        # Build kwargs based on what's in the data
        kwargs = {}
        for api_key, py_key in mapping.items():
            if api_key in data:
                kwargs[py_key] = data[api_key]
            elif api_key[0].upper() + api_key[1:] in data:
                kwargs[py_key] = data[api_key[0].upper() + api_key[1:]]

        return cls(**kwargs)

class Zitel:
    def __init__(self, address: str, command_codes: Dict[str, int]):
        self._address = address
        self._codes = command_codes
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def _generate_session_id(self) -> str:
        # Generates a random SHA256 hash for the session ID
        random_number = str(random.randint(0, 2147483647)) # max int32
        return self._generate_sha256(random_number)

    def _generate_sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode('utf-8')).hexdigest().lower()

    def _generate_md5(self, value: str) -> str:
        return hashlib.md5(value.encode('utf-8')).hexdigest().lower()

    def _post_request(self, request_obj: ZitelRequest) -> ZitelResponse:
        payload = request_obj.to_dict()
        try:
            response = self._session.post(self._address, json=payload, timeout=10)
            response.raise_for_status()
            
            if not response.text.strip():
                raise ValueError("No response from modem")

            data = response.json()
            return ZitelResponse.from_dict(data)
        except requests.exceptions.JSONDecodeError:
            raise ValueError("JSON decoding failed")
        except Exception:
            raise

    def get_salt(self) -> str:
        req = ZitelRequest(cmd=int(self._codes["CREATE_RANDOM_SALT"]), method="GET")
        response = self._post_request(req)
        return response.message

    def login(self, username: str, password: str) -> str:
        session_id = self._generate_session_id()
        salt = self.get_salt()
        
        hashed_password = self._generate_sha256(salt + self._generate_md5(password))
        
        login_req = LoginRequest(int(self._codes["LOGIN"]), username, hashed_password, session_id)
        
        response = self._post_request(login_req)
        
        if response.success:
            return response.session_id
        
        raise PermissionError("Authentication failed")

    def set_earfcn(self, earfcn: int, cell_id: int, session_id: str) -> bool:
        req = SetEARFCNRequest(int(self._codes["LOCK_ONE_CELL"]), earfcn, cell_id, session_id)
        response = self._post_request(req)
        return response.success

    def get_lte_status(self, session_id: str) -> Dict[str, str]:
        req = ZitelRequest(
            cmd=int(self._codes["GET_LTE_STATUS"]),
            method="POST",
            session_id=session_id
        )
        response = self._post_request(req)
        
        final_result = {}
        if response.message:
            items = response.message.split('$')
            for item in items:
                if '@' in item:
                    parts = item.split('@')
                    if len(parts) >= 2:
                        key = parts[0]
                        value = parts[1]
                        final_result[key] = value
        
        return final_result

    def get_current_cell_info(self, session_id: str) -> CellInfo:
        req = ZitelRequest(
            cmd=int(self._codes["LOCK_ONE_CELL"]),
            method="QUERY",
            session_id=session_id
        )
        response = self._post_request(req)
        
        freq_point = response.freq_point
        phy_cell_id = response.phy_cell_id
        locked_status = response.locked_status

        if locked_status == "0":
            lte_status = self.get_lte_status(session_id)
            freq_point = lte_status.get("EARFCN/ARFCN", "0")
            phy_cell_id = lte_status.get("Physical CellID", "0")

        return CellInfo(
            earfcn=int(freq_point) if freq_point else 0,
            cell_id=int(phy_cell_id) if phy_cell_id else 0,
            locked=(locked_status == "1")
        )