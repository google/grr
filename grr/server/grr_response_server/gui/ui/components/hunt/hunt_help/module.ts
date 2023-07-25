import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {RouterModule} from '@angular/router';

import {HuntHelp} from './hunt_help';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    CommonModule,
    MatDialogModule,
    MatDividerModule,
    MatIconModule,
    RouterModule,
    // keep-sorted end
    // clang-format on
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
