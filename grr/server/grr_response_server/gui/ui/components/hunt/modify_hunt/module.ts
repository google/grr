import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';
import {MatLegacyListModule} from '@angular/material/legacy-list';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {RouterModule} from '@angular/router';

import {RolloutFormModule} from '../../../components/hunt/rollout_form/module';

import {ModifyHunt} from './modify_hunt';
import {ModifyHuntRoutingModule} from './routing';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    MatLegacyButtonModule,
    MatLegacyChipsModule,
    MatLegacyDialogModule,
    MatDividerModule,
    MatIconModule,
    MatLegacyListModule,
    MatLegacyProgressSpinnerModule,
    ModifyHuntRoutingModule,
    RolloutFormModule,
  ],
  declarations: [
    ModifyHunt,
  ],
  exports: [
    ModifyHunt,
  ]
})
export class ModifyHuntModule {
}