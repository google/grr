import {ChangeDetectionStrategy, Component} from '@angular/core';
import {BehaviorSubject, Observable} from 'rxjs';
import {map, takeUntil} from 'rxjs/operators';

import {FlowFileResult, flowFileResultFromStatEntry, statusFromPathType} from '../../../components/flow_details/helpers/file_results_table';
import {CollectFilesByKnownPathArgs, CollectFilesByKnownPathProgress, CollectFilesByKnownPathResult, CollectFilesByKnownPathResultStatus} from '../../../lib/api/api_interfaces';
import {translateHashToHex, translateStatEntry} from '../../../lib/api_translation/flow';
import {Flow} from '../../../lib/models/flow';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {ExportMenuItem, Plugin} from './plugin';

interface FailedFileResult {
  readonly path?: string;
  readonly error?: string;
  readonly isNotFound?: boolean;
}

function failedResult(flowRes: CollectFilesByKnownPathResult):
    FailedFileResult {
  return {
    path: flowRes.stat?.pathspec?.path,
    error: flowRes.error,
    isNotFound:
        flowRes.status === CollectFilesByKnownPathResultStatus.NOT_FOUND,
  };
}

function isError(status: CollectFilesByKnownPathResultStatus|
                 undefined): boolean {
  if (!status) {
    return false;
  }

  return [
    CollectFilesByKnownPathResultStatus.FAILED,
    CollectFilesByKnownPathResultStatus.NOT_FOUND
  ].includes(status!);
}

/**
 * Component that displays results of CollectFilesByKnownPath flow.
 */
@Component({
  selector: 'collect-files-by-known-path-details',
  templateUrl: './collect_files_by_known_path_details.ng.html',
  styleUrls: ['./collect_files_by_known_path_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectFilesByKnownPathDetails extends Plugin {
  readonly QUERY_MORE_COUNT = 100;

  readonly args$: Observable<CollectFilesByKnownPathArgs> = this.flow$.pipe(
      map(flow => flow.args as CollectFilesByKnownPathArgs),
  );

  readonly flowProgress$: Observable<CollectFilesByKnownPathProgress> =
      this.flow$.pipe(
          map((flow) => flow.progress as CollectFilesByKnownPathProgress),
      );

  readonly retriesTotal$: Observable<number> = this.flowProgress$.pipe(
      map((progress) => Number(progress?.numRawFsAccessRetries ?? 0)));
  readonly retriesLabel$: Observable<string> =
      this.retriesTotal$.pipe(map((count) => {
        const p = count === 1 ? '' : 's';
        return `${count} file${
            p} fetched by parsing the raw disk image with libtsk or libfsntfs.`;
      }));

  readonly successTotal$: Observable<number> = this.flowProgress$.pipe(
      map((progress) => Number(progress?.numCollected ?? 0)));
  readonly successLabel$: Observable<string> =
      this.successTotal$.pipe(map((count) => {
        const p = count === 1 ? '' : 's';
        return `${count} successful file collection${p}`;
      }));

  readonly errorTotal$: Observable<number> = this.flowProgress$.pipe(
      map((progress) => Number(progress?.numFailed ?? 0)));
  readonly errorLabel$: Observable<string> =
      this.errorTotal$.pipe(map((count) => {
        const p = count === 1 ? '' : 's';
        return `${count} error${p}`;
      }));

  readonly anyResults$: Observable<boolean> = this.flowProgress$.pipe(
      map((progress) => Number(progress?.numCollected ?? 0) +
                  Number(progress?.numFailed ?? 0) >
              0));

  readonly description$ = this.args$.pipe(map(args => {
    const length = args.paths?.length ?? 0;
    if (length <= 1) {
      return args.paths?.[0] ?? '';
    } else {
      return `${args.paths?.[0]} + ${length - 1} more`;
    }
  }));

  readonly successFiles$ =
      new BehaviorSubject<ReadonlyArray<FlowFileResult>>([]);
  readonly errorFiles$ =
      new BehaviorSubject<ReadonlyArray<FailedFileResult>>([]);

  readonly errorFilesColumns: ReadonlyArray<string> =
      ['path', 'error', 'status'];

  readonly fileResults$:
      Observable<ReadonlyArray<CollectFilesByKnownPathResult>> =
          this.flowResultsLocalStore.results$.pipe(
              map(results => results?.map(
                      (data) => data.payload as CollectFilesByKnownPathResult)),
          );

  constructor(
      private readonly flowResultsLocalStore: FlowResultsLocalStore,
  ) {
    super();
    this.flowResultsLocalStore.query(this.flow$.pipe(
        map(flow => ({flow, withType: 'CollectFilesByKnownPathResult'}))));

    // Update table data sources every time there's new flow results.
    this.fileResults$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(results => {
          this.successFiles$.next(
              results
                  .filter(
                      res => res.status ===
                          CollectFilesByKnownPathResultStatus.COLLECTED)
                  .map(
                      res => flowFileResultFromStatEntry(
                          translateStatEntry(res.stat!),
                          translateHashToHex(res.hash ?? {}),
                          statusFromPathType(res?.stat?.pathspec?.pathtype))));

          this.errorFiles$.next(results.filter(res => isError(res.status))
                                    .map(res => failedResult(res)));
        });
  }

  queryMore() {
    this.flowResultsLocalStore.queryMore(this.QUERY_MORE_COUNT);
  }

  trackByRowIndex(index: number, item: FailedFileResult) {
    return index;
  }

  override getResultDescription(flow: Flow): string|undefined {
    const progress =
        flow.progress as CollectFilesByKnownPathProgress | undefined;

    if (progress) {
      const count = Number(progress?.numCollected ?? 0);
      return count === 1 ? '1 result' : `${count} results`;
    }

    return super.getResultDescription(flow);
  }

  override getExportMenuItems(flow: Flow): ReadonlyArray<ExportMenuItem> {
    const downloadItem = this.getDownloadFilesExportMenuItem(flow);
    const items = super.getExportMenuItems(flow);

    if (items.find(item => item.url === downloadItem.url)) {
      return items;
    }

    // If the menu does not yet contain "Download files", display it.
    return [downloadItem, ...items];
  }
}
