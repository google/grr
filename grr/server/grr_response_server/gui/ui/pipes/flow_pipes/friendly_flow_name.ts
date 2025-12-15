import {Pipe, PipeTransform} from '@angular/core';

import {FLOW_DETAILS_BY_TYPE} from '../../lib/data/flows/flow_definitions';
import {FlowType} from '../../lib/models/flow';

/** Unknown flow title, used as fallback in case there is no name. */
export const UNKNOWN_FLOW_TITLE = 'Unknown flow';

/**
 * Pipe that returns a friendly name for a flow.
 */
@Pipe({name: 'friendlyFlowName', standalone: true, pure: true})
export class FriendlyFlowNamePipe implements PipeTransform {
  transform(flowType: FlowType | undefined): string {
    if (flowType === undefined) {
      return UNKNOWN_FLOW_TITLE;
    }
    const flowItem = FLOW_DETAILS_BY_TYPE.get(flowType);
    return flowItem?.friendlyName || UNKNOWN_FLOW_TITLE;
  }
}
