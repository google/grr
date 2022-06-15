import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormArray, FormControl, FormGroup} from '@angular/forms';
import {combineLatest} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ExecutePythonHackArgs} from '../../lib/api/api_interfaces';
import {translateDict} from '../../lib/api_translation/primitive';
import {Binary, BinaryType} from '../../lib/models/flow';
import {compareAlphabeticallyBy} from '../../lib/type_utils';
import {ConfigGlobalStore} from '../../store/config_global_store';

declare interface ArgControl {
  key: FormControl<string>;
  value: FormControl<string>;
}

function makeControls() {
  return {
    hackName: new FormControl('', {nonNullable: true}),
    pyArgs: new FormArray<FormGroup<ArgControl>>([]),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a ExecutePythonHack flow. */
@Component({
  templateUrl: './execute_python_hack_form.ng.html',
  styleUrls: ['./execute_python_hack_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class ExecutePythonHackForm extends
    FlowArgumentForm<ExecutePythonHackArgs, Controls> {
  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: ExecutePythonHackArgs) {
    return {
      hackName: flowArgs.hackName ?? this.controls.hackName.defaultValue,
      pyArgs: Array.from(translateDict(flowArgs.pyArgs ?? {}).entries())
                  .map(([k, v]) => ({key: String(k), value: String(v)})),
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
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
    this.controls.pyArgs.push(new FormGroup({
      key: new FormControl('', {nonNullable: true}),
      value: new FormControl('', {nonNullable: true}),
    }));
  }

  removeKeyValueFormControl(i: number) {
    this.controls.pyArgs.removeAt(i);
  }
}
