import {ChangeDetectionStrategy, Component} from '@angular/core';
import {UntypedFormArray, UntypedFormControl, UntypedFormGroup} from '@angular/forms';
import {combineLatest} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ExecutePythonHackArgs} from '../../lib/api/api_interfaces';
import {translateDict} from '../../lib/api_translation/primitive';
import {Binary, BinaryType} from '../../lib/models/flow';
import {compareAlphabeticallyBy} from '../../lib/type_utils';
import {ConfigGlobalStore} from '../../store/config_global_store';

declare interface Arg {
  key: string;
  value: string;
}

declare interface FormState {
  hackName: string;
  pyArgs: ReadonlyArray<Arg>;
}

declare interface ArgControl {
  key: UntypedFormControl;
  value: UntypedFormControl;
}

declare interface Controls {
  hackName: UntypedFormControl;
  pyArgs: UntypedFormArray;
}

/** Form that configures a ExecutePythonHack flow. */
@Component({
  templateUrl: './execute_python_hack_form.ng.html',
  styleUrls: ['./execute_python_hack_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class ExecutePythonHackForm extends
    FlowArgumentForm<ExecutePythonHackArgs, FormState, Controls> {
  override makeControls(): Controls {
    return {
      hackName: new UntypedFormControl(),
      pyArgs: new UntypedFormArray([]),
    };
  }

  get pyArgsFormGroups(): UntypedFormGroup[] {
    return this.controls.pyArgs.controls as UntypedFormGroup[];
  }

  getKeyValueControls(formGroup: UntypedFormGroup): ArgControl {
    return formGroup.controls as unknown as ArgControl;
  }

  override convertFlowArgsToFormState(flowArgs: ExecutePythonHackArgs):
      FormState {
    return {
      hackName: flowArgs.hackName ?? '',
      pyArgs: Array.from(translateDict(flowArgs.pyArgs ?? {}).entries())
                  .map(([k, v]) => ({key: String(k), value: String(v)})),
    };
  }

  override convertFormStateToFlowArgs(formState: FormState):
      ExecutePythonHackArgs {
    return {
      hackName: formState.hackName,
      pyArgs: formState.pyArgs.length ? {
        dat: formState.pyArgs.map(
            ({key, value}) => ({k: {string: key}, v: {string: value}}))
      } :
                                        undefined
    };
  }

  override resetFlowArgs(flowArgs: ExecutePythonHackArgs): void {
    const formState = this.convertFlowArgsToFormState(flowArgs);
    for (let i = 0; i < formState.pyArgs.length; i++) {
      this.addKeyValueFormControl();
    }
    super.resetFlowArgs(flowArgs);
  }

  // TODO: As future UX improvement, we could highlight Python
  // hacks that match the current client OS, since Python hacks are "bound" to
  // one OS on upload.
  readonly hacks$ = this.configGlobalStore.binaries$.pipe(
      map((binaries) =>
              Array
                  .from(binaries.filter(b => b.type === BinaryType.PYTHON_HACK))
                  .sort(compareAlphabeticallyBy(b => b.path))),
  );

  readonly filteredHacks$ =
      combineLatest([
        this.hacks$,
        this.controls.hackName.valueChanges.pipe(startWith('')),
      ])
          .pipe(
              map(([entries, searchString]) => {
                searchString = searchString?.toLowerCase() ?? '';
                return entries.filter(
                    b => b.path.toLowerCase().includes(searchString));
              }),
          );

  readonly selectedHack$ =
      combineLatest([
        this.hacks$,
        this.controls.hackName.valueChanges,
      ])
          .pipe(
              map(([entries, searchString]) =>
                      entries.find(entry => entry.path === searchString)),
              startWith(undefined),
          );

  constructor(private readonly configGlobalStore: ConfigGlobalStore) {
    super();
  }

  trackHack(index: number, entry: Binary) {
    return entry.path;
  }

  selectHack(hackName: string) {
    this.controls.hackName.setValue(hackName);
  }

  addKeyValueFormControl() {
    const argControl: ArgControl = {
      key: new UntypedFormControl(''),
      value: new UntypedFormControl(''),
    };
    this.controls.pyArgs.push(new UntypedFormGroup({...argControl}));
  }

  removeKeyValueFormControl(i: number) {
    this.controls.pyArgs.removeAt(i);
  }
}
