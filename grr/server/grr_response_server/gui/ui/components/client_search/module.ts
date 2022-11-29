import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatTableModule} from '@angular/material/table';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {SubmitOnMetaEnterModule} from '../form/submit_on_meta_enter/submit_on_meta_enter_module';
import {InfiniteListModule} from '../helpers/infinite_list/infinite_list_module';
import {OnlineChipModule} from '../online_chip/module';
import {TimestampModule} from '../timestamp/module';

import {ClientSearch} from './client_search';
import {ClientSearchRoutingModule} from './routing';
import {SearchBox} from './search_box';

/**
 * Module for the client search results page and related components.
 */
@NgModule({
  imports: [
    // Core Angular modules.
    BrowserAnimationsModule,
    RouterModule,
    FormsModule,
    ReactiveFormsModule,

    // Angular Material modules.
    MatAutocompleteModule,
    MatButtonModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSidenavModule,
    MatTableModule,
    MatTooltipModule,

    // GRR modules.
    ClientSearchRoutingModule,
    InfiniteListModule,
    OnlineChipModule,
    SubmitOnMetaEnterModule,
    TimestampModule,
  ],
  declarations: [
    ClientSearch,
    SearchBox,
  ],
  exports: [
    SearchBox,
  ]
})
export class ClientSearchModule {
}
