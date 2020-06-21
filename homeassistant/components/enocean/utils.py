"""Utility methods for common ENOcean operation."""
from typing import List


def enocean_id_to_string(identifier: List[int]) -> str:
    """Return a decodable string representation of an ENOcean identifier."""
    return ":".join([f"{val:02X}" for val in identifier])
