import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {MatMenuModule} from '@angular/material/menu';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';
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
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    CopyButtonModule,
    DrawerLinkModule,
    HelpersModule,
    HuntArguments,
    HuntFlowArguments,
    HuntHelpModule,
    HuntStatusChipModule,
    InfiniteListModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatMenuModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTooltipModule,
    ReactiveFormsModule,
    RouterModule,
    TimestampModule,
    UserImageModule,
    // keep-sorted end
  ],
  declarations: [HuntOverviewPage],
  exports: [HuntOverviewPage],
})
export class HuntOverviewPageModule {}
