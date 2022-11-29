import {ChangeDetectionStrategy, Component, Input} from '@angular/core';

/**
 * Linkifies links in plain text.
 * Considers string tokens starting with 'http://' or 'https://' only as links.
 */
@Component({
  selector: 'app-text-with-links',
  templateUrl: './text_with_links.ng.html',
  styleUrls: ['./text_with_links.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TextWithLinks {
  @Input() text?: string|null = '';

  /**
   * Splits whitespace-separated text into an array, preserving whitespaces.
   * E.g.: 'my cat' -> ['my', ' ', 'cat']
   */
  protected get textTokens() {
    return this.text?.split(/(\s+)/) ?? [];
  }
  protected isLink(token: string) {
    return token.startsWith('https://') || token.startsWith('http://');
  }
}