
import {Flow, FlowResultCount} from '../models/flow';

import {FlowDetailsAdapter, FlowResultSection} from './adapter';

/** Generic adapter, rendering flow results as tables. */
export class DefaultAdapter extends FlowDetailsAdapter<Flow> {
  override getResultView(resultGroup: FlowResultCount, args: unknown|undefined):
      FlowResultSection|undefined {
    return super.getResultView(resultGroup, args);
  }
}
