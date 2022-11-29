import {ChangeDetectionStrategy, Component, OnDestroy, ViewContainerRef} from '@angular/core';
import {FormControl} from '@angular/forms';
import {ActivatedRoute, Router} from '@angular/router';
import {combineLatest, Observable} from 'rxjs';
import {map, startWith, takeUntil} from 'rxjs/operators';

import {FlowWithDescriptor, withDescriptor} from '../../lib/models/flow';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {FlowResultsLocalStore} from '../../store/flow_results_local_store';
import {FlowMenuAction} from '../flow_details/flow_details';
import {SnackBarErrorHandler} from '../helpers/error_snackbar/error_handler';

enum LoadMoreState {
  LOADING,
  HAS_MORE,
  ALL_LOADED,
}

/** Flow filter enum used for classifying the flows. */
export enum FlowFilter {
  ALL_HUMAN_FLOWS = 'All human flows',
  ALL_ROBOT_FLOWS = 'All robot flows',
  ALL_FLOWS = 'All flows',
}

/** Component that displays executed Flows on the currently selected Client. */
@Component({
  selector: 'flow-list',
  templateUrl: './flow_list.ng.html',
  styleUrls: ['./flow_list.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FlowResultsLocalStore],
})
export class FlowList implements OnDestroy {
  readonly LoadMoreState = LoadMoreState;
  readonly FlowFilter = FlowFilter;

  readonly flowFiltersForm = new FormControl(FlowFilter.ALL_HUMAN_FLOWS);

  readonly entries$: Observable<ReadonlyArray<FlowWithDescriptor>> =
      combineLatest([
        this.clientPageGlobalStore.flowListEntries$,
        this.configGlobalStore.flowDescriptors$,
      ])
          .pipe(
              map(([{flows}, fds]) => flows?.map(withDescriptor(fds)) ?? []),
          );

  readonly filteredEntries$: Observable<readonly FlowWithDescriptor[]> =
      combineLatest([
        this.entries$,
        this.flowFiltersForm.valueChanges.pipe(
            startWith(FlowFilter.ALL_HUMAN_FLOWS)),
      ]).pipe(map(([entries, filterType]) => entries.filter((entry) => {
        switch (filterType) {
          case FlowFilter.ALL_HUMAN_FLOWS:
            return entry.flow.isRobot === false;
          case FlowFilter.ALL_ROBOT_FLOWS:
            return entry.flow.isRobot === true;
          default:
            return true;
        }
      })));

  readonly loadMoreState$ = this.clientPageGlobalStore.flowListEntries$.pipe(
      map(({isLoading, hasMore}) => {
        if (isLoading || hasMore === undefined) {
          return LoadMoreState.LOADING;
        } else if (hasMore) {
          return LoadMoreState.HAS_MORE;
        } else {
          return LoadMoreState.ALL_LOADED;
        }
      }));

  readonly selectedFlowId$ = this.activatedRoute.params.pipe(
      map(params => params['flowId'] as string | null),
  );

  scrollTarget: string|null = null;

  private scrollOperationId: ReturnType<typeof setTimeout>|undefined;

  readonly ngOnDestroy = observeOnDestroy(this);

  readonly client$ = this.clientPageGlobalStore.selectedClient$;

  constructor(
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly router: Router,
      private readonly activatedRoute: ActivatedRoute,
      private readonly errorHandler: SnackBarErrorHandler,
      viewRef: ViewContainerRef,
  ) {
    const scrollIntoView = (selectedFlowId: string, timeout: number = 0) => {
      if (this.scrollOperationId) {
        // If there is already an existing scrollIntoView operation, cancel it.
        clearTimeout(this.scrollOperationId);
        this.scrollOperationId = undefined;
      }

      const flowElement = (viewRef.element.nativeElement as HTMLElement)
                              .querySelector(`#flow-${selectedFlowId}`);

      // Mark the selected flow as scroll target, which prevents additional
      // calls to this function for the same flow.
      this.scrollTarget = selectedFlowId;

      if (flowElement) {
        // If the flow element has been rendered already, scroll it into view.
        flowElement.scrollIntoView();
      } else {
        // Flow has been loaded, but the view has not yet been created. Angular
        // triggers this observer before it renders the view. During testing,
        // the view has always been created in the next tick, but we follow a
        // linear back-off for robustness.
        this.scrollOperationId = setTimeout(() => {
          scrollIntoView(selectedFlowId, timeout + 1);
        }, timeout);
      }
    };

    // Load and scroll the flow requested in the URL /flows/<id> into view.
    combineLatest(
        [this.clientPageGlobalStore.flowListEntries$, this.selectedFlowId$])
        .pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(([{flows, isLoading, hasMore}, selectedFlowId]) => {
          if (flows === undefined || !selectedFlowId || isLoading ||
              selectedFlowId === this.scrollTarget) {
            this.scrollTarget = selectedFlowId;
            return;
          }

          const index = flows.findIndex(e => e.flowId === selectedFlowId);

          if (index !== -1) {
            // The flow has been found in the results, but might not yet be
            // rendered as view. Schedule to scroll it into view.
            scrollIntoView(selectedFlowId);
          } else if (hasMore) {
            // The flow has not been found, but there might be more flows. Load
            // the next batch, upon which flowListEntries$ will
            // re-emit.
            this.clientPageGlobalStore.loadMoreFlows();
          } else {
            // All flows have been loaded and the requested flow still has not
            // been found. Mark it as active scroll target to prevent repeated
            // SnackBars when flow list is re-polled.
            this.scrollTarget = selectedFlowId;

            this.errorHandler.handleError(
                `Did not find flow ${selectedFlowId}.`);
          }
        });
  }

  triggerFlowAction(entry: FlowWithDescriptor, event: FlowMenuAction) {
    if (event === FlowMenuAction.DUPLICATE) {
      this.clientPageGlobalStore.startFlowConfiguration(
          entry.flow.name, entry.flow.args);
      window.scrollTo({top: 0, behavior: 'smooth'});
    } else if (event === FlowMenuAction.CANCEL) {
      this.clientPageGlobalStore.cancelFlow(entry.flow.flowId);
    } else if (event === FlowMenuAction.CREATE_HUNT) {
      this.router.navigate(['/new-hunt'], {
        queryParams:
            {'clientId': entry.flow.clientId, 'flowId': entry.flow.flowId},
      });
    }
  }

  entryTrackByFunction(index: number, entry: FlowWithDescriptor) {
    return entry.flow.flowId;
  }

  loadMore() {
    this.clientPageGlobalStore.loadMoreFlows();
  }
}
