import json
from dataclasses import dataclass
from typing import List
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AccountConfig:
    name: str
    credentials_path: str


class AccountManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.accounts: List[AccountConfig] = []
        self._load_config()

    def _load_config(self) -> None:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.accounts = [
                    AccountConfig(**account)
                    for account in config.get('accounts', [])
                ]
        except Exception as e:
            logger.error(f"Failed to load account config: {e}")
            raise
