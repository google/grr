import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSelectModule} from '@angular/material/select';
import {MatTableModule} from '@angular/material/table';
import {MatTabsModule} from '@angular/material/tabs';

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
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    CommonModule,
    CopyButtonModule,
    DrawerLinkModule,
    ExpandableHashModule,
    FileModeModule,
    FilterPaginate,
    FormsModule,
    HelpersModule,
    HumanReadableSizeModule,
    HuntResultsTable,
    MatAutocompleteModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
    MatTabsModule,
    ReactiveFormsModule,
    TimestampModule,
    UserImageModule,
    // keep-sorted end
    // clang-format on
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
