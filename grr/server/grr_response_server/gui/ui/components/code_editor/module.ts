import {NgModule} from '@angular/core';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';

import {CodeEditor} from './code_editor';

/** Module for the CodeEditor component. */
@NgModule({
  imports: [
    MatLegacyFormFieldModule,
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
