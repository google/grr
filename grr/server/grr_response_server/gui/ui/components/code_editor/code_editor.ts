import {
    ChangeDetectionStrategy,
    Component,
    ViewChild,
    ElementRef,
    AfterViewInit,
    ViewEncapsulation,
    Input,
    forwardRef,
} from '@angular/core';
import { NG_VALUE_ACCESSOR, ControlValueAccessor } from '@angular/forms';

import * as CodeMirror from 'codemirror';
// importing sql-hint is needed for SQL syntax highlighting
import 'codemirror/addon/hint/sql-hint.js';
// importing show-hint is needed for the autocomplete pop-up
import 'codemirror/addon/hint/show-hint.js';

type OnChangeFn = (textValue: string) => void;

/** Displays a code editor. */
@Component({
  selector: 'code-editor',
  templateUrl: './code_editor.ng.html',
  styleUrls: ['./code_editor.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CodeEditor),
      multi: true,
    },
  ],
})
export class CodeEditor implements AfterViewInit, ControlValueAccessor {
  @ViewChild('editorTarget')
  private readonly editorTarget!: ElementRef;
  private editor?: CodeMirror.Editor;

  private latestOverwrite = '';
  @Input()
  set editorValue(newValue: string) {
    this.latestOverwrite = newValue;
    this.editor?.setValue(newValue);
  }
  get editorValue() {
    return this.editor?.getValue() || '';
  }

  // ControlValueAccessor functionality for Angular Forms interoperability
  announceValueChanged: OnChangeFn = () => { };
  writeValue(value: string): void {
    this.editorValue = value;
  }
  registerOnChange(fn: OnChangeFn): void {
    this.announceValueChanged = fn;
  }
  registerOnTouched(): void { }

  ngAfterViewInit(): void {
    this.initializeEditor();

    // We have to re-set the editor value so that it contains the initial text
    // because input arguments are bound prior to ngAfterViewInit, when editor
    // was still undefined.
    this.editorValue = this.latestOverwrite;
  }

  private initializeEditor(): void {
    this.editor = CodeMirror.fromTextArea(this.editorTarget.nativeElement, {
      value: '',
      mode: 'text/x-sqlite',
      theme: 'idea',
      extraKeys: {'Ctrl-Space': 'autocomplete'},
      lineNumbers: true,
      lineWrapping: true,
    });

    this.editor.on('change', () => {
      this.announceValueChanged(this.editorValue);
    });
  }
}
