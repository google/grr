import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyAutocompleteModule} from '@angular/material/legacy-autocomplete';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyCheckboxModule} from '@angular/material/legacy-checkbox';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatLegacySelectModule} from '@angular/material/legacy-select';
import {MatLegacyTableModule} from '@angular/material/legacy-table';
import {MatLegacyTabsModule} from '@angular/material/legacy-tabs';

import {FileModeModule} from '../../../data_renderers/file_mode/file_mode_module';
import {ExpandableHashModule} from '../../../expandable_hash/module';
import {HelpersModule} from '../../../flow_details/helpers/module';
import {CopyButtonModule} from '../../../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../../../helpers/drawer_link/drawer_link_module';
import {FilterPaginate} from '../../../helpers/filter_paginate/filter_paginate';
import {HumanReadableSizeModule} from '../../../human_readable_size/module';
import {TimestampModule} from '../../../timestamp/module';
import {UserImageModule} from '../../../user_image/module';
import {HuntResultsTable} from '../hunt_results_table/hunt_results_table';

import {HuntResults} from './hunt_results';


@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,

    MatLegacyAutocompleteModule,
    MatLegacyButtonModule,
    MatLegacyCardModule,
    MatLegacyCheckboxModule,
    MatLegacyFormFieldModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyMenuModule,
    MatLegacyProgressSpinnerModule,
    MatLegacySelectModule,
    MatLegacyTableModule,
    MatLegacyTabsModule,

    CopyButtonModule,
    DrawerLinkModule,
    ExpandableHashModule,
    FileModeModule,
    FilterPaginate,
    HelpersModule,
    HumanReadableSizeModule,
    TimestampModule,
    UserImageModule,

    HuntResultsTable,
  ],
  declarations: [
    HuntResults,
  ],
  exports: [
    HuntResults,
  ],
})
export class HuntResultsModule {
}
