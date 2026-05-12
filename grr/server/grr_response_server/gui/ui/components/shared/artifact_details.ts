import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatTreeModule} from '@angular/material/tree';

import {ArtifactDescriptor, SourceType} from '../../lib/models/flow';
import {FriendlyArtifactTypePipe} from '../../pipes/friendly_artifact_type/friendly_artifact_type';
import {
  GlobExplanationMode,
  GlobExpressionExplanation,
} from './form/glob_expression_form_field/glob_expression_explanation';

/** Component that displays the details of an artifact. */
@Component({
  selector: 'artifact-details',
  templateUrl: './artifact_details.ng.html',
  styleUrls: ['./artifact_details.scss'],
  imports: [
    CommonModule,
    FriendlyArtifactTypePipe,
    GlobExpressionExplanation,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    MatTreeModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactDetails {
  readonly artifact = input.required<ArtifactDescriptor>();
  readonly clientId = input<string | undefined>(undefined);

  protected readonly SourceType = SourceType;
  protected readonly GlobExplanationMode = GlobExplanationMode;

  hasChildren(_: number, node: ArtifactDescriptor): boolean {
    return node.artifacts!! && node.artifacts.length > 0;
  }

  childrenAccessor(node: ArtifactDescriptor): ArtifactDescriptor[] {
    return Array.from(node.artifacts ?? []);
  }
}
