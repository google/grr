import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {Title} from '@angular/platform-browser';

import {GlobalStore} from '../../store/global_store';

// The not found page displays a random entry of these one-line ASCII arts.
const ASCII_ARTS: readonly string[] = [
  '(╯°□°)╯︵ ┻━┻',
  '(ノಠ益ಠ)ノ',
  '¯\\(◉‿◉)/¯',
];

/**
 * A page rendering error information about an address that could not be found.
 */
@Component({
  selector: 'not-found-page',
  templateUrl: './not_found_page.ng.html',
  styleUrls: ['./not_found_page.scss'],
  imports: [CommonModule, MatButtonModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotFoundPage {
  protected readonly globalStore = inject(GlobalStore);

  protected readonly asciiArt =
    ASCII_ARTS[Math.floor(Math.random() * ASCII_ARTS.length)];

  protected readonly currentUrlPath = window.location.href.slice(
    window.location.origin.length,
  );

  constructor() {
    inject(Title).setTitle('GRR | Not Found');
  }

  protected navigateBack() {
    window.history.back();
  }
}
