import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {TitleEditor, TitleEditorContent} from './title_editor';

@NgModule({
  imports: [
    BrowserAnimationsModule,
    MatLegacyButtonModule,
    MatIconModule,
    RouterModule,
  ],
  declarations: [TitleEditorContent, TitleEditor],
  exports: [TitleEditorContent, TitleEditor],
})
export class TitleEditorModule {
}
