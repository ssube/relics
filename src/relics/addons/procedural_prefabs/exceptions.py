"""Exception classes for the procedural prefabs addon."""


class ProceduralPrefabError(Exception):
    """Base exception for all procedural prefab errors."""

    pass


class ProcPrefabNotFoundError(ProceduralPrefabError):
    """Procedural prefab does not exist in registry."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Procedural prefab not found: {name}")


class ParamValidationError(ProceduralPrefabError):
    """Parameter validation failed."""

    def __init__(self, param_name: str, message: str) -> None:
        self.param_name = param_name
        super().__init__(f"Parameter '{param_name}' validation failed: {message}")


class PrefabListNotFoundError(ProceduralPrefabError):
    """Prefab list does not exist."""

    def __init__(self, list_name: str) -> None:
        self.list_name = list_name
        super().__init__(f"Prefab list not found: {list_name}")


class AttachmentSelectionError(ProceduralPrefabError):
    """Attachment selection failed."""

    def __init__(self, slot: str, message: str) -> None:
        self.slot = slot
        super().__init__(f"Attachment selection failed for slot '{slot}': {message}")


class CyclicAttachmentError(ProceduralPrefabError):
    """Cyclic attachment detected during spawning."""

    def __init__(self, prefab_chain: list) -> None:
        self.prefab_chain = prefab_chain
        chain_str = " -> ".join(prefab_chain)
        super().__init__(f"Cyclic attachment detected: {chain_str}")
