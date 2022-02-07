import {NgModule} from '@angular/core';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {TextView} from './text_view';


@NgModule({
  imports: [
    BrowserAnimationsModule,
  ],
  declarations: [
    TextView,
  ],
  exports: [
    TextView,
  ]
})
export class TextViewModule {
}
