// tslint:disable:no-any

import {convertToParamMap} from '@angular/router';

import {initTestEnvironment} from '../testing';

import {makeLegacyLink, makeLegacyLinkFromRoute} from './routing';

initTestEnvironment();


describe('makeLegacyLinkFromRoute', () => {
  it('uses route params from child, then parent routes', () => {
    const route = {
      params: {'barId': '456'},
      paramMap: convertToParamMap({'barId': '456'}),
      queryParams: {},
      data: {legacyLink: '#/foo/:fooId/bar/:barId'},
      parent: {
        params: {'fooId': '123'},
        paramMap: convertToParamMap({'fooId': '123'}),
        queryParams: {},
        data: {legacyLink: '#/foo/:fooId'},
      },
    };

    expect(makeLegacyLinkFromRoute(route as any))
        .toEqual(`${makeLegacyLink()}#/foo/123/bar/456`);
  });
});
