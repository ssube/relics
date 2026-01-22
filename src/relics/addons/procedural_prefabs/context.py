"""Generation context for procedural prefabs."""

import re
from copy import deepcopy
from typing import Any, Dict, List, Optional


class GenerationContext:
    """Context for procedural prefab generation.

    Manages parameters (inherited, read-only) and derived values
    (accumulated, mutable) during entity generation.

    Attributes:
        params: Read-only parameters passed to this generation.
        derived: Mutable derived values accumulated during generation.
    """

    # Pattern to match @param_name references
    PARAM_PATTERN = re.compile(r"@(\w+)")

    def __init__(
        self,
        params: Optional[Dict[str, Any]] = None,
        derived: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize generation context.

        Args:
            params: Initial parameters (will be copied).
            derived: Initial derived values (will be copied).
        """
        self._params: Dict[str, Any] = dict(params) if params else {}
        self._derived: Dict[str, Any] = dict(derived) if derived else {}

    @property
    def params(self) -> Dict[str, Any]:
        """Read-only view of parameters."""
        return dict(self._params)

    @property
    def derived(self) -> Dict[str, Any]:
        """Read-only view of derived values."""
        return dict(self._derived)

    def get_param(self, name: str, default: Any = None) -> Any:
        """Get a parameter value.

        Args:
            name: Parameter name.
            default: Default value if not found.

        Returns:
            Parameter value or default.
        """
        return self._params.get(name, default)

    def get_derived(self, name: str, default: Any = None) -> Any:
        """Get a derived value.

        Args:
            name: Derived value name.
            default: Default value if not found.

        Returns:
            Derived value or default.
        """
        return self._derived.get(name, default)

    def set_derived(self, name: str, value: Any) -> None:
        """Set a derived value.

        Args:
            name: Derived value name.
            value: Value to set.
        """
        self._derived[name] = value

    def add_derived(self, name: str, value: Any) -> None:
        """Add to a derived numeric value.

        Args:
            name: Derived value name.
            value: Value to add.

        Raises:
            TypeError: If current value is not numeric.
        """
        current = self._derived.get(name, 0)
        if not isinstance(current, (int, float)) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Cannot add to non-numeric value: {name}={current}, adding {value}"
            )
        self._derived[name] = current + value

    def multiply_derived(self, name: str, value: Any) -> None:
        """Multiply a derived numeric value.

        Args:
            name: Derived value name.
            value: Multiplier value.

        Raises:
            TypeError: If current value is not numeric.
        """
        current = self._derived.get(name, 1)
        if not isinstance(current, (int, float)) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Cannot multiply non-numeric: {name}={current}, by {value}"
            )
        self._derived[name] = current * value

    def append_derived(self, name: str, value: Any) -> None:
        """Append to a derived list value.

        Args:
            name: Derived value name.
            value: Value to append.
        """
        current = self._derived.get(name)
        if current is None:
            self._derived[name] = [value]
        elif isinstance(current, list):
            self._derived[name] = current + [value]
        else:
            raise TypeError(f"Cannot append to non-list value: {name}={current}")

    def resolve_value(self, value: Any) -> Any:
        """Resolve @param references in a value.

        Handles strings with @param_name patterns, replacing them
        with actual parameter or derived values.

        Args:
            value: Value to resolve (may be string, dict, list, etc.).

        Returns:
            Resolved value with all @param references substituted.
        """
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve_value(v) for v in value]
        return value

    def _resolve_string(self, value: str) -> Any:
        """Resolve @param references in a string.

        If the entire string is a single @param reference, returns
        the actual value (preserving type). Otherwise performs
        string substitution.

        Args:
            value: String to resolve.

        Returns:
            Resolved value.
        """
        # Check if entire string is a single @param reference
        full_match = self.PARAM_PATTERN.fullmatch(value)
        if full_match:
            param_name = full_match.group(1)
            return self._get_value(param_name)

        # Otherwise, do string substitution
        def replacer(m: re.Match) -> str:
            param_name = m.group(1)
            resolved = self._get_value(param_name)
            return str(resolved) if resolved is not None else m.group(0)

        return self.PARAM_PATTERN.sub(replacer, value)

    def _get_value(self, name: str) -> Any:
        """Get a value from params or derived.

        Derived values take precedence over params.

        Args:
            name: Value name.

        Returns:
            Value or None if not found.
        """
        if name in self._derived:
            return self._derived[name]
        return self._params.get(name)

    def get_all_values(self) -> Dict[str, Any]:
        """Get merged params and derived values for matching.

        Derived values take precedence over params.

        Returns:
            Merged dictionary of all values.
        """
        result = dict(self._params)
        result.update(self._derived)
        return result

    def child_context(
        self,
        inherit_params: Optional[List[str]] = None,
        override_params: Optional[Dict[str, Any]] = None,
    ) -> "GenerationContext":
        """Create a child context with param inheritance.

        Args:
            inherit_params: List of param names to inherit (None = inherit all).
            override_params: Additional params to override/add.

        Returns:
            New GenerationContext for child generation.
        """
        if inherit_params is None:
            # Inherit all params and derived
            new_params = dict(self._params)
            new_params.update(self._derived)
        else:
            # Inherit only specified params
            new_params = {}
            all_values = self.get_all_values()
            for name in inherit_params:
                if name in all_values:
                    new_params[name] = all_values[name]

        # Apply overrides (resolve @param references)
        if override_params:
            for key, value in override_params.items():
                new_params[key] = self.resolve_value(value)

        return GenerationContext(params=new_params)

    def copy(self) -> "GenerationContext":
        """Create a deep copy of this context.

        Returns:
            New GenerationContext with copied data.
        """
        return GenerationContext(
            params=deepcopy(self._params),
            derived=deepcopy(self._derived),
        )
