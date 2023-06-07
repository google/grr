
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

import {HelpersModule} from '../../../flow_details/helpers/module';
import {HuntArguments} from '../../hunt_arguments/hunt_arguments';
import {HuntFlowArguments} from '../../hunt_flow_arguments/hunt_flow_arguments';
import {HuntOriginalReference} from '../../hunt_original_reference/hunt_original_reference';
import {HuntProgressTable} from '../hunt_progress_table/hunt_progress_table';

import {HuntProgress} from './hunt_progress';


@NgModule({
  imports: [
    // keep-sorted start block=yes
    CommonModule, HuntOriginalReference, HuntProgressTable,
    // tslint:disable-next-line:deprecation
    MatLegacyTooltipModule, HelpersModule, HuntArguments, HuntFlowArguments,
    // keep-sorted end
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