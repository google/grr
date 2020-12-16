import {NgModule} from '@angular/core';
import {CodeEditor} from './code_editor';

/** Module for the CodeEditor component. */
@NgModule({
  declarations: [
    CodeEditor,
  ],
  exports: [
    CodeEditor,
  ],
})
export class CodeEditorModule {
}
