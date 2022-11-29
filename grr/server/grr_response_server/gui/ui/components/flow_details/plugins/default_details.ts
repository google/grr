import {ChangeDetectionStrategy, Component, OnChanges, OnInit, SimpleChanges} from '@angular/core';

import {FlowDetailsAdapter, FlowResultLinkSection, FlowResultSection, FlowResultViewSection} from '../../../lib/flow_adapters/adapter';
import {DEFAULT_ADAPTER, FLOW_ADAPTERS} from '../../../lib/flow_adapters/registry';
import {countFlowResults, Flow} from '../../../lib/models/flow';
import {FlowResultViewSectionWithFullQuery} from '../helpers/dynamic_result_section';

import {Plugin} from './plugin';

function toFullSectionData(section: FlowResultViewSection, flow: Flow):
    FlowResultViewSectionWithFullQuery {
  return {
    ...section,
    flow,
    totalResultCount: countFlowResults(flow.resultCounts ?? [], section.query),
  };
}

/** Default component that renders flow results based on FlowDetailsAdapter. */
@Component({
  selector: 'default-flow-details',
  templateUrl: './default_details.ng.html',
  styleUrls: ['./default_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DefaultDetails extends Plugin implements OnInit, OnChanges {
  showFallback = false;
  protected adapter?: FlowDetailsAdapter;
  protected sections?:
      ReadonlyArray<FlowResultViewSectionWithFullQuery|FlowResultLinkSection>;

  ngOnInit() {
    const adapter = FLOW_ADAPTERS[this.flow.name] ?? DEFAULT_ADAPTER;

    if (adapter === this.adapter) {
      return;
    }

    this.adapter = adapter;
    this.sections = adapter?.getResultViews(this.flow)?.map(
        s => this.isViewSection(s) ? toFullSectionData(s, this.flow) : s);
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.ngOnInit();
  }

  protected isViewSection(section: FlowResultSection):
      section is FlowResultViewSection {
    return (section as FlowResultViewSection).component !== undefined;
  }
}
