/**
 * Configures the spacing around an arbitrary D3-generated element.
 */
export declare interface PaddingConfiguration {
  topPx: number;
  rightPx: number;
  bottomPx: number;
  leftPx: number;
}

/** Default padding to apply to D3-generated elements. */
export const DEFAULT_PADDING_PX = 40;

/** Returns a CSS-compatible value for the padding property */
export function toCSSPaddingValue(padding: PaddingConfiguration): string {
  return `${padding.topPx}px ${padding.rightPx}px ${padding.bottomPx}px ${padding.leftPx}px`;
}
