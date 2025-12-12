import {Clipboard, ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  inject,
  input,
  ViewChild,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';

/**
 * Copies text on click. Does not change the content's dimensions or
 * appearance.
 */
@Component({
  selector: 'copy-button',
  templateUrl: './copy_button.ng.html',
  styleUrls: ['./copy_button.scss'],
  imports: [
    ClipboardModule,
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CopyButton {
  private readonly clipboard = inject(Clipboard);
  @ViewChild('copyContents') copyContentsElement!: ElementRef<HTMLElement>;

  /**
   * If set, clicking will not copy the textContent of this elements children,
   * but the provided text instead.
   */
  readonly overrideCopyText = input<string>();
  readonly multiline = input<boolean>();
  readonly tooltip = input<string>();

  protected copied = false;
  protected showIcon = false;

  protected triggerCopy(event: MouseEvent) {
    const copyText =
      this.overrideCopyText() ??
      this.copyContentsElement.nativeElement.textContent?.trim() ??
      '';

    this.copied = this.clipboard.copy(copyText);
    event.preventDefault();
    event.stopPropagation();
  }

  protected showCopyIcon() {
    this.showIcon = true;
    // If the user clicks "copy" we show a checkmark icon until the user moves
    // their mouse away. We do not reset the icon back to the copy icon
    // onMouseOut, because the element is still in a visible fade-out when the
    // mouse leaves. Thus, we reset the icon state on the next mouse enter.
    this.copied = false;
  }

  protected hideCopyIcon() {
    this.showIcon = false;
  }
}
