import {NgModule} from '@angular/core';

import {FileModePipe} from './file_mode_pipe';


@NgModule({
  imports: [],
  declarations: [
    FileModePipe,
  ],
  exports: [
    FileModePipe,
  ]
})
export class FileModeModule {
}
