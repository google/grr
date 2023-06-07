import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {FlowArgsViewModule} from '../flow_args_view/module';
import {CopyButtonModule} from '../helpers/copy_button/copy_button_module';
import {TimestampModule} from '../timestamp/module';
import {UserImageModule} from '../user_image/module';

import {FlowDetails} from './flow_details';
import {HelpersModule} from './helpers/module';
import {PluginsModule} from './plugins/module';



/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    ClipboardModule,
    CommonModule,
    FormsModule,
    HelpersModule,
    FlowArgsViewModule,
    ReactiveFormsModule,
    RouterModule,
    MatLegacyButtonModule,
    MatLegacyCardModule,
    MatLegacyChipsModule,
    MatLegacyFormFieldModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyMenuModule,
    MatLegacyProgressSpinnerModule,
    PluginsModule,
    UserImageModule,
    CopyButtonModule,
    TimestampModule,
  ],
  declarations: [
    FlowDetails,
  ],
  exports: [
    FlowDetails,
  ],
})
export class FlowDetailsModule {
}
