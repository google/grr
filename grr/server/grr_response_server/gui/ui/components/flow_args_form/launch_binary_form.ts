import {ChangeDetectionStrategy, Component} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';
import {combineLatest} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

import {LaunchBinaryArgs} from '../../lib/api/api_interfaces';
import {Binary, BinaryType} from '../../lib/models/flow';
import {compareAlphabeticallyBy} from '../../lib/type_utils';
import {ConfigGlobalStore} from '../../store/config_global_store';

import {Controls, FlowArgumentForm} from './form_interface';


const REQUIRED_BINARY_PREFIX = 'aff4:/config/executables/';

declare interface FormState {
  binary: string;
  commandLine: string;
}

/** Form that configures a LaunchBinary flow. */
@Component({
  templateUrl: './launch_binary_form.ng.html',
  styleUrls: ['./launch_binary_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LaunchBinaryForm extends
    FlowArgumentForm<LaunchBinaryArgs, FormState> {
  // TODO: As future UX improvement, we could highlight binaries
  // that match the current client OS, since binaries are "bound" to one OS on
  // upload.
  readonly binaries$ = this.configGlobalStore.binaries$.pipe(
      map((binaries) =>
              Array.from(binaries.filter(b => b.type === BinaryType.EXECUTABLE))
                  .map(b => ({...b, path: REQUIRED_BINARY_PREFIX + b.path}))
                  .sort(compareAlphabeticallyBy(b => b.path))),
  );

  readonly filteredBinaries$ =
      combineLatest([
        this.binaries$,
        this.controls.binary.valueChanges.pipe(startWith('')),
      ])
          .pipe(
              map(([entries, searchString]) => {
                searchString = searchString?.toLowerCase() ?? '';
                return entries.filter(
                    b => b.path.toLowerCase().includes(searchString));
              }),
          );

  constructor(private readonly configGlobalStore: ConfigGlobalStore) {
    super();
  }

  override makeControls(): Controls<FormState> {
    return {
      binary: new UntypedFormControl(''),
      commandLine: new UntypedFormControl(''),
    };
  }

  override convertFlowArgsToFormState(flowArgs: LaunchBinaryArgs): FormState {
    return {
      binary: flowArgs.binary ?? '',
      commandLine: flowArgs.commandLine ?? '',
    };
  }

  override convertFormStateToFlowArgs(formState: FormState): LaunchBinaryArgs {
    return formState;
  }

  trackBinary(index: number, entry: Binary) {
    return entry.path;
  }

  selectBinary(binary: string) {
    this.controls.binary.setValue(binary);
  }
}
