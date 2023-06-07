import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

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
import {HuntPageRoutingModule} from './routing';

/**
 * Module for hunt view page.
 */
@NgModule({
  imports: [
    // TODO: Re-enable tslint after migration is complete.
    // tslint:disable:deprecation
    // keep-sorted start block=yes
    ApprovalCardModule,    CommonModule,
    CopyButtonModule,      DrawerLinkModule,
    HelpersModule,         HuntArguments,
    HuntFlowArguments,     HuntPageRoutingModule,
    HuntProgressModule,    HuntResultDetailsModule,
    HuntResultsModule,     HuntStatusChipModule,
    MatIconModule,         MatLegacyTooltipModule,
    MatLegacyButtonModule, MatLegacyChipsModule,
    ModifyHuntModule,      TitleEditorModule,
    UserImageModule,       HumanReadableSizeModule,
    // keep-sorted end
    // tslint:enable:deprecation
  ],
  declarations: [HuntPage],
})
export class HuntPageModule {
}
