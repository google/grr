import {AfterContentInit, AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, ContentChild, Directive, ElementRef, EventEmitter, HostListener, Input, OnChanges, Output} from '@angular/core';

import {assertNonNull} from '../../../lib/preconditions';

/**
 * The directive that marks a tag as editable. The tag has to be
 * wrapped in <title-editor> component, that handles the inputs and the output
 * callback and the CSS for the border. The directive uses the 'contentEditable'
 * attribute instead of an input tag, so the content keeps the original styles
 * (color and font) during editing.
 */
@Directive({
  selector: '[titleEditable]',
  host: {
    '[attr.contenteditable]': `contenteditable ? 'plaintext-only' : 'false'`,
    '(keydown.enter)': 'stopEdit()',
    '(keydown.escape)': 'cancelEditing()',
  },
})
export class TitleEditorContent implements AfterViewInit {
  contenteditable = false;
  private previousValue = '';

  constructor(
      private readonly element: ElementRef,
      private readonly parent: TitleEditor,
  ) {}

  ngAfterViewInit() {
    this.parent.markForCheck();
  }

  startEdit() {
    this.previousValue = this.getText();
    this.contenteditable = true;
    this.parent.markForCheck();
    setTimeout(() => {
      this.element.nativeElement.focus();
    });
  }

  getText() {
    return this.element.nativeElement.textContent;
  }

  cancelEditing() {
    if (!this.contenteditable) {
      return;
    }
    this.element.nativeElement.textContent = this.previousValue;
    this.stopEdit();
  }

  @HostListener('blur')
  stopEdit() {
    if (!this.contenteditable) {
      return;
    }
    this.element.nativeElement.scrollLeft = 0;
    this.contenteditable = false;
    const text = this.element.nativeElement.textContent;
    if (text !== this.previousValue) {
      this.parent.save(text);
    } else {
      this.parent.markForCheck();
    }
  }
}

/**
 * A component that allows editing the child content inline. The editable
 * child tag has to be marked with [titleEditable] directive.
 */
@Component({
  selector: 'title-editor',
  templateUrl: 'title_editor.ng.html',
  styleUrls: ['./title_editor.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TitleEditor implements AfterContentInit, OnChanges {
  @Input() disabled = false;
  @Output() changed = new EventEmitter<string>();
  @ContentChild(TitleEditorContent) content!: TitleEditorContent;

  constructor(private readonly changeDetectorRef: ChangeDetectorRef) {}

  ngAfterContentInit() {
    assertNonNull(this.content, '[titleEditable]');
  }

  get editing() {
    return this.content?.contenteditable;
  }

  ngOnChanges() {
    if (this.disabled && this.editing) {
      this.content?.cancelEditing();
    }
  }

  startEdit() {
    if (this.disabled || this.editing) {
      return;
    }
    this.content.startEdit();
  }

  save(newValue: string) {
    this.changed.emit(newValue);
    this.changeDetectorRef.markForCheck();
  }

  markForCheck() {
    this.changeDetectorRef.markForCheck();
  }
}
