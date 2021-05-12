import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {ConfigService} from '@app/components/config/config';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateScheduledFlow} from '@app/lib/api_translation/flow';
import {ScheduledFlow} from '@app/lib/models/flow';
import {Observable} from 'rxjs';
import {concatMap, exhaustMap, filter, map, mapTo, shareReplay, tap, withLatestFrom} from 'rxjs/operators';

import {poll} from '../lib/polling';
import {isNonNull} from '../lib/preconditions';

interface State {
  readonly creator?: string;
  readonly clientId?: string;
  readonly scheduledFlows?: ScheduledFlow[];
}

/** Interface for ScheduledFlowStore. */
@Injectable({
  providedIn: 'root',
})
export class ScheduledFlowFacade {
  constructor(private readonly store: ScheduledFlowStore) {}

  selectSource(source: {creator?: string, clientId?: string}) {
    this.store.selectSource(source);
  }

  unscheduleFlow(scheduledFlowId: string) {
    this.store.unscheduleFlow(scheduledFlowId);
  }

  readonly scheduledFlows$: Observable<ReadonlyArray<ScheduledFlow>> =
      this.store.scheduledFlows$;
}

/** Do not use. Use ScheduledFlowFacade instead. */
@Injectable({
  providedIn: 'root',
})
export class ScheduledFlowStore extends ComponentStore<State> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configService: ConfigService,
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

  private readonly listScheduledFlows = this.effect<void>(
      obs$ => obs$.pipe(
          withLatestFrom(this.state$),
          map(([, {clientId, creator}]) => ({clientId, creator})),
          filter(
              (args): args is {clientId: string, creator: string} =>
                  isNonNull(args.clientId) && isNonNull(args.creator)),
          exhaustMap(
              ({creator, clientId}) =>
                  this.httpApiService.listScheduledFlows(clientId, creator)),
          map(apiScheduledFlows =>
                  apiScheduledFlows.map(translateScheduledFlow)),
          tap(scheduledFlows => {
            this.updateScheduledFlows(scheduledFlows);
          }),
          ));

  /** An observable emitting all ScheduledFlows for the client. */
  readonly scheduledFlows$: Observable<ReadonlyArray<ScheduledFlow>> =
      poll({
        pollIntervalMs: this.configService.config.flowListPollingIntervalMs,
        pollEffect: this.listScheduledFlows,
        selector: this.select(state => state.scheduledFlows),
      })
          .pipe(
              filter(isNonNull),
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
          tap((scheduledFlowId) => {
            this.deleteScheduledFlow(scheduledFlowId);
          }),
          ));

  private readonly updateScheduledFlows =
      this.updater<ScheduledFlow[]>((state, scheduledFlows) => ({
                                      ...state,
                                      scheduledFlows,
                                    }));

  private readonly deleteScheduledFlow =
      this.updater<string>((state, scheduledFlowId) => {
        return {
          ...state,
          scheduledFlows: state.scheduledFlows?.filter(
              sf => sf.scheduledFlowId !== scheduledFlowId)
        };
      });
}
