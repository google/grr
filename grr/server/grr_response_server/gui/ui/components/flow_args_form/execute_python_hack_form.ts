import {ChangeDetectionStrategy, Component, OnDestroy, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {combineLatest} from 'rxjs';
import {map, shareReplay, startWith} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ExecutePythonHackArgs} from '../../lib/api/api_interfaces';
import {Binary, BinaryType} from '../../lib/models/flow';
import {observeOnDestroy} from '../../lib/reactive';
import {compareAlphabeticallyBy} from '../../lib/type_utils';
import {ConfigGlobalStore} from '../../store/config_global_store';


const HACK_NAME: keyof ExecutePythonHackArgs = 'hackName';

/** Form that configures a ExecutePythonHack flow. */
@Component({
  templateUrl: './execute_python_hack_form.ng.html',
  styleUrls: ['./execute_python_hack_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecutePythonHackForm extends
    FlowArgumentForm<ExecutePythonHackArgs> implements OnInit, OnDestroy {
  readonly form = new FormGroup({
    [HACK_NAME]: new FormControl(),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map(values => ({
            ...this.defaultFlowArgs,
            [HACK_NAME]: values[HACK_NAME],
          })),
      shareReplay(1),
  );
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

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
        this.form.controls[HACK_NAME].valueChanges.pipe(startWith('')),
      ])
          .pipe(
              map(([entries, searchString]) => {
                searchString = searchString.toLowerCase();
                return entries.filter(
                    b => b.path.toLowerCase().includes(searchString));
              }),
          );

  readonly selectedHack$ =
      combineLatest([
        this.hacks$,
        this.form.controls[HACK_NAME].valueChanges,
      ])
          .pipe(
              map(([entries, searchString]) =>
                      entries.find(entry => entry.path === searchString)),
              startWith(undefined),
          );

  readonly ngOnDestroy = observeOnDestroy(this);

  constructor(private readonly configGlobalStore: ConfigGlobalStore) {
    super();
  }

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }

  trackHack(index: number, entry: Binary) {
    return entry.path;
  }

  selectHack(hackName: string) {
    this.form.patchValue({[HACK_NAME]: hackName});
  }
}
