import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {MatListModule} from '@angular/material/list';
import {RouterModule} from '@angular/router';

import {SplitPanel} from '../shared/split_panel/split_panel';

/** Component that displays the administration page. */
@Component({
  selector: 'administration-page',
  templateUrl: './administration_page.ng.html',
  imports: [CommonModule, RouterModule, MatListModule, SplitPanel],
  styleUrls: ['./administration_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdministrationPage {}
