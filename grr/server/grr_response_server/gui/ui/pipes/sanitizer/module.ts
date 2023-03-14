import {NgModule} from '@angular/core';
import {BrowserModule} from '@angular/platform-browser';

import {SanitizerPipe} from './sanitizer_pipe';

@NgModule({
  imports: [BrowserModule],
  declarations: [SanitizerPipe],
  exports: [SanitizerPipe],
})
export class SanitizerPipeModule {
}