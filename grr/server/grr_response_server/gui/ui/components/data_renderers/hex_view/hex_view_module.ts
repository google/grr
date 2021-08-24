import {NgModule} from '@angular/core';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {HexView} from './hex_view';


@NgModule({
  imports: [
    BrowserAnimationsModule,
  ],
  declarations: [
    HexView,
  ],
  exports: [
    HexView,
  ]
})
export class HexViewModule {
}
