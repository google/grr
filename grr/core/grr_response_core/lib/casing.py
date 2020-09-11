# Lint as: python3
"""Functions to convert strings between different case styles."""


def SnakeToCamel(snake_str: str) -> str:
  """Convert a snake_case string representing one identifier to lowerCamelCase.

  The function uses a best-effort approach to convert the given string to a
  valid lowerCamelCase string, meaning that it converts even strings that use
  multiple consecutive underscores between words and/or that start/end with an
  underscore.

  Args:
    snake_str: A snake_case string representing a single identifier.

  Returns:
    A lowerCamelCase representation of the given string.
  """
  # Extract the words from the snake_case string.
  words = list(filter(lambda word: len(word) > 0, snake_str.split("_")))
  if not words:
    return ""

  words[:] = map(str.lower, words)

  lower_camel_str = words[0] + ''.join(map(str.capitalize, words[1:]))

  return lower_camel_str


def CamelToSnake(lower_camel_str: str) -> str:
  """Convert a lowerCamelCase string representing one identifier to snake_case.

  The function uses a best-effort approach to convert the given string to a
  valid snake_case string, meaning that it converts even strings that start
  with a capital letter.

  Args:
    lower_camel_str: A lowerCamelCase string representing a single identifier.

  Returns:
    A snake_case representation of the given string.
  """
  camel_str_len = len(lower_camel_str)
  words = []
  i_word_start = 0

  for i_char in range(camel_str_len):
    if lower_camel_str[i_char].isupper():
      if i_word_start != i_char:  # Required for uppercase first letter case.
        words.append(lower_camel_str[i_word_start:i_char])
      i_word_start = i_char

  # Add the word at the end of the string, possibly the only word.
  words.append(lower_camel_str[i_word_start:camel_str_len])

  temp_snake_str = "_".join(map(str.lower, words))

  # Remove duplicate underscores, if any.
  snake_str_list = []
  prev_char = ""
  for char in temp_snake_str:
    if not char == prev_char == "_":
      snake_str_list.append(char)
    prev_char = char

  # Remove the underscore from the start/end, if any.
  if len(snake_str_list) > 0 and snake_str_list[0] == "_":
    snake_str_list.pop(0)
  if len(snake_str_list) > 0 and snake_str_list[-1] == "_":
    snake_str_list.pop()

  return "".join(snake_str_list)
