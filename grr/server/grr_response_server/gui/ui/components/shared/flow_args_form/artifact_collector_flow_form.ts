import {A11yModule} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import {
  AbstractControl,
  FormControl,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';
import {MatTreeModule} from '@angular/material/tree';

import {ArtifactCollectorFlowArgs} from '../../../lib/api/api_interfaces';
import {safeTranslateOperatingSystem} from '../../../lib/api/translation/flow';
import {
  ArtifactDescriptor,
  extendArtifactDescriptor,
  ExtendedArtifactDescriptor,
} from '../../../lib/models/flow';
import {HumanReadableOsPipe} from '../../../pipes/operating_system/human_readable_os_pipe';
import {GlobalStore} from '../../../store/global_store';
import {ArtifactDetails} from '../../shared/artifact_details';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls(validator: ValidatorFn) {
  return {
    artifactName: new FormControl<string>('', [validator]),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a ArtifactCollectorFlow. */
@Component({
  selector: 'artifact-collector-flow-form',
  templateUrl: './artifact_collector_flow_form.ng.html',
  styleUrls: [
    './flow_args_form_styles.scss',
    './artifact_collector_flow_form.scss',
  ],
  imports: [
    A11yModule,
    ArtifactDetails,
    CommonModule,
    HumanReadableOsPipe,
    MatAutocompleteModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
    MatButtonModule,
    MatTreeModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactCollectorFlowForm extends FlowArgsFormInterface<
  ArtifactCollectorFlowArgs,
  Controls
> {
  readonly globalStore = inject(GlobalStore);

  readonly clientOs = input<string | undefined>(undefined);
  readonly clientId = input<string | undefined>(undefined);

  protected selectedArtifact = signal<ArtifactDescriptor | undefined>(
    undefined,
  );

  private readonly extendedArtifactDescriptors = computed<
    ExtendedArtifactDescriptor[]
  >(() => {
    const clientOs = safeTranslateOperatingSystem(this.clientOs());
    return Array.from(this.globalStore.artifactDescriptorMap().values(), (ad) =>
      extendArtifactDescriptor(ad, clientOs),
    );
  });

  protected readonly filteredArtifactDescriptors = computed<
    ExtendedArtifactDescriptor[]
  >(() => {
    return this.extendedArtifactDescriptors().filter((ad) =>
      ad.matchesInput(this.formValues()?.artifactName ?? ''),
    );
  });

  override makeControls(): Controls {
    return makeControls((control: AbstractControl): ValidationErrors | null => {
      if (
        control.value &&
        this.globalStore.artifactDescriptorMap().has(control.value)
      ) {
        return null;
      }
      // Invalid: The input does not match any artifact of the list of available
      // artifacts.
      return {'optionNotSelected': true};
    });
  }

  override convertFlowArgsToFormState(
    flowArgs: ArtifactCollectorFlowArgs,
  ): ControlValues<Controls> {
    return {
      artifactName:
        flowArgs.artifactList!! && flowArgs.artifactList.length > 0
          ? flowArgs.artifactList?.[0]
          : this.controls.artifactName.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): ArtifactCollectorFlowArgs {
    return {
      artifactList: formState.artifactName ? [formState.artifactName] : [],
    };
  }

  /**
   * Selects an artifact from the autocomplete list.
   */
  selectArtifact(artifact: string): void {
    this.controls.artifactName.setValue(artifact);
    this.selectedArtifact.set(
      this.globalStore.artifactDescriptorMap().get(artifact),
    );
  }

  override resetFlowArgs(flowArgs: ArtifactCollectorFlowArgs) {
    super.resetFlowArgs(flowArgs);

    const artifact = flowArgs.artifactList?.[0];
    if (artifact) {
      this.selectedArtifact.set(
        this.globalStore.artifactDescriptorMap().get(artifact),
      );
    }
  }
}
