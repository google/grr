import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
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
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressSpinnerModule,
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
