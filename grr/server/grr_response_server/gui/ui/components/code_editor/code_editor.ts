import {
    ChangeDetectionStrategy,
    Component,
    ViewChild,
    ElementRef,
    AfterViewInit,
    ViewEncapsulation,
    Output,
    EventEmitter,
    Input,
} from '@angular/core';

import * as CodeMirror from 'codemirror';
// importing sql-hint is needed for SQL syntax highlighting
import 'codemirror/addon/hint/sql-hint.js';
// importing show-hint is needed for the autocomplete pop-up
import 'codemirror/addon/hint/show-hint.js';


/** Displays a code editor. */
@Component({
  selector: 'code-editor',
  templateUrl: './code_editor.ng.html',
  styleUrls: ['./code_editor.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class CodeEditor implements AfterViewInit {
  @ViewChild('editorTarget')
  private readonly editorTarget!: ElementRef;

  @Input() initialValue = '';
  @Output() latestValue = new EventEmitter<string>();

  ngAfterViewInit(): void {
    this.initializeEditor();
  }

  private initializeEditor(): void {
    const editor = CodeMirror.fromTextArea(this.editorTarget.nativeElement, {
      value: '',
      mode: 'text/x-sqlite',
      theme: 'idea',
      extraKeys: {'Ctrl-Space': 'autocomplete'},
      lineNumbers: true,
      lineWrapping: true,
    });

    editor.on('change', () => {
      this.latestValue.emit(editor.getValue());
    });

    editor.setValue(this.initialValue);
  }
}
