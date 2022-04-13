import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable, of} from 'rxjs';
import {concatMap, filter, map, mapTo, shareReplay, startWith, switchMap, withLatestFrom} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {translateScheduledFlow} from '../lib/api_translation/flow';
import {ScheduledFlow} from '../lib/models/flow';
import {isNonNull} from '../lib/preconditions';

interface State {
  readonly creator?: string;
  readonly clientId?: string;
}

/** Global store for showing scheduled flows. */
@Injectable({
  providedIn: 'root',
})
export class ScheduledFlowGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new ScheduledFlowComponentStore(this.httpApiService);

  selectSource(source: {creator?: string, clientId?: string}) {
    this.store.selectSource(source);
  }

  unscheduleFlow(scheduledFlowId: string) {
    this.store.unscheduleFlow(scheduledFlowId);
  }

  readonly scheduledFlows$: Observable<ReadonlyArray<ScheduledFlow>> =
      this.store.scheduledFlows$;
}

class ScheduledFlowComponentStore extends ComponentStore<State> {
  constructor(
      private readonly httpApiService: HttpApiService,
  ) {
    super({});
  }

  readonly selectSource = this.updater<{creator?: string, clientId?: string}>(
      (state, {creator, clientId}) => {
        return {
          creator,
          clientId,
        };
      });

  readonly scheduledFlows$ =
      this.select(({clientId, creator}) => ({clientId, creator}))
          .pipe(
              switchMap(
                  ({clientId, creator}) => (clientId && creator) ?
                      this.httpApiService.subscribeToScheduledFlowsForClient(
                          clientId, creator) :
                      of([])),
              startWith([]),
              map(apiScheduledFlows =>
                      apiScheduledFlows.map(translateScheduledFlow)),
              shareReplay({bufferSize: 1, refCount: true}),
          );

  /** Unschedules a previously scheduled flow. */
  readonly unscheduleFlow = this.effect<string>(
      obs$ => obs$.pipe(
          withLatestFrom(this.select(state => state.clientId)),
          filter((args): args is[string, string] => isNonNull(args[1])),
          concatMap(
              ([scheduledFlowId, clientId]) =>
                  this.httpApiService.unscheduleFlow(clientId, scheduledFlowId)
                      .pipe(mapTo(scheduledFlowId))),
          ));
}
