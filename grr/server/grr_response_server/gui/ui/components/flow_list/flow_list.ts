import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, ViewChild, ViewContainerRef} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {MatSnackBar} from '@angular/material/snack-bar';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, combineLatest, Observable} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {Flow, FlowDescriptorMap, FlowWithDescriptor} from '../../lib/models/flow';
import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {FlowResultsLocalStore} from '../../store/flow_results_local_store';
import {FlowArgsDialog, FlowArgsDialogData} from '../flow_args_dialog/flow_args_dialog';
import {FlowMenuAction} from '../flow_details/flow_details';
import {ErrorSnackbar} from '../helpers/error_snackbar/error_snackbar';

/** Adds the corresponding FlowDescriptor to a Flow, if existent. */
function withDescriptor(fds: FlowDescriptorMap):
    ((flow: Flow) => FlowWithDescriptor) {
  return flow => ({
           flow,
           descriptor: fds.get(flow.name),
         });
}

enum LoadMoreState {
  LOADING,
  HAS_MORE,
  ALL_LOADED,
}

/** Component that displays executed Flows on the currently selected Client. */
@Component({
  selector: 'flow-list',
  templateUrl: './flow_list.ng.html',
  styleUrls: ['./flow_list.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FlowResultsLocalStore],
})
export class FlowList implements AfterViewInit, OnDestroy {
  readonly LoadMoreState = LoadMoreState;

  readonly entries$: Observable<ReadonlyArray<FlowWithDescriptor>> =
      combineLatest([
        this.clientPageGlobalStore.flowListEntries$,
        this.configGlobalStore.flowDescriptors$,
      ])
          .pipe(
              map(([{flows}, fds]) => flows?.map(withDescriptor(fds)) ?? []),
          );

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
      filter(isNonNull),
  );

  scrollTarget: string|null = null;

  private scrollOperationId: ReturnType<typeof setTimeout>|undefined;

  @ViewChild('footer') footer!: ElementRef<HTMLElement>;

  private readonly triggerLoadMoreThroughScroll$ =
      new BehaviorSubject<boolean>(false);

  readonly ngOnDestroy = observeOnDestroy(this, () => {
    this.triggerLoadMoreThroughScroll$.complete();
  });

  constructor(
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly dialog: MatDialog,
      private readonly router: Router,
      private readonly activatedRoute: ActivatedRoute,
      viewRef: ViewContainerRef,
      snackBar: MatSnackBar,
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
            snackBar.openFromComponent(
                ErrorSnackbar, {data: `Did not find flow ${selectedFlowId}.`});
          }
        });

    combineLatest([this.triggerLoadMoreThroughScroll$, this.loadMoreState$])
        .pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(([footerVisible, loadMoreState]) => {
          if (footerVisible && loadMoreState === LoadMoreState.HAS_MORE) {
            // After loading new flows, there can be a short period where
            // loadMoreState = HAS_MORE but the footer is still in view,
            // because the new flow cards will only be rendered in the next
            // tick. To prevent always calling loadMore twice, set the trigger
            // flag to false. This requires the view to move out of view and
            // into again to re-trigger loading more.
            this.triggerLoadMoreThroughScroll$.next(false);
            this.loadMore();
          }
        });
  }

  ngAfterViewInit() {
    const observer = new IntersectionObserver((entries) => {
      if (entries.length > 0) {
        this.triggerLoadMoreThroughScroll$.next(entries[0].isIntersecting);
      }
    });

    if (this.footer.nativeElement) {
      observer.observe(this.footer.nativeElement);
    }
  }

  triggerFlowAction(entry: FlowWithDescriptor, event: FlowMenuAction) {
    if (event === FlowMenuAction.DUPLICATE) {
      this.clientPageGlobalStore.startFlowConfiguration(
          entry.flow.name, entry.flow.args);
      window.scrollTo({top: 0, behavior: 'smooth'});
    } else if (event === FlowMenuAction.CANCEL) {
      this.clientPageGlobalStore.cancelFlow(entry.flow.flowId);
    } else if (event === FlowMenuAction.VIEW_ARGS) {
      if (!entry.descriptor) {
        throw new Error('Cannot show flow args without flow descriptor.');
      }
      const data: FlowArgsDialogData = {
        flowArgs: entry.flow.args as {},
        flowDescriptor: entry.descriptor,
      };
      this.dialog.open(FlowArgsDialog, {data});
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
