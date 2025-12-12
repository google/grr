import {DateTime, Duration} from '../../date_time';
import {assertTruthy} from '../../preconditions';
import {
  Any,
  DataBlob,
  Dict,
  DurationSeconds,
  KeyValue,
  RDFDatetime,
  RDFDatetimeSeconds,
} from '../api_interfaces';

/**
 * Constructs an API timestamp from a given DateTime object.
 *
 * @param apiTimestamp
 */
export function createOptionalApiTimestamp(
  dateTime?: DateTime | null,
): string | undefined {
  if (dateTime != null) {
    return (dateTime.toMillis() * 1e3).toString();
  }
  return undefined;
}

/**
 * Constructs an API timestamp from a given Date object.
 */
export function createOptionalApiTimestampFromDate(
  date?: Date | null,
): string | undefined {
  if (date != null) {
    return (date.getTime() * 1e3).toString();
  }
  return undefined;
}

/**
 * Constructs a Date from a unixtime string with microsecond-precision.
 *
 * Because `Date` uses millisecond-precision, microseconds are truncated.
 */
export function createDate(apiTimestamp: RDFDatetime): Date {
  assertTruthy(apiTimestamp, 'Date');

  const date = new Date(Number(apiTimestamp) / 1000);
  if (isNaN(date.valueOf())) {
    throw new Error(`Date "${apiTimestamp}" is invalid.`);
  }
  return date;
}

/**
 * Constructs a Date from a unixtime string with microsecond-precision.
 *
 * Because `Date` uses millisecond-precision, microseconds are truncated. This
 * function returns undefined when given undefined or the empty string.
 */
export function createOptionalDate(apiTimestamp: undefined): undefined;
export function createOptionalDate(apiTimestamp: ''): undefined;
export function createOptionalDate(apiTimestamp: RDFDatetime): Date;
export function createOptionalDate(
  apiTimestamp?: RDFDatetime,
): Date | undefined;

export function createOptionalDate(
  apiTimestamp?: RDFDatetime,
): Date | undefined {
  if (!apiTimestamp) {
    return undefined; // Return undefined for undefined and empty string.
  }
  return createDate(apiTimestamp);
}

/**
 * Constructs a Date from a unixtime string with seconds precision.
 */
export function createOptionalDateSeconds(
  timestampSeconds: undefined,
): undefined;
export function createOptionalDateSeconds(
  timestampSeconds: RDFDatetimeSeconds,
): Date;
export function createOptionalDateSeconds(
  timestampSeconds?: RDFDatetimeSeconds,
): Date | undefined;

export function createOptionalDateSeconds(
  timestampSeconds?: RDFDatetimeSeconds,
): Date | undefined {
  if (!timestampSeconds) {
    return undefined;
  }
  const result = new Date(Number(timestampSeconds) * 1000);
  if (isNaN(result.valueOf())) {
    throw new Error(`Date "${timestampSeconds}" is invalid.`);
  }
  return result;
}

/**
 * Constructs a DateTime from a unixtime string.
 */
export function createOptionalDateTime(
  apiTimestamp: RDFDatetime | undefined,
): DateTime | undefined {
  if (!apiTimestamp) {
    return undefined;
  }

  return DateTime.fromJSDate(createDate(apiTimestamp));
}

/** Converts a Date to millseconds since unix epoch. */
export function toOptionalMillis(date: undefined): undefined;
export function toOptionalMillis(date: Date): number;
export function toOptionalMillis(date?: Date): number | undefined;
export function toOptionalMillis(date?: Date): number | undefined {
  return date?.getTime();
}

/**
 * Constructs a Duration from a duration seconds.
 */
export function createDuration(apiDuration: DurationSeconds): Duration {
  const duration = Duration.fromObject({seconds: Number(apiDuration)});
  if (isNaN(duration.valueOf())) {
    throw new Error(`Duration "${apiDuration}" is invalid.`);
  }
  return duration;
}

/**
 * Constructs an optional Duration from a DurationSeconds object.
 */
export function createOptionalDuration(apiDuration: DurationSeconds): undefined;
export function createOptionalDuration(apiDuration: ''): undefined;
export function createOptionalDuration(apiDuration: DurationSeconds): Duration;
export function createOptionalDuration(
  apiDuration?: DurationSeconds,
): Duration | undefined;

