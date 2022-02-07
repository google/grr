import {Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {ReadLowLevelArgs} from '../../../lib/api/api_interfaces';
import {getTempBlobUrl} from '../../../lib/api/http_api_service';
import {Flow, FlowState} from '../../../lib/models/flow';

import {ExportMenuItem, Plugin} from './plugin';


/**
 * Component that displays results of ReadLowLevel flow.
 */
@Component({
  selector: 'read-low-level-details',
  templateUrl: './read_low_level_details.ng.html',
  styleUrls: ['./read_low_level_details.scss'],
})
export class ReadLowLevelDetails extends Plugin {
  readonly flowState$: Observable<FlowState> = this.flow$.pipe(
      map((flow: Flow) => flow.state),
  );

  readonly clientId$: Observable<string> = this.flow$.pipe(
      map((flow: Flow) => flow.clientId),
  );

  readonly args$: Observable<ReadLowLevelArgs> = this.flow$.pipe(
      map((flow: Flow) => flow.args as ReadLowLevelArgs),
  );
  // TODO: render readable bytes.
  readonly title$ = this.args$.pipe(map((args: ReadLowLevelArgs) => {
    let title = `${args.length} bytes `;
    if (args.offset) {
      title += `starting at ${args.offset} `;
    }
    title += `from ${args.path}`;
    return title;
  }));

  override getExportMenuItems(flow: Flow): readonly ExportMenuItem[] {
    // Strips punctuation.
    const args = this.flow.args as ReadLowLevelArgs | undefined;
    const alphanumericOnly = args?.path?.replace(/[^\p{L}\s]/gu, '') ?? '';
    const archiveFileName =
        `${this.flow.clientId}_${this.flow.flowId}_${alphanumericOnly}`;
    return [
      {
        title: 'Download data',
        url: getTempBlobUrl(this.flow.clientId, archiveFileName),
      },
      ...super.getExportMenuItems(flow),
    ];
  }
}
