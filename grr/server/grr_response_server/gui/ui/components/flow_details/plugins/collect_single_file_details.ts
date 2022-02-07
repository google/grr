import {ChangeDetectionStrategy, Component} from '@angular/core';
import {EMPTY, Observable, of} from 'rxjs';
import {filter, map, mergeMap} from 'rxjs/operators';

import {FlowFileResult, flowFileResultFromStatEntry} from '../../../components/flow_details/helpers/file_results_table';
import {CollectSingleFileArgs, CollectSingleFileProgress, CollectSingleFileProgressStatus, PathSpecPathType} from '../../../lib/api/api_interfaces';
import {translateHashToHex, translateStatEntry} from '../../../lib/api_translation/flow';
import {Flow} from '../../../lib/models/flow';
import {isNonNull} from '../../../lib/preconditions';

import {ExportMenuItem, Plugin} from './plugin';



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
  pathSpecPathType = PathSpecPathType;

  progress$: Observable<CollectSingleFileProgress|undefined> = this.flow$.pipe(
      map((flow) => flow.progress as CollectSingleFileProgress | undefined),
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
              translateStatEntry(result.stat!),
              translateHashToHex(result.hash ?? {}))]),
  );

  filePathType$: Observable<PathSpecPathType> = this.progress$.pipe(
      map((progress) => progress?.result?.stat?.pathspec?.pathtype),
      filter(isNonNull),
  );

  args$: Observable<CollectSingleFileArgs> = this.flow$.pipe(
      map((flow) => flow.args as CollectSingleFileArgs),
  );

  override getResultDescription(flow: Flow): string|undefined {
    const progress = flow.progress as CollectSingleFileProgress | undefined;

    if (progress?.status === CollectSingleFileProgressStatus.NOT_FOUND) {
      return 'File not found';
    } else if (progress?.status === CollectSingleFileProgressStatus.FAILED) {
      return progress.errorDescription!;
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
