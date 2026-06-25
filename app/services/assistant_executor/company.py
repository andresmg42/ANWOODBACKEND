from typing import Any

from ..company_info import get_company_info
from ._base import ExecutorBase


class CompanyHandler(ExecutorBase):
    def informacion_empresa(self, tema: str | None = None) -> dict[str, Any]:
        return get_company_info(self.db, tema)
