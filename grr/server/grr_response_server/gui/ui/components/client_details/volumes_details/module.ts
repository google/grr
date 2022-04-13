import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';

import {VolumesDetails} from './volumes_details';

/**
 * Module for the users details component.
 */
@NgModule({
  imports: [
    CommonModule,
    CopyButtonModule,
    TimestampModule,
    HumanReadableSizeModule,
  ],
  declarations: [
    VolumesDetails,
  ],
  exports: [
    VolumesDetails,
  ]
})
export class VolumesDetailsModule {
}
