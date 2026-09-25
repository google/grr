import {Component, inject} from '@angular/core';
import {Router} from '@angular/router';

/**
 * Component that redirects from /v2 to /.
 *
 * Temporary component that should be removed once no links point to /v2
 * anymore.
 * TODO - Remove this component once no links point to /v2 anymore.
 */
@Component({template: '', selector: 'v2-redirect'})
export class V2Redirect {
  constructor() {
    const router = inject(Router);
    const redirectedUrl = router.url.replace(/^\/v2(\/|$)/, '/');
    router.navigateByUrl(redirectedUrl, {replaceUrl: true});
  }
}
