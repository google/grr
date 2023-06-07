import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyAutocompleteModule} from '@angular/material/legacy-autocomplete';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyTableModule} from '@angular/material/legacy-table';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {MatSidenavModule} from '@angular/material/sidenav';
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
    MatLegacyAutocompleteModule,
    MatLegacyButtonModule,
    MatLegacyChipsModule,
    MatLegacyFormFieldModule,
    MatIconModule,
    MatLegacyInputModule,
    MatSidenavModule,
    MatLegacyTableModule,
    MatLegacyTooltipModule,

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
