import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {TextView} from './text_view';

@NgModule({
  imports: [CommonModule],
  declarations: [TextView],
  exports: [TextView],
})
export class TextViewModule {}
