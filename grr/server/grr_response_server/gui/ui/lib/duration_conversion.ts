const BASES: Array<[string, string, number]> = [
  ['w', 'week', 60 * 60 * 24 * 7],
  ['d', 'day', 60 * 60 * 24],
  ['h', 'hour', 60 * 60],
  ['m', 'minute', 60],
  ['s', 'second', 1],
  ['', '', 1],
];

/** Parses a string like '1 h' into the raw number of seconds, e.g. 3600. */
export function parseDurationString(input: string): number {
  const matches = input
    .trim()
    .toLowerCase()
    .match(/^(\d+) *([smhdw])?$/);
  if (!matches) {
    throw new Error(`Invalid duration input "${input}".`);
  }

  const [, inputDurationString, inputPrefix] = matches;
  let inputBase = undefined;
  const inputDurationNumber = Number(inputDurationString);

  if (inputPrefix === undefined) {
    return inputDurationNumber;
  }

  for (const [curPrefix, , curBase] of BASES) {
    if (inputPrefix === curPrefix) {
      inputBase = curBase;
      break;
    }
  }

  if (!inputBase) {
    throw new Error(
      `Invalid base ${inputPrefix} for duration input "${input}".`,
    );
  }

  return inputDurationNumber * inputBase;
}

/**
 * Determines the largest possible unit that fits the given number of bytes,
 * e.g. 3600 results in [1, 'h'].
 * @param mode use 'short' to get symbols (h) and 'long' for long unit names
 *   (hours).
 */
export function toDurationUnit(
  duration: number,
  mode: 'short' | 'long' = 'short',
): [number, string] {
  if (duration === 0) {
    const prefix = mode === 'long' ? 'second' : 's';
    return [duration, getDurationSuffix(0, prefix, mode)];
  }

  for (const [shortPrefix, longPrefix, base] of BASES) {
    if (duration % base === 0) {
      const prefix = mode === 'long' ? longPrefix : shortPrefix;
      const durationAtBase = duration / base;
      return [durationAtBase, getDurationSuffix(durationAtBase, prefix, mode)];
    }
  }

  return [duration, getDurationSuffix(duration, '', mode)];
}

/**
 * Renders `seconds` as duration string with the largest possible unit, e.g.
 * 3600 results in '1 hour'.
 * @param mode use 'short' to get symbols (s) and 'long' for long unit names
 *   (seconds).
 */
export function toDurationString(
  duration: number,
  mode: 'short' | 'long' = 'short',
) {
  const roundedNoDecimal = Math.round(duration);
  const [durationAtUnit, unit] = toDurationUnit(roundedNoDecimal, mode);
  return `${durationAtUnit} ${unit}`;
}

function getDurationSuffix(
  duration: number,
  prefix: string,
  mode: 'short' | 'long' = 'short',
) {
  if (mode === 'short') {
    return `${prefix}`;
  } else if (duration === 1) {
    return `${prefix}`;
  } else {
    return `${prefix}s`;
  }
}
