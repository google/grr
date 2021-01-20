import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FlowFileResult, flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {CollectSingleFileArgs, CollectSingleFileProgress, CollectSingleFileProgressStatus, PathSpecPathType} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {EMPTY, Observable, of} from 'rxjs';
import {filter, map, mergeMap} from 'rxjs/operators';
import {translateHashToHex} from '../../../lib/api_translation/flow';
import {isNonNull} from '../../../lib/preconditions';
import {Plugin} from './plugin';



/**
 * Component that allows selecting, configuring, and starting a Flow.
 */
@Component({
  selector: 'collect-single-file-details',
  templateUrl: './collect_single_file_details.ng.html',
  styleUrls: ['./collect_single_file_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectSingleFileDetails extends Plugin {
  constructor(private readonly httpApiService: HttpApiService) {
    super();
  }

  pathSpecPathType = PathSpecPathType;

  progress$: Observable<CollectSingleFileProgress|undefined> =
      this.flowListEntry$.pipe(
          map((flowListEntry) =>
                  flowListEntry.flow.progress as CollectSingleFileProgress |
                  undefined),
      );

  errorDescription$: Observable<string> =
      this.progress$.pipe(mergeMap((progress) => {
        if (!progress) {
          return EMPTY;
        }

        if (progress.status === CollectSingleFileProgressStatus.NOT_FOUND) {
          return of('File not found');
        } else if (progress.status === CollectSingleFileProgressStatus.FAILED) {
          return of(progress.errorDescription!);
        } else {
          return EMPTY;
        }
      }));

  fileResults$: Observable<ReadonlyArray<FlowFileResult>> = this.progress$.pipe(
      map((progress) => progress?.result),
      filter(isNonNull),
      map((result) => [flowFileResultFromStatEntry(
              result.stat!, translateHashToHex(result.hash ?? {}))]),
  );

  filePathType$: Observable<PathSpecPathType> = this.progress$.pipe(
      map((progress) => progress?.result?.stat?.pathspec?.pathtype),
      filter(isNonNull),
  );

  args$: Observable<CollectSingleFileArgs> = this.flowListEntry$.pipe(
      map((flowListEntry) => flowListEntry.flow.args as CollectSingleFileArgs),
  );

  archiveUrl$: Observable<string> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        return this.httpApiService.getFlowFilesArchiveUrl(
            flowListEntry.flow.clientId, flowListEntry.flow.flowId);
      }));

  archiveFileName$: Observable<string> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        return flowListEntry.flow.clientId.replace('.', '_') + '_' +
            flowListEntry.flow.flowId + '.zip';
      }));
}
