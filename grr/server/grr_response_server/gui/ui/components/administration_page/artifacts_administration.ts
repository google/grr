import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatDialog, MatDialogConfig} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatListModule} from '@angular/material/list';
import {RouterModule} from '@angular/router';

import {
  extendArtifactDescriptor,
  ExtendedArtifactDescriptor,
} from '../../lib/models/flow';
import {GlobalStore} from '../../store/global_store';
import {SplitPanel} from '../shared/split_panel/split_panel';
import {CreateArtifactDialog} from './create_artifact_dialog';

/** Component that displays the artifacts administration page. */
@Component({
  selector: 'artifacts-administration',
  templateUrl: './artifacts_administration.ng.html',
  styleUrls: ['./artifacts_administration.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatFormFieldModule,
    ReactiveFormsModule,
    SplitPanel,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactsAdministration {
  protected readonly globalStore = inject(GlobalStore);
  private readonly dialog = inject(MatDialog);

  protected readonly extendedArtifactDescriptors = computed<
    ExtendedArtifactDescriptor[]
  >(() => {
    return Array.from(this.globalStore.artifactDescriptorMap().values(), (ad) =>
      extendArtifactDescriptor(ad),
    ).sort((a, b) => a.name.localeCompare(b.name));
  });

  protected readonly searchFormControl = new FormControl('', {
    nonNullable: true,
  });

  protected openCreateArtifactDialog() {
    const dialogConfig = new MatDialogConfig();
    dialogConfig.minWidth = '60vw';
    dialogConfig.height = '70vh';
    dialogConfig.autoFocus = false;
    this.dialog.open(CreateArtifactDialog, dialogConfig);
  }
}
