"""Pagination helpers shared by repositories."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageRequest:
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            object.__setattr__(self, "page", 1)
        if self.page_size < 1:
            object.__setattr__(self, "page_size", 20)
        if self.page_size > 100:
            object.__setattr__(self, "page_size", 100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