export function createOptionalDuration(
  apiDuration?: DurationSeconds,
): Duration | undefined {
  if (!apiDuration) {
    return undefined; // Return undefined for undefined and empty string.
  }
  return createDuration(apiDuration);
}

/**
 * Creates an unknown object out of protobuf's any object.
 * Unknown is different from any as, unlike any, it has to be explicitly cast
 * to a type for any use.
 */
export function createUnknownObject(anyObject?: Any): unknown | undefined {
  if (!anyObject) {
    return undefined;
  }

  const result = {...anyObject};
  delete result['@type'];
  return result;
}

/**
 * Decodes a encoded base64 string into a byte array.
 * Throws exception when the provided string is encoded wrongly.
 */
export function decodeBase64(encodedString?: string): Uint8Array {
  if (encodedString === undefined) {
    return new Uint8Array(0);
  }

  const decodedString = atob(encodedString);

  const byteArray = new Uint8Array(decodedString.length);
  for (let i = 0; i < decodedString.length; i++) {
    byteArray[i] = decodedString.charCodeAt(i);
  }

  return byteArray;
}

/** Encodes a Unicode string with base64. */
export function encodeStringToBase64(str: string): string {
  return btoa(str);
}

/** Decodes base64 data and returns a string. */
export function decodeBase64ToString(data: string): string {
  return atob(data);
}

/**
 * Returns the uppercase hex representation of the least significant byte of
 * the provided number
 */
export function leastSignificantByteToHex(number: number): string {
  number = number & 0xff;

  return number.toString(16).toUpperCase().padStart(2, '0');
}

/** Returns the uppercase hex representation of a byte array. */
export function bytesToHex(bytes: Uint8Array): string {
  return [...bytes].map(leastSignificantByteToHex).join('');
}

/** Creates IPv4 address string from a 4 bytes array */
export function createIpv4Address(bytes: Uint8Array): string {
  if (bytes.length !== 4) {
    return '';
  }

  return `${bytes[0]}.${bytes[1]}.${bytes[2]}.${bytes[3]}`;
}

/**
 * Creates IPv6 non-abbreviated address string from a 16 bytes array
 */
export function createIpv6Address(bytes: Uint8Array): string {
  if (bytes.length !== 16) {
    return '';
  }

  let ipString = `${leastSignificantByteToHex(
    bytes[0],
  )}${leastSignificantByteToHex(bytes[1])}`;
  for (let i = 2; i < 16; i += 2) {
    ipString += `:${leastSignificantByteToHex(
      bytes[i],
    )}${leastSignificantByteToHex(bytes[i + 1])}`;
  }

  return ipString;
}

/** Creates a MAC Address string from a 6 bytes array */
export function createMacAddress(bytes: Uint8Array): string {
  if (bytes.length !== 6) {
    return '';
  }

  let macString = `${leastSignificantByteToHex(bytes[0])}`;
  for (let i = 1; i < 6; i++) {
    macString += `:${leastSignificantByteToHex(bytes[i])}`;
  }

  return macString;
}

/** Converts a DataBlob into a native JavaScript value. */
export function translateDataBlob(blob: DataBlob): unknown {
  if (blob.integer !== undefined) {
    return BigInt(blob.integer);
  } else if (blob.string !== undefined) {
    return blob.string;
  } else if (blob.boolean !== undefined) {
    return blob.boolean;
  } else if (blob.float !== undefined) {
    return blob.float;
  } else if (blob.list !== undefined) {
    return [...(blob.list.content ?? [])].map(translateDataBlob);
  } else if (blob.set !== undefined) {
    return new Set([...(blob.set.content ?? [])].map(translateDataBlob));
  } else if (blob.dict !== undefined) {
    return translateDict(blob.dict);
  } else {
    return undefined;
  }
}

function translateKeyValue({k, v}: KeyValue): [unknown, unknown] {
  return [translateDataBlob(k ?? {}), translateDataBlob(v ?? {})];
}

/** Translates a RDF Dict into a JavaScript Map with native values. */
export function translateDict(dict: Dict): ReadonlyMap<unknown, unknown> {
  const keyvalues = [...(dict.dat ?? [])].map(translateKeyValue);
  return new Map(keyvalues);
}

/** Converts an optional numeric value to a bigint. */
export function createOptionalBigInt(data?: string): bigint | undefined {
  return data !== undefined ? BigInt(data) : data;
}
