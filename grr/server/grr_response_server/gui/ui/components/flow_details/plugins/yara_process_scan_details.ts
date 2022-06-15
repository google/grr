import {ChangeDetectionStrategy, Component, TrackByFunction} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {Process, YaraMatch, YaraProcessScanMatch, YaraProcessScanRequest, YaraStringMatch} from '../../../lib/api/api_interfaces';
import {decodeBase64ToString} from '../../../lib/api_translation/primitive';
import {countFlowResults, Flow, FlowState} from '../../../lib/models/flow';
import {FlowResultMapFunction, FlowResultsQueryWithAdapter} from '../helpers/load_flow_results_directive';

import {Plugin} from './plugin';

/** Component that displays flow results. */
@Component({
  selector: 'app-yara-process-scan-details',
  templateUrl: './yara_process_scan_details.ng.html',
  styleUrls: ['./yara_process_scan_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class YaraProcessScanDetails extends Plugin {
  private readonly flowArgs$ =
      this.flow$.pipe(map(flow => flow.args as YaraProcessScanRequest));

  readonly title$ = this.flowArgs$.pipe(map(
      args => `Processes matching ${args.yaraSignature ?? '(no YARA rule)'}`));

  readonly query$: Observable<FlowResultsQueryWithAdapter<ReadonlyArray<Row>>> =
      this.flow$.pipe(map(flow => ({
                            flow,
                            withType: 'YaraProcessScanMatch',
                            resultMapper,
                          })));

  override getResultDescription(flow: Flow): string|undefined {
    const regionCount = countFlowResults(
        flow.resultCounts ?? [], {type: 'YaraProcessScanMatch'});
    if (!regionCount && flow.state === FlowState.RUNNING) {
      return '';  // Hide "0 results" if flow is still running.
    } else {
      // As soon as we have ≥1 results, show the result count. Only show
      // "0 results" if the flow is finished.
      return pluralize(regionCount ?? 0, 'process', 'processes');
    }
  }

  readonly trackByRowIndex: TrackByFunction<Row> = (index, row) => index;

  readonly displayedColumns =
      ['pid', 'process', 'ruleId', 'matchOffset', 'matchId', 'matchData'];
}

function pluralize(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

declare interface Row {
  process?: Process;
  match?: YaraMatch;
  stringMatch?: YaraStringMatch;
  data: string;
}

const resultMapper: FlowResultMapFunction<ReadonlyArray<Row>> = (results) =>
    (results ?? [])
        .map(res => res.payload as YaraProcessScanMatch)
        .flatMap(
            response => (response.match ?? [])
                            .flatMap(
                                yaraMatch => (yaraMatch.stringMatches ?? [])
                                                 .map(
                                                     stringMatch => toRow(
                                                         response,
                                                         yaraMatch,
                                                         stringMatch,
                                                         ))));

function toRow(
    response: YaraProcessScanMatch,
    yaraMatch: YaraMatch,
    stringMatch: YaraStringMatch,
) {
  return {
    process: response.process,
    match: yaraMatch,
    stringMatch,
    data: decodeBase64ToString(stringMatch.data ?? ''),
  };
}
