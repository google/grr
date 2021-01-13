import {NgModule} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {CodeEditor} from './code_editor';

/** Module for the CodeEditor component. */
@NgModule({
  imports: [
    MatFormFieldModule,
  ],
  declarations: [
    CodeEditor,
  ],
  exports: [
    CodeEditor,
  ],
})
export class CodeEditorModule {
}
