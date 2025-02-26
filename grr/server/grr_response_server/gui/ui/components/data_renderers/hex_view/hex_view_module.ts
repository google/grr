import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {HexView} from './hex_view';

@NgModule({
  imports: [CommonModule],
  declarations: [HexView],
  exports: [HexView],
})
export class HexViewModule {}
