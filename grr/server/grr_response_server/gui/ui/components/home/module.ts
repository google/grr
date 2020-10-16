import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {ApiModule} from '@app/lib/api/module';

import {OnlineChipModule} from '../online_chip/module';
import {TimestampModule} from '../timestamp/module';

import {Home} from './home';
import {HomeRoutingModule} from './routing';
import {SearchBox} from './search_box';


/**
 * Module for the home page and related components.
 */
@NgModule({
  imports: [
    // Core Angular modules.
    BrowserAnimationsModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,

    // Angular Material modules.
    MatAutocompleteModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatSidenavModule,
    MatToolbarModule,

    // GRR modules.
    HomeRoutingModule,
    ApiModule,
    TimestampModule,
    OnlineChipModule,
  ],
  declarations: [Home, SearchBox],
})
export class HomeModule {
}
