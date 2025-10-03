"""
Repository Pattern Implementation for Telbooru

This package provides abstract repository interfaces and concrete implementations
for data access, following the Repository Pattern to decouple business logic
from data access concerns.
"""

from .interfaces import (
    IBooruRepository,
    IUserRepository,
    ISearchRepository
)

from .booru_repository import BooruRepository
from .user_repository import UserRepository
from .search_repository import SearchRepository

__all__ = [
    'IBooruRepository',
    'IUserRepository',
    'ISearchRepository',
    'BooruRepository',
    'UserRepository',
    'SearchRepository'
]