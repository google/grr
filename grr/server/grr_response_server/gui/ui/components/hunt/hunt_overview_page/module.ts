
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatCardModule} from '@angular/material/card';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';

import {HelpersModule} from '../../flow_details/helpers/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {InfiniteListModule} from '../../helpers/infinite_list/infinite_list_module';
import {HuntArguments} from '../../hunt/hunt_arguments/hunt_arguments';
import {HuntFlowArguments} from '../../hunt/hunt_flow_arguments/hunt_flow_arguments';
import {TimestampModule} from '../../timestamp/module';
import {UserImageModule} from '../../user_image/module';
import {HuntStatusChipModule} from '../hunt_status_chip/module';

import {HuntOverviewPage} from './hunt_overview_page';


@NgModule({
  imports: [
    CommonModule,
    CopyButtonModule,
    RouterModule,
    HelpersModule,
    HuntArguments,
    HuntFlowArguments,
    HuntStatusChipModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTooltipModule,
    ReactiveFormsModule,
    InfiniteListModule,
    TimestampModule,
    UserImageModule,
  ],
  declarations: [
    HuntOverviewPage,
  ],
  exports: [
    HuntOverviewPage,
  ],
})
export class HuntOverviewPageModule {
}