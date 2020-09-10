# Lint as: python3
"""Functions to convert strings between different case styles."""
import re


def SnakeToCamel(snake_str: str) -> str:
  """Convert a string in snake_case to lowerCamelCase."""
  if not snake_str:
    return snake_str

  snake_components = snake_str.split("_")
  lower_camel_str = (
    f"{snake_components[0][:1].lower() + snake_components[0][1:]}"
    f"{''.join([comp.capitalize() for comp in snake_components[1:]])}"
  )

  return lower_camel_str


def CamelToSnake(lower_camel_str: str) -> str:
  """Convert a string in lowerCamelCase to snake_case."""
  if not lower_camel_str:
    return lower_camel_str

  return re.sub("([A-Z])", "_\\1", lower_camel_str).lower()
