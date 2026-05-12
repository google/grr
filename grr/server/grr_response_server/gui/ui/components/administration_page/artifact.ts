import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input as routerInput,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDialog, MatDialogConfig} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';

import {ArtifactDescriptor} from '../../lib/models/flow';
import {GlobalStore} from '../../store/global_store';
import {ArtifactDetails} from '../shared/artifact_details';
import {
  DeleteArtifactDialog,
  DeleteArtifactDialogData,
} from './delete_artifact_dialog';

/** Component that displays the artifacts. */
@Component({
  selector: 'artifact',
  templateUrl: './artifact.ng.html',
  styleUrls: ['./artifact.scss'],
  imports: [
    ArtifactDetails,
    CommonModule,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Artifact {
  protected readonly globalStore = inject(GlobalStore);
  private readonly dialog = inject(MatDialog);

  artifactName = routerInput<string | undefined>();

  protected readonly artifact = computed(() => {
    const artifactName = this.artifactName();
    if (artifactName === undefined) {
      return undefined;
    }
    return this.globalStore.artifactDescriptorMap().get(artifactName);
  });

  openDeleteArtifactDialog(artifact: ArtifactDescriptor) {
    const dialogData: DeleteArtifactDialogData = {
      artifact,
      onDeleteArtifact: () => {
        this.globalStore.deleteArtifact(artifact.name);
      },
    };
    const dialogConfig = new MatDialogConfig();
    dialogConfig.data = dialogData;
    this.dialog.open(DeleteArtifactDialog, dialogConfig);
  }
}
