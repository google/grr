import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTabsModule} from '@angular/material/tabs';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {HexViewModule} from '../data_renderers/hex_view/hex_view_module';
import {DrawerLinkModule} from '../helpers/drawer_link/drawer_link_module';
import {HumanReadableSizeModule} from '../human_readable_size/module';
import {TimestampModule} from '../timestamp/module';

import {FileDetails} from './file_details';
import {FileDetailsPage} from './file_details_page';
import {FileDetailsRoutingModule} from './routing';

@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,

    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatTabsModule,

    DrawerLinkModule,
    FileDetailsRoutingModule,
    HexViewModule,
    HumanReadableSizeModule,
    TimestampModule,
  ],
  declarations: [
    FileDetails,
    FileDetailsPage,
  ],
  exports: [
    FileDetails,
  ]
})
export class FileDetailsModule {
}
