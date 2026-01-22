"""Core data classes for procedural prefabs."""

from typing import Any, Dict, List, Optional, Type

import pydantic.dataclasses


@pydantic.dataclasses.dataclass
class ParamDefinition:
    """Definition of a parameter for a procedural prefab.

    Attributes:
        name: Parameter name (used with @name syntax).
        param_type: Type name for validation (str, int, float, bool, list).
        required: Whether the parameter must be provided.
        default: Default value if not provided.
        allowed_values: If set, parameter must be one of these values.
    """

    name: str
    param_type: str = "any"
    required: bool = False
    default: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None

    def validate_value(self, value: Any) -> bool:
        """Check if a value satisfies this parameter's constraints.

        Args:
            value: Value to validate.

        Returns:
            True if valid.

        Raises:
            ValueError: If validation fails.
        """
        if self.allowed_values is not None and value not in self.allowed_values:
            raise ValueError(
                f"Value '{value}' not in allowed values: {self.allowed_values}"
            )

        # "any" type accepts all values
        if self.param_type == "any":
            return True

        type_map: Dict[str, type] = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
        }

        expected_type = type_map.get(self.param_type)
        if expected_type:
            # Special case: int is valid for float
            if self.param_type == "float" and isinstance(value, int):
                return True
            if not isinstance(value, expected_type):
                raise ValueError(
                    f"Expected type '{self.param_type}', got '{type(value).__name__}'"
                )

        return True


@pydantic.dataclasses.dataclass
class WhenClause:
    """Condition for matching based on parameter values.

    Uses exact-match semantics: all conditions must match.

    Attributes:
        conditions: Dictionary of param_name -> expected_value.
    """

    conditions: Dict[str, Any]


@pydantic.dataclasses.dataclass
class ComponentVariant:
    """A component with optional conditional when clause.

    Attributes:
        component_type: Name of the component type.
        fields: Field values for the component.
        when: Optional condition for this variant.
    """

    component_type: str
    fields: Dict[str, Any]
    when: Optional[WhenClause] = None


@pydantic.dataclasses.dataclass
class DeriveOperation:
    """Operation to derive a new value in the context.

    Attributes:
        target: Name of the derived value to set/modify.
        operation: Operation type (set, add, multiply, append).
        value: Value for the operation (can use @param references).
    """

    target: str
    operation: str
    value: Any

    def __post_init__(self) -> None:
        """Validate operation type."""
        valid_ops = {"set", "add", "multiply", "append"}
        if self.operation not in valid_ops:
            raise ValueError(
                f"Invalid operation '{self.operation}', must be one of: {valid_ops}"
            )


@pydantic.dataclasses.dataclass
class AddOperation:
    """Operation to add a component conditionally.

    Attributes:
        component_type: Name of the component type to add.
        fields: Field values for the component.
    """

    component_type: str
    fields: Dict[str, Any]


@pydantic.dataclasses.dataclass
class ConditionalBlock:
    """A block of operations that execute when conditions match.

    Attributes:
        when: Condition for this block.
        add: Components to add if condition matches.
        derive: Values to derive if condition matches.
    """

    when: WhenClause
    add: List[AddOperation]
    derive: List[DeriveOperation]


@pydantic.dataclasses.dataclass
class AttachmentDefinition:
    """Definition of a child entity attachment.

    Attributes:
        prefab: Static prefab name to spawn (mutually exclusive with from_list).
        from_list: List name to select from (mutually exclusive with prefab).
        edge_type: Type of edge relationship (HasEquipped, IsWearing, HasAttached).
        slot: Slot name for the attachment.
        inherit_params: Parameters to inherit from parent context.
        override_params: Parameters to override for child context.
        optional: Whether this attachment can be skipped.
        skip: Static skip flag.
    """

    prefab: Optional[str] = None
    from_list: Optional[str] = None
    edge_type: str = "HasAttached"
    slot: str = "default"
    inherit_params: Optional[List[str]] = None
    override_params: Optional[Dict[str, Any]] = None
    optional: bool = False
    skip: bool = False

    def __post_init__(self) -> None:
        """Validate attachment definition."""
        if not self.prefab and not self.from_list and not self.skip:
            raise ValueError(
                "AttachmentDefinition must have 'prefab', 'from_list', or 'skip'"
            )
        if self.prefab and self.from_list:
            raise ValueError(
                "AttachmentDefinition cannot have both 'prefab' and 'from_list'"
            )


@pydantic.dataclasses.dataclass
class GraphDefinition:
    """Definition of the entity graph structure.

    Attributes:
        components: List of component variants for the main entity.
        conditionals: List of conditional blocks.
        attachments: List of attachment definitions for child entities.
        lists: Named lists of prefab names for attachment selection.
    """

    components: List[ComponentVariant]
    conditionals: Optional[List[ConditionalBlock]] = None
    attachments: Optional[List[AttachmentDefinition]] = None
    lists: Optional[Dict[str, List[str]]] = None


@pydantic.dataclasses.dataclass
class ProceduralPrefab:
    """A procedural prefab definition.

    Attributes:
        name: Unique name for this prefab.
        params: Parameter definitions.
        graph: The entity graph definition.
        base_prefab: Optional base prefab to inherit from.
    """

    name: str
    params: List[ParamDefinition]
    graph: GraphDefinition
    base_prefab: Optional[str] = None

    def get_param(self, name: str) -> Optional[ParamDefinition]:
        """Get a parameter definition by name.

        Args:
            name: Parameter name.

        Returns:
            ParamDefinition or None if not found.
        """
        for p in self.params:
            if p.name == name:
                return p
        return None

    def get_required_params(self) -> List[ParamDefinition]:
        """Get all required parameters.

        Returns:
            List of required ParamDefinitions.
        """
        return [p for p in self.params if p.required]


# Type alias for component registry
ComponentRegistry = Dict[str, Type[Any]]
