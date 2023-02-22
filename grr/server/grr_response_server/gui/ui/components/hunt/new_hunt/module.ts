import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ApprovalCardModule} from '../../approval_card/module';
import {FlowDetailsModule} from '../../flow_details/module';
import {TitleEditorModule} from '../../form/title_editor/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {HuntFlowArguments} from '../hunt_flow_arguments/hunt_flow_arguments';

import {ClientsFormModule} from './clients_form/module';
import {NewHunt} from './new_hunt';
import {OutputPluginsFormModule} from './output_plugins_form/module';
import {ParamsFormModule} from './params_form/module';
import {NewHuntRoutingModule} from './routing';

/**
 * Module for new hunt creation.
 */
@NgModule({
  imports: [
    NewHuntRoutingModule,
    ClientsFormModule,
    CopyButtonModule,
    OutputPluginsFormModule,
    FlowDetailsModule,
    CommonModule,
    ParamsFormModule,
    HuntFlowArguments,
    ApprovalCardModule,
    TitleEditorModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    MatTooltipModule,
    MatFormFieldModule,
  ],
  declarations: [NewHunt],
})
export class NewHuntModule {
}
