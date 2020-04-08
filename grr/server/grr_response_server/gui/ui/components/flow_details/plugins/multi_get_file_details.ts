import {ChangeDetectionStrategy, Component} from '@angular/core';
import {MultiGetFileArgs, MultiGetFileProgress, PathSpec} from '@app/lib/api/api_interfaces';
import {Complete} from '@app/lib/type_utils';
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
  pathSpecToPath(ps: PathSpec): string {
    return ps.path || '';
  }

  get args() {
    return this.flowListEntry.flow.args as MultiGetFileArgs;
  }

  get hasProgress() {
    return this.flowListEntry.flow.progress !== undefined;
  }

  get progress(): Complete<MultiGetFileProgress> {
    const p = this.flowListEntry.flow.progress as MultiGetFileProgress;

    return {
      numPendingHashes: p.numPendingHashes || 0,
      numPendingFiles: p.numPendingFiles || 0,
      numSkipped: p.numSkipped || 0,
      numCollected: p.numCollected || 0,
      numFailed: p.numFailed || 0,
      pathspecsProgress: p.pathspecsProgress || [],
    };
  }
}
