import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {RouterModule} from '@angular/router';
import {BehaviorSubject, combineLatest, Observable} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

import {Hunt} from '../../../lib/models/hunt';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {FlowArgsViewData} from '../../flow_args_view/flow_args_view';
import {FlowArgsViewModule} from '../../flow_args_view/module';
import {HelpersModule} from '../../flow_details/helpers/module';
import {ColorScheme} from '../../flow_details/helpers/result_accordion';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';

/** Component that displays a hunt request. */
@Component({
  selector: 'hunt-flow-arguments',
  templateUrl: './hunt_flow_arguments.ng.html',
  styleUrls: ['./hunt_flow_arguments.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    CopyButtonModule,
    FlowArgsViewModule,
    HelpersModule,
    RouterModule,
  ],
  standalone: true,
})
export class HuntFlowArguments {
  protected readonly hunt$ = new BehaviorSubject<Hunt|null>(null);
  @Input()
  set hunt(hunt: Hunt|null) {
    this.hunt$.next(hunt);
  }
  get hunt() {
    return this.hunt$.value;
  }

  protected readonly ColorScheme = ColorScheme;

  constructor(private readonly configGlobalStore: ConfigGlobalStore) {}

  protected readonly flowArgsViewData$: Observable<FlowArgsViewData|null> =
      combineLatest([this.hunt$, this.configGlobalStore.flowDescriptors$])
          .pipe(
              map(([hunt, flowDescriptors]):
                      FlowArgsViewData|null => {
                        const flowDescriptor =
                            flowDescriptors.get(hunt?.flowName ?? '');

                        if (!hunt?.flowArgs || !hunt?.flowName ||
                            !flowDescriptor) {
                          return null;
                        }

                        return {
                          flowDescriptor,
                          flowArgs: hunt?.flowArgs,
                        };
                      }),
              startWith(null as FlowArgsViewData|null),
          );
}
