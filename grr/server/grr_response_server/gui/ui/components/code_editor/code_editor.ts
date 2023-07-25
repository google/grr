// Importing sql-hint is needed for SQL syntax highlighting.
import 'codemirror/addon/hint/sql-hint.js';
// Importing show-hint is needed for the autocomplete pop-up.
import 'codemirror/addon/hint/show-hint.js';


import {FocusMonitor} from '@angular/cdk/a11y';
import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, forwardRef, HostBinding, Input, OnDestroy, ViewChild, ViewEncapsulation,} from '@angular/core';
import {ControlValueAccessor, NG_VALUE_ACCESSOR, NgControl} from '@angular/forms';
import {MatFormFieldControl} from '@angular/material/form-field';
// tslint:disable-next-line:enforce-name-casing
import * as CodeMirror from 'codemirror';
import {Subject} from 'rxjs';
import {takeUntil} from 'rxjs/operators';

import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';

type OnChangeFn = (textValue: string) => void;

/** Language/mode to syntax highlight in the code editor. */
export enum HighlightMode {
  PLAIN = 'text/plain',
  OSQUERY = 'text/x-sqlite',
}

/**
 * Displays a code editor.
 * It can be used as an Angular form field, and it can be put inside
 * <mat-form-field></mat-form-field> tags.
 */
@Component({
  selector: 'app-code-editor',
  templateUrl: './code_editor.ng.html',
  styleUrls: [
    './code_editor.scss',
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CodeEditor),
      multi: true,
    },
    {
      provide: MatFormFieldControl,
      useExisting: CodeEditor,
      multi: true,
    }
  ],
})
export class CodeEditor implements MatFormFieldControl<string>, OnDestroy,
                                   AfterViewInit, ControlValueAccessor {
  private static uniqueNumber = 0;

  readonly ngOnDestroy = observeOnDestroy(this, () => {
    this.focusMonitor.stopMonitoring(this.rootElement.nativeElement);
  });

  readonly controlType = 'code-editor';

  @Input() highlight: HighlightMode = HighlightMode.PLAIN;

  /**
   * ID to associate all labels and hints of the enclosing mat-form-field with.
   */
  @HostBinding() readonly id: string;

  get value() {
    return this.editorValue;
  }
  set value(newValue: string|null) {
    this.editorValue = newValue ?? '';
  }

  get empty(): boolean {
    return this.editorValue === '';
  }

  readonly stateChanges = new Subject<void>();
  focused = false;

  // not implemented
  shouldLabelFloat = true;

  // not implemented
  required = false;

  // not implemented
  disabled = false;

  // not implemented
  placeholder = '';

  // not implemented
  ngControl: NgControl|null = null;

  // not implemented
  errorState = false;

  /**
   * Whether the code editor input will be focused when the enclosing
   * mat-form-field container is clicked
   */
  @Input() focusOnContainerClick = true;

  private initializeEditor(): void {
    this.editor = CodeMirror.fromTextArea(this.editorTarget.nativeElement, {
      value: '',
      mode: this.highlight,
      theme: 'neo',
      extraKeys: {'Ctrl-Space': 'autocomplete'},
      lineNumbers: true,
      lineWrapping: true,
    });

    this.editor.on('change', () => {
      this.announceValueChanged(this.editorValue);
      this.editorValueChanges$.next(this.editorValue);
    });
  }

  @ViewChild('editorTarget') private readonly editorTarget!: ElementRef;
  protected editor?: CodeMirror.Editor;

  private latestOverwrite = '';

  protected readonly editorValueChanges$ = new Subject<string>();

  // ControlValueAccessor functionality
  private announceValueChanged: OnChangeFn = () => {};

  constructor(
      private readonly focusMonitor: FocusMonitor,
      private readonly rootElement: ElementRef<HTMLElement>,
  ) {
    this.id = `${this.controlType}-${CodeEditor.uniqueNumber}`;
    CodeEditor.uniqueNumber += 1;

    focusMonitor.monitor(rootElement.nativeElement, true).subscribe(focused => {
      this.focused = isNonNull(focused);
      this.stateChanges.next();
    });

    this.editorValueChanges$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(() => {
          this.stateChanges.next();
        });
  }

  focus() {
    this.editor?.focus();
  }

  onContainerClick(event: MouseEvent): void {
    if (this.focusOnContainerClick) {
      this.focus();
    }
  }

  // not implemented
  setDescribedByIds(ids: string[]): void {}


  writeValue(value: string|undefined|null): void {
    this.editorValue = value ?? '';
  }

  registerOnChange(fn: OnChangeFn): void {
    this.announceValueChanged = fn;
  }

  registerOnTouched(): void {}

  set editorValue(newValue: string) {
    // The editor is initialized in ngAfterViewInit, and will be undefined
    // before that, including when @Input() arguments are set.
    // See ngAfterViewInit.
    this.editor?.setValue(newValue);
    this.latestOverwrite = newValue;
  }

  get editorValue() {
    return this.editor?.getValue() ?? '';
  }

  ngAfterViewInit(): void {
    this.initializeEditor();

    // We have to re-set the editor value so that it contains the initial text
    // because input arguments are bound prior to ngAfterViewInit, when editor
    // was still undefined.
    this.editorValue = this.latestOverwrite;
  }
}
