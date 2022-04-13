import {ChangeDetectionStrategy, Component} from '@angular/core';
import {combineLatest, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {FlowFileResult, statusFromPathSpecProgressStatus} from '../../../components/flow_details/helpers/file_results_table';
import {MultiGetFileArgs, MultiGetFileProgress} from '../../../lib/api/api_interfaces';
import {StatEntry} from '../../../lib/models/vfs';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {Plugin} from './plugin';

/**
 * Component that allows selecting, configuring, and starting a Flow.
 */
@Component({
  selector: 'multi-get-file-flow-details',
  templateUrl: './multi_get_file_details.ng.html',
  styleUrls: ['./multi_get_file_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MultiGetFileDetails extends Plugin {
  constructor(readonly flowResultsLocalStore: FlowResultsLocalStore) {
    super();
    this.flowResultsLocalStore.query(
        this.flow$.pipe(map(flow => ({flow, withType: 'StatEntry'}))));
  }

  readonly QUERY_MORE_COUNT = 100;

  readonly flowProgress$: Observable<MultiGetFileProgress> = this.flow$.pipe(
      map((flow) => flow.progress as MultiGetFileProgress),
  );

  readonly flowResults$: Observable<StatEntry[]> =
      this.flowResultsLocalStore.results$.pipe(map(
          results => results?.map((data) => data.payload as StatEntry),
          ));

  readonly results$: Observable<FlowFileResult[]> =
      combineLatest([
        this.flowResults$,
        this.flowProgress$.pipe(
            map(progress => progress?.pathspecsProgress),
            map(pathspecProgress => new Map(
                    pathspecProgress?.map(p => ([p?.pathspec?.path, p])))))
      ]).pipe(map(([results, fileProgress]): FlowFileResult[] => {
        // TODO: Revise whether we want to display `FAILED` results
        // in the table or not.
        return results?.map((result): FlowFileResult => {
          const fileStatus = fileProgress.get(result?.pathspec?.path);
          return {
            statEntry: result,
            status: statusFromPathSpecProgressStatus(fileStatus?.status)
          };
        });
      }));


  readonly totalFiles$: Observable<number> = this.flowProgress$.pipe(
      map((progress) => Number(
              (progress?.numSkipped ?? 0) + (progress?.numCollected ?? 0) +
              (progress?.numFailed ?? 0))));

  readonly args$: Observable<MultiGetFileArgs> = this.flow$.pipe(
      map((flow) => flow.args as MultiGetFileArgs),
  );

  readonly description$ = this.args$.pipe(map(args => {
    if (args?.pathspecs === undefined) {
      return 'No paths specified';
    }
    const length = args?.pathspecs?.length ?? 0;
    if (length <= 1) {
      return args?.pathspecs[0].path ?? '';
    } else {
      return `${args?.pathspecs[0].path} + ${length - 1} more`;
    }
  }));
}
