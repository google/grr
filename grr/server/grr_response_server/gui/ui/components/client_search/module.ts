import {NgModule} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';
import {MatTableModule} from '@angular/material/table';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {OnlineChipModule} from '../online_chip/module';
import {TimestampModule} from '../timestamp/module';

import {ClientSearch} from './client_search';
import {ClientSearchRoutingModule} from './routing';

/**
 * Module for the client search results page and related components.
 */
@NgModule({
  imports: [
    // Core Angular modules.
    BrowserAnimationsModule,
    RouterModule,

    // Angular Material modules.
    MatChipsModule,
    MatTableModule,

    // GRR modules.
    ClientSearchRoutingModule,
    TimestampModule,
    OnlineChipModule,

  ],
  declarations: [
    ClientSearch,
  ],
})
export class ClientSearchModule {
}
