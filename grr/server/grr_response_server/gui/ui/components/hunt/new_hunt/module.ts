import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';

import {ApprovalCardModule} from '../../approval_card/module';
import {FlowDetailsModule} from '../../flow_details/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {HuntFlowArguments} from '../hunt_flow_arguments/hunt_flow_arguments';
import {HuntHelpModule} from '../hunt_help/module';
import {HuntOriginalReference} from '../hunt_original_reference/hunt_original_reference';

import {ClientsFormModule} from './clients_form/module';
import {NewHunt} from './new_hunt';
import {OutputPluginsFormModule} from './output_plugins_form/module';
import {ParamsFormModule} from './params_form/module';

/**
 * Module for new hunt creation.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    ApprovalCardModule,
    ClientsFormModule,
    CommonModule,
    CopyButtonModule,
    FlowDetailsModule,
    FormsModule,
    HuntFlowArguments,
    HuntHelpModule,
    HuntOriginalReference,
    MatButtonModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    OutputPluginsFormModule,
    ParamsFormModule,
    ReactiveFormsModule,
    RouterModule,
    // keep-sorted end
    // clang-format on
  ],
  declarations: [NewHunt],
})
export class NewHuntModule {
}
