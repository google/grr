import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';
import {MatButtonModule} from '@angular/material/button';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatInputModule} from '@angular/material/input';
import {ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatDialogModule} from '@angular/material/dialog';

import {OsqueryQueryHelper} from './osquery_query_helper';
import {TableInfoItem} from './table_info_item';


/** Module for the OsqueryQueryHelper component. */
@NgModule({
  imports: [
    RouterModule,
    CommonModule,
    MatButtonModule,
    MatAutocompleteModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    ReactiveFormsModule,
  ],
  declarations: [
    OsqueryQueryHelper,
    TableInfoItem,
  ],
  exports: [
    OsqueryQueryHelper,
  ],
})
export class OsqueryQueryHelperModule {
}
