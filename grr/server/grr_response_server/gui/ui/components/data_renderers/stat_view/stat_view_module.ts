import {NgModule} from '@angular/core';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';

import {StatView} from './stat_view';

@NgModule({
  imports: [
    BrowserAnimationsModule,

    MatLegacyTooltipModule,

    CopyButtonModule,
    HumanReadableSizeModule,
    TimestampModule,
  ],
  declarations: [
    StatView,
  ],
  exports: [
    StatView,
  ]
})
export class StatViewModule {
}
