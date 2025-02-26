import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';

import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';

import {StatView} from './stat_view';

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    CopyButtonModule,
    HumanReadableSizeModule,
    MatTooltipModule,
    TimestampModule,
    // keep-sorted end
  ],
  declarations: [StatView],
  exports: [StatView],
})
export class StatViewModule {}
