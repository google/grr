import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {HumanReadableSizeModule} from '../human_readable_size/module';
import {TimestampModule} from '../timestamp/module';

import {FileDetails} from './file_details';
import {FileDetailsRoutingModule} from './routing';

@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,

    MatButtonModule,
    MatIconModule,
    MatTooltipModule,

    FileDetailsRoutingModule,
    HumanReadableSizeModule,
    TimestampModule,
  ],
  declarations: [
    FileDetails,
  ],
})
export class FileDetailsModule {
}
