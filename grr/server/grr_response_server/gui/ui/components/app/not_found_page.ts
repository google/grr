import {Component} from '@angular/core';
import {Title} from '@angular/platform-browser';

import {makeLegacyLink} from '../../lib/routing';
import {ConfigGlobalStore} from '../../store/config_global_store';

// The not found page displays a random entry of these one-line ASCII arts.
const ASCII_ARTS: ReadonlyArray<string> = [
  '(╯°□°)╯︵ ┻━┻',
  '(ノಠ益ಠ)ノ',
  '¯\\(◉‿◉)/¯',
];

/**
 * A page rendering error information about an address that could not be found.
 */
@Component({
  selector: 'app-not-found-page',
  templateUrl: './not_found_page.ng.html',
  styleUrls: ['./not_found_page.scss']
})
export class NotFoundPage {
  readonly uiConfig$ = this.configGlobalStore.uiConfig$;

  readonly asciiArt = ASCII_ARTS[Math.floor(Math.random() * ASCII_ARTS.length)];

  readonly legacyLink = makeLegacyLink();

  readonly currentUrlPath =
      window.location.href.slice(window.location.origin.length);

  constructor(
      private readonly configGlobalStore: ConfigGlobalStore, title: Title) {
    title.setTitle('GRR | Not Found');
  }

  navigateBack() {
    window.history.back();
  }
}
