
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';

import {HelpersModule} from '../../../flow_details/helpers/module';
import {HuntArguments} from '../../hunt_arguments/hunt_arguments';
import {HuntFlowArguments} from '../../hunt_flow_arguments/hunt_flow_arguments';
import {HuntOriginalReference} from '../../hunt_original_reference/hunt_original_reference';
import {HuntProgressTable} from '../hunt_progress_table/hunt_progress_table';

import {HuntProgress} from './hunt_progress';


@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    CommonModule,
    HelpersModule,
    HuntArguments,
    HuntFlowArguments,
    HuntOriginalReference,
    HuntProgressTable,
    MatTooltipModule,
    // keep-sorted end
    // clang-format on
  ],
  declarations: [
    HuntProgress,
  ],
  exports: [
    HuntProgress,
  ],
})
export class HuntProgressModule {
}