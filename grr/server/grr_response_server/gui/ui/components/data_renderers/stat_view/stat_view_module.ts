import {NgModule} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';

import {StatView} from './stat_view';

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    BrowserAnimationsModule,
    CopyButtonModule,
    HumanReadableSizeModule,
    MatTooltipModule,
    TimestampModule,
    // keep-sorted end
    // clang-format on
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
