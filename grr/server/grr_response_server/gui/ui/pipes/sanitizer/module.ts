import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {SanitizerPipe} from './sanitizer_pipe';

@NgModule({
  imports: [CommonModule],
  declarations: [SanitizerPipe],
  exports: [SanitizerPipe],
})
export class SanitizerPipeModule {}
