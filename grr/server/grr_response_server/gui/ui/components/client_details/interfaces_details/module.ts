import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {InterfacesDetails} from './interfaces_details';

/**
 * Module for the network interfaces details component.
 */
@NgModule({
  imports: [
    CommonModule,
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
