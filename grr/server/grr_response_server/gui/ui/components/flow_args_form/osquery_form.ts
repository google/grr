import {ChangeDetectionStrategy, Component, OnInit, Output, ViewChild, ElementRef, AfterViewInit} from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {shareReplay} from 'rxjs/operators';

import * as CodeMirror from 'codemirror';
import 'codemirror/addon/hint/show-hint.js';
import 'codemirror/addon/hint/sql-hint.js';

import {OsqueryArgs} from '../../lib/api/api_interfaces';


/** Form that configures an Osquery flow. */
@Component({
  selector: 'osquery-form',
  templateUrl: './osquery_form.ng.html',
  styleUrls: ['./osquery_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryForm extends FlowArgumentForm<OsqueryArgs> implements
    OnInit, AfterViewInit {
  readonly form = new FormGroup({
    query: new FormControl(null, Validators.required),
    timeoutMillis: new FormControl(null, Validators.required),
    ignoreStderrErrors: new FormControl(null),
  });

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  @ViewChild('editorTarget')
  readonly editorTarget!: ElementRef;

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }

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
      this.form.patchValue({
        query: editor.getValue(),
      });
    });
  }
}
