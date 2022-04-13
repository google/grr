import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';

import {InterfacesDetails} from './interfaces_details';

/**
 * Module for the network interfaces details component.
 */
@NgModule({
  imports: [
    CommonModule,
    CopyButtonModule,
  ],
  declarations: [
    InterfacesDetails,
  ],
  exports: [
    InterfacesDetails,
  ]
})
export class InterfacesDetailsModule {
}
