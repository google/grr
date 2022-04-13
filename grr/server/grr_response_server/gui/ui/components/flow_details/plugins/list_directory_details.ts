import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {FlowFileResult, flowFileResultFromStatEntry} from '../../../components/flow_details/helpers/file_results_table';
import {ListDirectoryArgs, RecursiveListDirectoryArgs, StatEntry as ApiStatEntry} from '../../../lib/api/api_interfaces';
import {translateStatEntry} from '../../../lib/api_translation/flow';
import {FlowResultMapFunction, FlowResultsQueryWithAdapter} from '../helpers/load_flow_results_directive';

import {Plugin} from './plugin';

const ADAPTER: FlowResultMapFunction<ReadonlyArray<FlowFileResult>|undefined> =
    (results) => results?.map(item => item.payload as ApiStatEntry)
                     .map(translateStatEntry)
                     .map(res => flowFileResultFromStatEntry(res, {}));

/**
 * Component that displays ListDirectory and RecursiveListDirectory flow
 * results.
 */
@Component({
  selector: 'list_directory-flow-details',
  templateUrl: './list_directory_details.ng.html',
  styleUrls: ['./list_directory_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListDirectoryDetails extends Plugin {
  readonly QUERY_MORE_COUNT = 100;

  readonly totalFiles$ = this.flow$.pipe(
      map(flow => flow.resultCounts
                      ?.find(resultCount => resultCount.type === 'StatEntry')
                      ?.count));

  readonly args$: Observable<ListDirectoryArgs|RecursiveListDirectoryArgs> =
      this.flow$.pipe(
          map((flow) =>
                  flow.args as ListDirectoryArgs | RecursiveListDirectoryArgs),
      );

  readonly description$ = this.args$.pipe(
      map(args => args?.pathspec?.path ?? 'No paths specified'));

  readonly query$: Observable<
      FlowResultsQueryWithAdapter<ReadonlyArray<FlowFileResult>|undefined>> =
      this.flow$.pipe(map(flow => ({flow, resultMapper: ADAPTER})));
}
