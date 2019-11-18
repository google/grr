import {NgModule} from '@angular/core';
import {MatTableModule} from '@angular/material/table';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

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
    MatTableModule,

    // GRR modules.
    ClientSearchRoutingModule,
  ],
  declarations: [
    ClientSearch,
  ],
})
export class ClientSearchModule {
}
