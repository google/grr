import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {TitleEditorModule} from '../../form/title_editor/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';

import {HuntPage} from './hunt_page';
import {HuntResultsModule} from './hunt_results/module';
import {HuntPageRoutingModule} from './routing';

/**
 * Module for hunt view page.
 */
@NgModule({
  imports: [
    CommonModule, CopyButtonModule, HuntPageRoutingModule, HuntResultsModule,
    TitleEditorModule
  ],
  declarations: [HuntPage],
})
export class HuntPageModule {
}
