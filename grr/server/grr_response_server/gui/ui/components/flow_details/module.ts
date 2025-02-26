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
import {MatTooltipModule} from '@angular/material/tooltip';

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
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    ClipboardModule,
    CommonModule,
    CopyButtonModule,
    FlowArgsViewModule,
    FormsModule,
    HelpersModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    PluginsModule,
    ReactiveFormsModule,
    RouterModule,
    TimestampModule,
    UserImageModule,
    // keep-sorted end
  ],
  declarations: [FlowDetails],
  exports: [FlowDetails],
})
export class FlowDetailsModule {}
