import {ChangeDetectionStrategy, Component, TrackByFunction} from '@angular/core';
import {map} from 'rxjs/operators';

import {FlowFileResult, flowFileResultFromStatEntry} from '../../../components/flow_details/helpers/file_results_table';
import {ExecuteResponse, StatEntry} from '../../../lib/api/api_interfaces';
import {isRegistryEntry, isStatEntry, translateArtifactCollectorFlowProgress, translateExecuteResponse, translateVfsStatEntry} from '../../../lib/api_translation/flow';
import {ArtifactProgress, Flow, FlowResult, RegistryKey, RegistryValue} from '../../../lib/models/flow';
import {isNull} from '../../../lib/preconditions';
import {Writable} from '../../../lib/type_utils';
import {FlowResultMapFunction, FlowResultsQueryWithAdapter} from '../helpers/load_flow_results_directive';

import {Plugin} from './plugin';

function getResults(results: ReadonlyArray<FlowResult>, typeName: 'StatEntry'):
    ReadonlyArray<StatEntry>;
function getResults(
    results: ReadonlyArray<FlowResult>,
    typeName: 'ExecuteResponse'): ReadonlyArray<ExecuteResponse>;
function getResults(
    results: ReadonlyArray<FlowResult>, typeName: string): ReadonlyArray<{}> {
  return results.filter(item => item.payloadType === typeName)
      .map(item => item.payload as {});
}

declare interface ArtifactRow {
  readonly name: string;
  readonly numResults?: number;
  readonly description: string;
  readonly resultQuery: FlowResultsQueryWithAdapter<ArtifactResults>;
}

function toRow(flow: Flow, artifact: ArtifactProgress): ArtifactRow {
  let description: string;
  if (isNull(artifact.numResults)) {
    description = '';
  } else if (artifact.numResults === 1) {
    description = '1 result';
  } else {
    description = `${artifact.numResults} results`;
  }

  return {
    name: artifact.name,
    numResults: artifact.numResults,
    description,
    resultQuery: {
      flow,
      withTag: `artifact:${artifact.name}`,
      resultMapper: mapFlowResults,
    },
  };
}

interface ArtifactResults {
  readonly fileResults: ReadonlyArray<FlowFileResult>;
  readonly registryResults: ReadonlyArray<RegistryKey|RegistryValue>;
  readonly executeResponseResults: ReadonlyArray<ExecuteResponse>;
  readonly unknownResultCount: number;
}

const mapFlowResults: FlowResultMapFunction<ArtifactResults> = (rawResults) => {
  const statEntryResults =
      getResults(rawResults ?? [], 'StatEntry').map(translateVfsStatEntry);

  const results: Writable<ArtifactResults> = {
    fileResults: statEntryResults.filter(isStatEntry)
                     .map(stat => flowFileResultFromStatEntry(stat)),
    registryResults: statEntryResults.filter(isRegistryEntry),
    executeResponseResults: getResults(rawResults ?? [], 'ExecuteResponse')
                                .map(translateExecuteResponse),
    unknownResultCount: rawResults?.length ?? 0,
  };

  results.unknownResultCount -= results.fileResults.length +
      results.registryResults.length + results.executeResponseResults.length;

  return results;
};

/** Component that displays flow results. */
@Component({
  selector: 'app-artifact-collector-flow-details',
  templateUrl: './artifact_collector_flow_details.ng.html',
  styleUrls: ['./artifact_collector_flow_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactCollectorFlowDetails extends Plugin {
  readonly INITIAL_COUNT = 100;

  readonly artifactRows$ = this.flow$.pipe(
      map((flow) => Array
                        .from(translateArtifactCollectorFlowProgress(flow)
                                  .artifacts.values())
                        .map(a => toRow(flow, a))));

  readonly trackArtifactByName: TrackByFunction<ArtifactRow> =
      (index, artifact) => artifact.name;
}
