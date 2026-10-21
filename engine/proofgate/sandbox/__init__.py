"""Isolated execution of a reporter's own reproduction steps. ProofGate never writes exploits."""

from .base import Sandbox, get_sandbox
from .sanitizer import parse_sanitizer

__all__ = ["Sandbox", "get_sandbox", "parse_sanitizer"]
