import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';
import {RouterModule} from '@angular/router';

import {HuntHelp} from './hunt_help';
import {HuntHelpRoutingModule} from './routing';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    MatLegacyDialogModule,
    MatDividerModule,
    MatIconModule,
    HuntHelpRoutingModule,
  ],
  declarations: [
    HuntHelp,
  ],
  exports: [
    HuntHelp,
  ]
})
export class HuntHelpModule {
}
