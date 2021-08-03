import {NgModule} from '@angular/core';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {FileDetails} from './file_details';
import {FileDetailsRoutingModule} from './routing';

@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,

    FileDetailsRoutingModule,
  ],
  declarations: [
    FileDetails,
  ],
})
export class FileDetailsModule {
}
