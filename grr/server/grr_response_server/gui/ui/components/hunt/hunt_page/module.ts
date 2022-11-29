import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';

import {TitleEditorModule} from '../../form/title_editor/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {UserImageModule} from '../../user_image/module';
import {HuntStatusChipModule} from '../hunt_status_chip/module';

import {HuntPage} from './hunt_page';
import {HuntProgress} from './hunt_progress/hunt_progress';
import {HuntResultDetailsModule} from './hunt_result_details/module';
import {HuntResultsModule} from './hunt_results/module';
import {HuntPageRoutingModule} from './routing';

/**
 * Module for hunt view page.
 */
@NgModule({
  imports: [
    CommonModule,
    CopyButtonModule,
    HuntPageRoutingModule,
    HuntProgress,
    HuntResultDetailsModule,
    HuntResultsModule,
    HuntStatusChipModule,
    MatButtonModule,
    MatChipsModule,
    TitleEditorModule,
    UserImageModule,
  ],
  declarations: [HuntPage],
})
export class HuntPageModule {
}
