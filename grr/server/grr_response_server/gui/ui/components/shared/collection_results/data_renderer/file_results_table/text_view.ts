import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {FileContent} from '../../../../../lib/models/vfs';
import {Codeblock} from '../codeblock';

function toRows(content: FileContent | undefined): string[] {
  if (content === undefined) {
    return [];
  }
  return content.textContent?.split('\n') ?? [];
}

/** Component to show plain-text file contents. */
@Component({
  selector: 'text-view',
  templateUrl: './text_view.ng.html',
  imports: [CommonModule, Codeblock],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TextView {
  readonly textContent = input.required<string[], FileContent | undefined>({
    transform: toRows,
  });
}
