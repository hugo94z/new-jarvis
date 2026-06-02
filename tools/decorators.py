"""
Decorators utilitaires pour les outils :
  - @safe_tool : capture les exceptions et retourne {"error": ...}
  - @cached : cache LRU avec TTL pour les appels coûteux
"""

import functools
import time
from typing import Any, Callable, Dict, Optional, Tuple


def safe_tool(func: Callable) -> Callable:
    """
    Décorateur qui englobe une fonction outil dans un try/except.

    En cas de succès, le résultat de la fonction est retourné tel quel.
    En cas d'erreur, retourne {"error": message, "exception": type_exception}.

    Usage:
        @safe_tool
        def mouse_click(x, y):
            pyautogui.click(x, y)
            return {"success": True}
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> dict:
        try:
            result = func(*args, **kwargs)
            # Si la fonction ne retourne rien, on crée un succès implicite
            if result is None:
                return {"success": True}
            # Si la fonction retourne déjà un dict, le laisser tel quel
            if isinstance(result, dict):
                return result
            # Sinon, encapsuler
            return {"success": True, "result": result}
        except Exception as e:
            # Capturer le vrai message (sans traceback)
            err_msg = str(e)
            if not err_msg:
                err_msg = f"{type(e).__name__}"
            return {
                "error": err_msg,
                "exception": type(e).__name__,
            }

    return wrapper


# --- Cache avec TTL ---

class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.time() + ttl

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


def cached(ttl: float = 300):
    """
    Décorateur de cache avec durée de vie (TTL en secondes).

    Le résultat de la fonction est mis en cache pour `ttl` secondes.
    Les appels suivants avec les mêmes arguments retournent le résultat
    mis en cache sans réexécuter la fonction.

    Args:
        ttl: Durée de vie du cache en secondes (défaut: 300 = 5 min).

    Usage:
        @cached(ttl=600)
        def get_weather(city):
            return requests.get(...).json()
    """

    def decorator(func: Callable) -> Callable:
        cache: Dict[Tuple, _CacheEntry] = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Construire une clé de cache à partir des arguments
            # Seuls les kwargs sont utilisés (les outils sont appelés avec **kwargs)
            if kwargs:
                key_parts = sorted(kwargs.items())
            else:
                key_parts = tuple(args) if args else ()
            key = (func.__name__,) + tuple(key_parts)

            # Vérifier le cache
            entry = cache.get(key)
            if entry is not None and not entry.is_expired:
                return entry.value

            # Exécuter la fonction et mettre en cache
            result = func(*args, **kwargs)
            cache[key] = _CacheEntry(result, ttl)

            # Nettoyer les entrées expirées (paresseux, nettoyage léger)
            if len(cache) > 200:
                expired_keys = [
                    k for k, e in cache.items() if e.is_expired
                ]
                for k in expired_keys:
                    del cache[k]

            return result

        return wrapper

    return decorator