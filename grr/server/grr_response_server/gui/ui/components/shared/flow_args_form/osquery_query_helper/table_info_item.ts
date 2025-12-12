import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {
  Match,
  stringWithHighlightsFromMatch,
  StringWithHighlightsPart,
} from '../../../../lib/fuzzy_matcher';

import {type OsqueryTableSpec} from './osquery_table_specs';

/** An item containing table info to display in the query helper menu */
@Component({
  selector: 'table-info-item',
  templateUrl: './table_info_item.ng.html',
  styleUrls: ['./table_info_item.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
})
export class TableInfoItem {
  readonly tableSpec = input.required<OsqueryTableSpec>();
  readonly matchMap = input.required<Map<string, Match>>();

  get docsLinkToTable(): string {
    const tableName = this.tableSpec().name;
    return `https://osquery.io/schema/4.5.1/#${tableName}`;
  }

  convertToHighlightedParts(
    subject: string,
  ): readonly StringWithHighlightsPart[] {
    const matchResult = this.matchMap().get(subject);

    if (matchResult) {
      const stringWithHighlights = stringWithHighlightsFromMatch(matchResult);
      return stringWithHighlights.parts;
    } else {
      return [
        {
          value: subject,
          highlight: false,
        },
      ];
    }
  }

  trackByIndex(index: number, unusedElement: unknown): number {
    return index;
  }
}
