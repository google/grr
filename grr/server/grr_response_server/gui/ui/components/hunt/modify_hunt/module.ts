import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
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
    MatButtonModule,
    MatChipsModule,
    MatDialogModule,
    MatDividerModule,
    MatIconModule,
    MatListModule,
    MatProgressSpinnerModule,
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