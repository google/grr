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

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    BrowserAnimationsModule,
    DrawerLinkModule,
    HexViewModule,
    HumanReadableSizeModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatTooltipModule,
    RouterModule,
    TimestampModule,
    // keep-sorted end
    // clang-format on
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
