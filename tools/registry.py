"""
Tool Registry — système de décorateur @register_tool.

Permet de définir un outil une seule fois (sur sa fonction) et de générer
automatiquement :
  1. Le schéma JSON pour l'API OpenAI/DeepSeek (AGENT_TOOLS)
  2. Le dictionnaire de dispatch nom → fonction (FUNCTION_MAP)
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, get_type_hints


class ToolRegistry:
    """Registre global des outils disponibles pour l'agent."""

    def __init__(self):
        self._tools: Dict[str, dict] = {}  # name → {func, schema, ...}

    def register(
        self,
        name: str,
        description: str,
        params: Optional[Dict[str, str]] = None,
        optional_params: Optional[Dict[str, str]] = None,
    ):
        """
        Décorateur pour enregistrer une fonction comme outil.

        Args:
            name: Nom unique de l'outil (ex: "mouse_click").
            description: Description complète envoyée au LLM.
            params: Dictionnaire {nom_param: description} des paramètres REQUIS.
            optional_params: Dictionnaire {nom_param: description} des paramètres OPTIONNELS.
        """

        def decorator(func: Callable) -> Callable:
            # --- Construire le schéma JSON OpenAI ---
            properties = {}
            required = []

            # Paramètres requis
            if params:
                for pname, pdesc in (params or {}).items():
                    properties[pname] = self._infer_schema(pname, pdesc, func, required=True)
                    required.append(pname)

            # Paramètres optionnels
            if optional_params:
                for pname, pdesc in (optional_params or {}).items():
                    properties[pname] = self._infer_schema(pname, pdesc, func, required=False)

            tool_schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }

            self._tools[name] = {
                "func": func,
                "schema": tool_schema,
            }
            return func

        return decorator

    def _infer_schema(
        self,
        pname: str,
        pdesc: str,
        func: Callable,
        required: bool = True,
    ) -> dict:
        """
        Infère le schéma JSON d'un paramètre à partir de son type hint Python.
        """
        hints = get_type_hints(func)
        py_type = hints.get(pname, str)

        type_map = {
            int: "integer",
            float: "number",
            str: "string",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        json_type = type_map.get(py_type, "string")

        # Détecter si une valeur par défaut existe (param optionnel)
        sig = inspect.signature(func)
        if pname in sig.parameters:
            param = sig.parameters[pname]
            if param.default is not inspect.Parameter.empty:
                # C'est un paramètre avec valeur par défaut
                pass  # déjà marqué optionnel via optional_params

        schema: dict = {
            "type": json_type,
            "description": pdesc,
        }

        # Si le type est list, ajouter items
        if json_type == "array":
            schema["items"] = {"type": "string"}

        return schema

    def get_definitions(self) -> List[dict]:
        """
        Retourne la liste complète des définitions d'outils au format OpenAI.
        → Remplace AGENT_TOOLS.
        """
        return [t["schema"] for t in self._tools.values()]

    def get_function_map(self) -> Dict[str, Callable]:
        """
        Retourne le dictionnaire de dispatch nom → fonction.
        → Remplace FUNCTION_MAP.
        """
        return {name: t["func"] for name, t in self._tools.items()}

    def get_tool_names(self) -> List[str]:
        """Retourne la liste des noms d'outils disponibles."""
        return list(self._tools.keys())

    def __len__(self):
        return len(self._tools)

    def __repr__(self):
        return f"<ToolRegistry: {len(self._tools)} tools>"


# --- Instance globale ---
TOOL_REGISTRY = ToolRegistry()


# --- Décorateur public ---
def register_tool(
    name: str,
    description: str,
    params: Optional[Dict[str, str]] = None,
    optional_params: Optional[Dict[str, str]] = None,
    **kwargs,
):
    """Alias pratique vers TOOL_REGISTRY.register()."""
    return TOOL_REGISTRY.register(
        name=name,
        description=description,
        params=params,
        optional_params=optional_params,
    )
