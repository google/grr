const BASES: Array<[string, string, number]> = [
  ['P', 'peta', 1000 ** 5],
  ['Pi', 'pebi', 1024 ** 5],
  ['T', 'tera', 1000 ** 4],
  ['Ti', 'tebi', 1024 ** 4],
  ['G', 'giga', 1000 ** 3],
  ['Gi', 'gibi', 1024 ** 3],
  ['M', 'mega', 1000 ** 2],
  ['Mi', 'mebi', 1024 ** 2],
  ['k', 'kilo', 1000],
  ['Ki', 'kibi', 1024],
  ['', '', 1],
];

/** Parses a string like '1 KiB' into the raw number of bytes, e.g. 1024. */
export function parseByteString(input: string): number {
  const matches = input
    .trim()
    .toLowerCase()
    .match(/^(\d+) *([kmgtp]i?)?b?$/);
  if (!matches) {
    throw new Error(`Invalid byte input "${input}".`);
  }

  const [, inputBytesString, inputPrefix] = matches;
  let inputBase = undefined;
  const inputByteNumber = Number(inputBytesString);

  if (inputPrefix === undefined) {
    return inputByteNumber;
  }

  for (const [curPrefix, , curBase] of BASES) {
    if (inputPrefix === curPrefix.toLowerCase()) {
      inputBase = curBase;
      break;
    }
  }

  if (!inputBase) {
    throw new Error(`Invalid base ${inputPrefix} for byte input "${input}".`);
  }

  return inputByteNumber * inputBase;
}

/**
 * Determines the largest possible unit that fits the given number of bytes,
 * e.g. 2048 results in [2, 'KiB'].
 * @param mode use 'short' to get symbols (KiB) and 'long' for long unit names
 *   (kibibytes).
 */
export function toByteUnit(
  bytes: number,
  mode: 'short' | 'long' = 'short',
): [number, string] {
  if (bytes === 0) {
    return [bytes, getByteSuffix(0, '', mode)];
  }

  for (const [shortPrefix, longPrefix, base] of BASES) {
    if (bytes % base === 0) {
      const prefix = mode === 'long' ? longPrefix : shortPrefix;
      const bytesAtBase = bytes / base;
      return [bytesAtBase, getByteSuffix(bytesAtBase, prefix, mode)];
    }
  }

  return [bytes, getByteSuffix(bytes, '', mode)];
}

/**
 * Renders `bytes` as byte string with the largest possible unit, e.g. 2048
 * results in '2 KiB'.
 * @param mode use 'short' to get symbols (KiB) and 'long' for long unit names
 *   (kibibytes).
 */
export function toByteString(bytes: number, mode: 'short' | 'long' = 'short') {
  const [bytesAtUnit, unit] = toByteUnit(bytes, mode);
  return `${bytesAtUnit} ${unit}`;
}

function getByteSuffix(
  bytes: number,
  prefix: string,
  mode: 'short' | 'long' = 'short',
) {
  if (mode === 'short') {
    return `${prefix}B`;
  } else if (bytes === 1) {
    return `${prefix}byte`;
  } else {
    return `${prefix}bytes`;
  }
}
