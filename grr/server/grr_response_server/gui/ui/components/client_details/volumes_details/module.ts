import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';

import {VolumesDetails} from './volumes_details';

/**
 * Module for the users details component.
 */
@NgModule({
  imports: [
    CommonModule,
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
