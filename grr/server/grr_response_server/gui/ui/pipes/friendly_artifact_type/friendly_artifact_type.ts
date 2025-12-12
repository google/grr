import {Pipe, PipeTransform} from '@angular/core';

import {SourceType} from '../../lib/models/flow';
import {checkExhaustive} from '../../lib/utils';

/**
 * Pipe that returns a friendly name for a flow.
 */
@Pipe({name: 'FriendlyArtifactType', standalone: true, pure: true})
export class FriendlyArtifactTypePipe implements PipeTransform {
  transform(artifactType: SourceType): string {
    switch (artifactType) {
      case SourceType.COMMAND:
        return 'Executes command';
      case SourceType.FILE:
        return 'Collects file';
      case SourceType.PATH:
        return 'Collects path';
      case SourceType.REGISTRY_KEY:
        return 'Collects Windows Registry key';
      case SourceType.REGISTRY_VALUE:
        return 'Collects Windows Registry value';
      case SourceType.WMI:
        return 'Queries WMI';
      case SourceType.COLLECTOR_TYPE_UNKNOWN:
        return 'Unknown artifact';
      default:
        return checkExhaustive(
          artifactType,
          'Invalid source type ' + String(artifactType),
        );
    }
  }
}
