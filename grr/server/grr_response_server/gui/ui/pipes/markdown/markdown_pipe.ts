import {Pipe, PipeTransform} from '@angular/core';

import {marked, MarkedOptions} from '../../lib/markdown';

const GLOBAL_MARKED_CONFIG: MarkedOptions = {
  silent: true,
};

/**
 * Pipe which converts a Markdown string to an HTML string.
 */
@Pipe({name: 'markdown'})
export class MarkdownPipe implements PipeTransform {
  transform(value: string, options: MarkedOptions = {}): string {
    return marked(value, {
      ...GLOBAL_MARKED_CONFIG,
      ...options,
    });
  }
}
