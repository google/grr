import {ActivatedRouteSnapshot} from '@angular/router';

/** A Route with a template string ('#/clients/:id') to link to the old UI. */
export declare interface RouteWithLegacyLink {
  data: {legacyLink: string;};
}

/** Routes with `data.legacyLink` that link to the old UI. */
export type RoutesWithLegacyLinks = RouteWithLegacyLink[];

/** Constructs a link to the old UI by parsing a Route's data.legacyLink. */
export function makeLegacyLinkFromRoute(route: ActivatedRouteSnapshot): string {
  let legacyLink: string = route.data['legacyLink'] ?? '';

  for (const [key, value] of Object.entries(route.params)) {
    legacyLink = legacyLink.replace(`:${key}`, value);
  }

  for (const [key, value] of Object.entries(route.queryParams)) {
    legacyLink = legacyLink.replace(`:${key}`, encodeURIComponent(value));
  }

  return makeLegacyLink(legacyLink);
}

/** Returns a link to the old UI, e.g. provide '#/clients/'. */
export function makeLegacyLink(suffix: string = ''): string {
  const url = new URL(window.location.origin);
  url.pathname = '/';
  url.hash = '';
  return url.toString() + suffix;
}
