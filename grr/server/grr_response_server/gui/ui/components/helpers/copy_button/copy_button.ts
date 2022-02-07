import {Clipboard} from '@angular/cdk/clipboard';
import {Component, ElementRef, Input, ViewChild} from '@angular/core';

/**
 * Copies text on click. Does not change the content's dimensions or
 * appearance.
 */
@Component({
  selector: 'app-copy-button',
  templateUrl: './copy_button.ng.html',
  styleUrls: ['./copy_button.scss'],
  host: {
    '(click)': 'triggerCopy($event)',
    '(mouseenter)': 'onMouseEnter($event)',
  },
})
export class CopyButton {
  @ViewChild('copyContents') copyContentsElement!: ElementRef<HTMLElement>;

  /**
   * If set, clicking will not copy the textContent of this elements children,
   * but the provided text instead.
   */
  @Input() overrideCopyText: string|null|undefined = undefined;

  copied = false;

  constructor(private readonly clipboard: Clipboard) {}

  get copyText() {
    return this.overrideCopyText ??
        this.copyContentsElement.nativeElement.textContent?.trim() ?? '';
  }

  triggerCopy(event: MouseEvent) {
    this.copied = this.clipboard.copy(this.copyText);
    event.preventDefault();
    event.stopPropagation();
  }

  onMouseEnter(event: MouseEvent) {
    // If the user clicks "copy" we show a checkmark icon until the user moves
    // their mouse away. We do not reset the icon back to the copy icon
    // onMouseOut, because the element is still in a visible fade-out when the
    // mouse leaves. Thus, we reset the icon state on the next mouse enter.
    this.copied = false;
  }
}
