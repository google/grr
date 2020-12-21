import {EventEmitter, Input, OnDestroy, Output} from '@angular/core';
import {FlowListEntry, FlowResultsQuery} from '@app/lib/models/flow';
import {ReplaySubject, Subject} from 'rxjs';
import {map} from 'rxjs/operators';
import {makeLegacyLink} from '../../../lib/routing';

/**
 * Flow results query without the flowId field.
 *
 * Flow results queries issues by details plugins are equivalent to the
 * FlowResultsQuery interface, but there should be no need for the user to
 * provide the flowId field, since it can/should be filled in automatically.
 */
export type FlowResultsQueryWithoutFlowId = Omit<FlowResultsQuery, 'flowId'>;

/**
 * Base class for all flow details plugins.
 */
export abstract class Plugin implements OnDestroy {
  private flowListEntryValue?: FlowListEntry;

  /**
   * Subject emitting new FlowListEntry values on every "flowListEntry"
   * binding change.
   */
  readonly flowListEntry$ = new ReplaySubject<FlowListEntry>(1);

  /**
   * Event that is triggered when additional flow results data is needed to
   * be present in the flowListEntry.
   */
  @Output()
  flowResultsQuery = new EventEmitter<FlowResultsQueryWithoutFlowId>();

  readonly fallbackUrl$ = this.flowListEntry$.pipe(map(fle => {
    const {flowId, clientId} = fle.flow;
    return makeLegacyLink(`#/clients/${clientId}/flows/${flowId}`);
  }));

  readonly unsubscribe$ = new Subject<void>();

  /**
   * Flow input binding containing flow data information to display.
   */
  @Input()
  set flowListEntry(value: FlowListEntry) {
    this.flowListEntryValue = value;
    this.flowListEntry$.next(value);
  }

  get flowListEntry(): FlowListEntry {
    return this.flowListEntryValue!;
  }

  /**
   * Emits an event indicating that the flow list entry should be updated with
   * results of a gvein query.
   */
  queryFlowResults(query: FlowResultsQueryWithoutFlowId) {
    this.flowResultsQuery.emit(query);
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();

    this.flowListEntry$.complete();
  }
}
