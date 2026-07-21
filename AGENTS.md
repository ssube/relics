# Agentic Developer Guide

## Compiler-visible types

Do not introduce Python `typing.Any` or TypeScript `any`. If either appears in
code you are changing, replace it with a type that states the actual contract:
a named model, protocol, generic parameter, discriminated union, `object` plus
explicit narrowing, or a recursive JSON value type. Do not hide an unknown
shape behind casts or type-ignore comments.

Use `dict[K, V]` when callers require a concrete mutable dictionary. A
`Mapping[K, V]` may be read-only or implemented by a custom object, so it is
not an interchangeable spelling of `dict[K, V]`.

If you cannot explain a value to the compiler, the behavior will not be
reliable enough to maintain.
