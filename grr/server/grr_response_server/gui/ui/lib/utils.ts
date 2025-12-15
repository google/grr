/**
 * Throw an exception on unexpected values.
 *
 * checkExhaustive can be used along with type narrowing to ensure at
 * compile time that all possible types for a value have been handled. For cases
 * where exhaustiveness can not be guaranteed at compile time (i.e. proto enums)
 * an exception will be thrown.
 *
 * Example usage:
 *
 * ```
 * // enumValue: Enum.A | Enum.B
 * switch(enumValue) {
 *   case Enum.A:
 *     break;
 *   case Enum.B:
 *     break;
 *   default:
 *     checkExhaustive(enumValue);
 *     break;
 * }
 * ```
 */
export function checkExhaustive(value: never, msg?: string): never {
  throw new Error(msg);
}
