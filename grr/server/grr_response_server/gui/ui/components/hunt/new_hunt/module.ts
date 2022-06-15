import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';

import {ApprovalModule} from '../../approval/module';
import {FlowDetailsModule} from '../../flow_details/module';
import {TitleEditorModule} from '../../form/title_editor/module';

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
    OutputPluginsFormModule,
    FlowDetailsModule,
    CommonModule,
    ParamsFormModule,
    ApprovalModule,
    TitleEditorModule,
    MatButtonModule,
  ],
  declarations: [NewHunt],
})
export class NewHuntModule {
}
