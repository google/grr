import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {TitleEditor, TitleEditorContent} from './title_editor';

@NgModule({
  imports: [
    BrowserAnimationsModule,
    MatButtonModule,
    MatIconModule,
    RouterModule,
  ],
  declarations: [TitleEditorContent, TitleEditor],
  exports: [TitleEditorContent, TitleEditor],
})
export class TitleEditorModule {
}
