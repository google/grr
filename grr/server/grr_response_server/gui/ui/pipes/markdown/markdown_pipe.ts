import {Pipe, PipeTransform} from '@angular/core';

import {Marked} from 'marked';

/**
 * Pipe which converts a Markdown string to an HTML string.
 */
@Pipe({name: 'markdown'})
export class MarkdownPipe implements PipeTransform {
  private readonly marked = new Marked();

  transform(value: string): string {
    return this.marked.parse(value, {
      async: false,
      silent: true,
    });
  }
}
