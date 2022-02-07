import {ChangeDetectionStrategy, Component, OnDestroy, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {combineLatest} from 'rxjs';
import {map, shareReplay, startWith} from 'rxjs/operators';

import {LaunchBinaryArgs} from '../../lib/api/api_interfaces';
import {Binary, BinaryType} from '../../lib/models/flow';
import {observeOnDestroy} from '../../lib/reactive';
import {compareAlphabeticallyBy} from '../../lib/type_utils';
import {ConfigGlobalStore} from '../../store/config_global_store';

import {FlowArgumentForm} from './form_interface';


const BINARY: keyof LaunchBinaryArgs = 'binary';

const REQUIRED_BINARY_PREFIX = 'aff4:/config/executables/';

/** Form that configures a LaunchBinary flow. */
@Component({
  templateUrl: './launch_binary_form.ng.html',
  styleUrls: ['./launch_binary_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LaunchBinaryForm extends
    FlowArgumentForm<LaunchBinaryArgs> implements OnInit, OnDestroy {
  readonly form = new FormGroup({
    [BINARY]: new FormControl(),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map(values => ({
            ...this.defaultFlowArgs,
            [BINARY]: values[BINARY],
          })),
      shareReplay(1),
  );
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

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
        this.form.controls[BINARY].valueChanges.pipe(startWith('')),
      ])
          .pipe(
              map(([entries, searchString]) => {
                searchString = searchString.toLowerCase();
                return entries.filter(
                    b => b.path.toLowerCase().includes(searchString));
              }),
          );

  readonly ngOnDestroy = observeOnDestroy(this);

  constructor(private readonly configGlobalStore: ConfigGlobalStore) {
    super();
  }

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }

  trackBinary(index: number, entry: Binary) {
    return entry.path;
  }

  selectBinary(binary: string) {
    this.form.patchValue({[BINARY]: binary});
  }
}
