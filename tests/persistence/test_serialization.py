"""Tests for persistence serialization helpers."""

from pydantic import BaseModel

from relics import Component
from relics.persistence.serialization import _component_to_dict, _dict_to_component


class PydanticV2Component(BaseModel, Component):
    """Test component using Pydantic v2 BaseModel (not dataclass)."""

    name: str
    value: int
    _private: str = "hidden"


class PlainComponent(Component):
    """Test component using plain class (no dataclass decorator)."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self._internal = "private"


class ModelFieldsOnlyComponent(Component):
    """Test component with only model_fields attribute (no __pydantic_fields__).

    This simulates an older Pydantic-style or custom class that only has model_fields.
    """

    model_fields = {"name": None, "value": None}  # Class attribute

    def __init__(self, name: str, value: int):
        self.name = name
        self.value = value
        self._private = "hidden"


class TestComponentToDict:
    """Tests for _component_to_dict serialization."""

    def test_pydantic_v2_basemodel_with_pydantic_fields(self) -> None:
        """Test serialization of Pydantic v2 BaseModel components.

        Note: Modern Pydantic v2 models have __pydantic_fields__ which is checked
        before model_fields in the serialization code.
        """
        component = PydanticV2Component(name="test", value=42)

        result = _component_to_dict(component)

        assert result == {"name": "test", "value": 42}
        assert "_private" not in result

    def test_model_fields_only_component(self) -> None:
        """Test serialization using model_fields attribute (no __pydantic_fields__).

        This tests the model_fields code path for custom classes that only
        have model_fields defined (not __dataclass_fields__ or __pydantic_fields__).
        """
        component = ModelFieldsOnlyComponent(name="test", value=99)

        # Verify it doesn't have the other attributes that would be checked first
        assert not hasattr(component, "__dataclass_fields__")
        assert not hasattr(component, "__pydantic_fields__")
        assert hasattr(component, "model_fields")

        result = _component_to_dict(component)

        assert result == {"name": "test", "value": 99}
        assert "_private" not in result

    def test_plain_class_with_dict(self) -> None:
        """Test serialization of plain class components using __dict__."""
        component = PlainComponent(x=1.5, y=2.5)

        result = _component_to_dict(component)

        assert result == {"x": 1.5, "y": 2.5}
        assert "_internal" not in result


class TestDictToComponent:
    """Tests for _dict_to_component deserialization."""

    def test_pydantic_v2_basemodel_deserialization(self) -> None:
        """Test deserialization to Pydantic v2 BaseModel."""
        data = {"name": "loaded", "value": 99}

        result = _dict_to_component(PydanticV2Component, data)

        assert isinstance(result, PydanticV2Component)
        assert result.name == "loaded"
        assert result.value == 99
