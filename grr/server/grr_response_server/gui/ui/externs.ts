/**
 * Convert a number or a string to a bignum.
 * Returns a number because BigInts support the usual numeric operators.
 * TODO(user): Remove once JSCompiler natively supports BigInts.
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/BigInt
 */
// tslint:disable-next-line:enforce-name-casing
declare function BigInt(num: number|string): number;

// Best-effort polyfill for Safari.
window.BigInt = window.BigInt ?? window.Number;
