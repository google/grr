import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatLegacyAutocompleteModule} from '@angular/material/legacy-autocomplete';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {RouterModule} from '@angular/router';

import {OsqueryQueryHelper} from './osquery_query_helper';
import {TableInfoItem} from './table_info_item';


/** Module for the OsqueryQueryHelper component. */
@NgModule({
  imports: [
    RouterModule,
    CommonModule,
    MatLegacyButtonModule,
    MatLegacyAutocompleteModule,
    MatLegacyTooltipModule,
    MatLegacyFormFieldModule,
    MatLegacyInputModule,
    MatLegacyDialogModule,
    ReactiveFormsModule,
  ],
  declarations: [
    OsqueryQueryHelper,
    TableInfoItem,
  ],
  exports: [
    OsqueryQueryHelper,
  ]
})
export class OsqueryQueryHelperModule {
}
