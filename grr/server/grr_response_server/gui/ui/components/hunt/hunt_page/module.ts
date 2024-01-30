import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ApprovalCardModule} from '../../approval_card/module';
import {HelpersModule} from '../../flow_details/helpers/module';
import {TitleEditorModule} from '../../form/title_editor/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../../helpers/drawer_link/drawer_link_module';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {UserImageModule} from '../../user_image/module';
import {HuntArguments} from '../hunt_arguments/hunt_arguments';
import {HuntFlowArguments} from '../hunt_flow_arguments/hunt_flow_arguments';
import {HuntStatusChipModule} from '../hunt_status_chip/module';
import {ModifyHuntModule} from '../modify_hunt/module';

import {HuntPage} from './hunt_page';
import {HuntProgressModule} from './hunt_progress/module';
import {HuntResultDetailsModule} from './hunt_result_details/module';
import {HuntResultsModule} from './hunt_results/module';

/**
 * Module for hunt view page.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    ApprovalCardModule,
    CommonModule,
    CopyButtonModule,
    DrawerLinkModule,
    HelpersModule,
    HumanReadableSizeModule,
    HuntArguments,
    HuntFlowArguments,
    HuntProgressModule,
    HuntResultDetailsModule,
    HuntResultsModule,
    HuntStatusChipModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    MatTooltipModule,
    ModifyHuntModule,
    TitleEditorModule,
    UserImageModule,
    // keep-sorted end
  ],
  declarations: [HuntPage],
})
export class HuntPageModule {}
