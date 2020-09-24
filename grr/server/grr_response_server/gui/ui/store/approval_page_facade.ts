import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {ConfigService} from '@app/components/config/config';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateApproval} from '@app/lib/api_translation/client';
import {combineLatest, Observable, timer} from 'rxjs';
import {filter, map, switchMap, switchMapTo, tap} from 'rxjs/operators';

import {ClientApproval} from '../lib/models/client';
import {isNonNull} from '../lib/preconditions';

interface ApprovalPageState {
  readonly selectedApprovalKey?: ApprovalKey;
  readonly approval?: ClientApproval;
}

interface ApprovalKey {
  readonly approvalId: string;
  readonly clientId: string;
  readonly requestor: string;
}

interface PollingConfig<K> {
  readonly pollingIntervalMs: number;
  readonly pollingEffect: () => void;
  readonly observable: Observable<K>;
}


class BaseComponentStore<T extends {}> extends ComponentStore<T> {
  constructor(state: T) {
    super(state);
  }

  protected setter<K extends keyof T>(key: K): (value: T[K]) => void {
    return this.updater((state, value) => ({...state, [key]: value}));
  }

  protected selectKey<K extends keyof T>(key: K): Observable<T[K]> {
    return this.select((state) => state[key]);
  }

  protected poll<T>(config: PollingConfig<T>) {
    return combineLatest([
             timer(0, config.pollingIntervalMs).pipe(tap(() => {
               config.pollingEffect();
             })),
             config.observable,
           ])
        .pipe(map(([, value]) => value));
  }
}

/**
 * ComponentStore implementation used by the ApprovalPageFacade. Shouldn't be
 * used directly. Declared as an exported global symbol to make dependency
 * injection possible.
 */
@Injectable({
  providedIn: 'root',
})
export class ApprovalPageStore extends BaseComponentStore<ApprovalPageState> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configService: ConfigService,
  ) {
    super({});
  }

  private readonly updateApproval = this.setter('approval');

  readonly selectApproval = this.setter('selectedApprovalKey');

  private readonly fetchApproval = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.selectKey('selectedApprovalKey')),
          filter(isNonNull),
          switchMap(({clientId, requestor, approvalId}) => {
            return this.httpApiService.fetchClientApproval(
                {clientId, requestor, approvalId});
          }),
          map(translateApproval),
          tap(approval => {
            this.updateApproval(approval);
          }),
          ));

  /** An observable emitting all ScheduledFlows for the client. */
  readonly approval$: Observable<ClientApproval> =
      this.poll({
            pollingIntervalMs:
                this.configService.config.approvalPollingIntervalMs,
            pollingEffect: this.fetchApproval,
            observable: this.selectKey('approval'),
          })
          .pipe(
              filter(isNonNull),
          );

  readonly grantApproval = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.selectKey('selectedApprovalKey')),
          filter(isNonNull),
          switchMap(({clientId, requestor, approvalId}) => {
            return this.httpApiService.grantClientApproval(
                {clientId, requestor, approvalId});
          }),
          map(translateApproval),
          tap(approval => {
            this.updateApproval(approval);
          }),
          ));
}

/** Store that loads and stores data for the approval page. */
@Injectable({
  providedIn: 'root',
})
export class ApprovalPageFacade {
  constructor(private readonly store: ApprovalPageStore) {}

  readonly approval$: Observable<ClientApproval> = this.store.approval$;

  selectApproval(approvalKey: ApprovalKey): void {
    this.store.selectApproval(approvalKey);
  }

  grantApproval(): void {
    this.store.grantApproval();
  }
}
