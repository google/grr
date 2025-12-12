import {Pipe, PipeTransform, SecurityContext} from '@angular/core';
import {DomSanitizer, SafeValue} from '@angular/platform-browser';

/**
 * Pipe which sanitizes stringified DOM elements. By default it assumes the
 * context is set to HTML.
 */
@Pipe({name: 'sanitize'})
export class SanitizerPipe implements PipeTransform {
  constructor(private readonly sanitizer: DomSanitizer) {}

  transform(
    value: string | SafeValue | null | undefined,
    context: SecurityContext = SecurityContext.HTML,
  ): string | null {
    return this.sanitizer.sanitize(context, value ?? null);
  }
}
