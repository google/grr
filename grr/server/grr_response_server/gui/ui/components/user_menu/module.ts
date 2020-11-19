import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {UserImageModule} from '../user_image/module';

import {UserMenu} from './user_menu';


/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatTooltipModule,
    ReactiveFormsModule,
    RouterModule,
    UserImageModule,
  ],
  declarations: [
    UserMenu,
  ],
  exports: [
    UserMenu,
  ],
})
export class UserMenuModule {
}
