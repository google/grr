
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';

import {HelpersModule} from '../../../flow_details/helpers/module';
import {HuntArguments} from '../../hunt_arguments/hunt_arguments';
import {HuntFlowArguments} from '../../hunt_flow_arguments/hunt_flow_arguments';
import {HuntProgressTable} from '../hunt_progress_table/hunt_progress_table';

import {HuntProgress} from './hunt_progress';


@NgModule({
  imports: [
    CommonModule,
    MatTooltipModule,
    HelpersModule,
    HuntArguments,
    HuntFlowArguments,
    HuntProgressTable,
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