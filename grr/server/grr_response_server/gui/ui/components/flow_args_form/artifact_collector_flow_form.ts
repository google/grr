import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {map, shareReplay} from 'rxjs/operators';

import {ArtifactCollectorFlowArgs} from '../../lib/api/api_interfaces';

/** Form that configures a ArtifactCollectorFlow. */
@Component({
  selector: 'artifact-collector-flow-form',
  templateUrl: './artifact_collector_flow_form.ng.html',
  styleUrls: ['./artifact_collector_flow_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactCollectorFlowForm extends
    FlowArgumentForm<ArtifactCollectorFlowArgs> implements OnInit {
  readonly form = new FormGroup({
    artifactName: new FormControl(),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map(values => ({
            ...this.defaultFlowArgs,
            artifactList: [values.artifactName],
            applyParsers: false,
          })),
      shareReplay(1),
  );
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue({
      artifactName: this.defaultFlowArgs.artifactList?.[0] ?? '',
    });
  }
}
