
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';
import {MatLegacySelectModule} from '@angular/material/legacy-select';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {RouterModule} from '@angular/router';

import {HelpersModule} from '../../flow_details/helpers/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../../helpers/drawer_link/drawer_link_module';
import {InfiniteListModule} from '../../helpers/infinite_list/infinite_list_module';
import {HuntArguments} from '../../hunt/hunt_arguments/hunt_arguments';
import {HuntFlowArguments} from '../../hunt/hunt_flow_arguments/hunt_flow_arguments';
import {HuntHelpModule} from '../../hunt/hunt_help/module';
import {TimestampModule} from '../../timestamp/module';
import {UserImageModule} from '../../user_image/module';
import {HuntStatusChipModule} from '../hunt_status_chip/module';

import {HuntOverviewPage} from './hunt_overview_page';


@NgModule({
  imports: [
    CommonModule,          CopyButtonModule,       DrawerLinkModule,
    RouterModule,          HelpersModule,          HuntArguments,
    HuntFlowArguments,     HuntHelpModule,         HuntStatusChipModule,
    MatLegacyButtonModule, MatLegacyCardModule,    MatLegacyChipsModule,
    MatIconModule,         MatProgressBarModule,   MatLegacySelectModule,
    MatLegacyMenuModule,   MatLegacyTooltipModule, ReactiveFormsModule,
    InfiniteListModule,    TimestampModule,        UserImageModule,
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