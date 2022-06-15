import {ChangeDetectionStrategy, Component, TrackByFunction} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {Process, YaraProcessDumpArgs, YaraProcessDumpInformation, YaraProcessDumpResponse} from '../../../lib/api/api_interfaces';
import {countFlowResults, Flow, FlowState} from '../../../lib/models/flow';
import {FlowResultMapFunction, FlowResultsQueryWithAdapter} from '../helpers/load_flow_results_directive';

import {Plugin} from './plugin';

/** Component that displays flow results. */
@Component({
  selector: 'app-dump-process-memory-details',
  templateUrl: './dump_process_memory_details.ng.html',
  styleUrls: ['./dump_process_memory_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DumpProcessMemoryDetails extends Plugin {
  private readonly flowArgs$ =
      this.flow$.pipe(map(flow => flow.args as YaraProcessDumpArgs));

  readonly title$ = this.flowArgs$.pipe(map(args => {
    const parts: string[] = [];

    if (args.dumpAllProcesses) {
      parts.push('Dump all processes');
    }

    if (args.pids?.length) {
      parts.push(`PID ${args.pids.join(', ')}`);
    }

    if (args.processRegex) {
      parts.push(`Process name matches ${args.processRegex}`);
    }

    return parts.join(', ');
  }));

  readonly query$: Observable<FlowResultsQueryWithAdapter<ReadonlyArray<Row>>> =
      this.flow$.pipe(map(flow => ({
                            flow,
                            withType: 'YaraProcessDumpResponse',
                            resultMapper,
                          })));

  override getResultDescription(flow: Flow): string|undefined {
    const regionCount =
        countFlowResults(flow.resultCounts ?? [], {type: 'StatEntry'});
    if (!regionCount && flow.state === FlowState.RUNNING) {
      return '';  // Hide "0 results" if flow is still running.
    } else {
      // As soon as we have ≥1 results, show the result count. Only show
      // "0 results" if the flow is finished.
      return pluralize(regionCount ?? 0, 'region', 'regions');
    }
  }

  readonly trackByRowIndex: TrackByFunction<Row> = (index, row) => index;

  readonly displayedColumns = ['pid', 'cmdline', 'memoryRegionsCount', 'error'];
}

function pluralize(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

declare interface Row {
  process?: Process;
  error?: string;
  memoryRegionsCount: string;
}

const resultMapper: FlowResultMapFunction<ReadonlyArray<Row>> = (results) => {
  return results?.map(res => res.payload as YaraProcessDumpResponse)
             .flatMap(
                 res => [...res.dumpedProcesses ?? [], ...res.errors ?? []])
             .map(res => ({
                    process: res.process,
                    memoryRegionsCount: pluralize(
                        (res as YaraProcessDumpInformation)
                                .memoryRegions?.length ??
                            0,
                        'region', 'regions'),
                    error: res.error,
                  })) ??
      [];
};
