'use strict';

goog.module('grrUi.docs.apiHelperServiceTest');

const {docsModule} = goog.require('grrUi.docs.docs');


describe('ApiHelperService', () => {
  let $q;
  let $rootScope;
  let grrApiHelperService;
  let grrApiService;


  beforeEach(module(docsModule.name));

  beforeEach(inject(($injector) => {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrApiHelperService = $injector.get('grrApiHelperService');

    const deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          type: 'RDFString',
          value: 'FooBarAuthManager',
        },
      },
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    grrApiHelperService.clear();
  }));

  const fooHelper = {
    buildStartFlow: function(clientId, createFlowJson) {
      const deferred = $q.defer();
      deferred.resolve(`foo start ${clientId}`);
      return deferred.promise;
    },
  };

  const barHelper = {
    buildStartFlow: function(clientId, createFlowJson) {
      const deferred = $q.defer();
      deferred.resolve(`bar start ${clientId}`);
      return deferred.promise;
    },
  };

  it('builds start flow commands with helpers of all types', (done) => {
    grrApiHelperService.registerHelper('Foo', null, fooHelper);
    grrApiHelperService.registerHelper('Bar', null, barHelper);

    grrApiHelperService
        .buildStartFlow('C.1111222233334444', {
          foo: 'bar',
        })
        .then((result) => {
          expect(result).toEqual({
            'Foo': {
              webAuthType: null,
              data: 'foo start C.1111222233334444',
            },
            'Bar': {
              webAuthType: null,
              data: 'bar start C.1111222233334444',
            },
          });
          done();
        });

    $rootScope.$apply();
  });

  it('uses helper with a matching webAuthType, if available', (done) => {
    grrApiHelperService.registerHelper('Foo', null, fooHelper);
    grrApiHelperService.registerHelper('Foo', 'FooBarAuthManager', barHelper);

    grrApiHelperService
        .buildStartFlow('C.1111222233334444', {
          foo: 'bar',
        })
        .then((result) => {
          expect(result).toEqual({
            'Foo': {
              webAuthType: 'FooBarAuthManager',
              data: 'bar start C.1111222233334444',
            },
          });
          done();
        });

    $rootScope.$apply();
  });

  it('uses helper with null webAuthType if no matches', (done) => {
    grrApiHelperService.registerHelper('Foo', null, fooHelper);
    grrApiHelperService.registerHelper('Foo', 'SomeOtherAuthManager',
                                       barHelper);

    grrApiHelperService
        .buildStartFlow('C.1111222233334444', {
          foo: 'bar',
        })
        .then((result) => {
          expect(result).toEqual({
            'Foo': {
              webAuthType: null,
              data: 'foo start C.1111222233334444',
            },
          });
          done();
        });

    $rootScope.$apply();
  });

  it('ignores helpers if no matches and no helper with null webAuthType',
     (done) => {
       grrApiHelperService.registerHelper(
           'Foo', 'YetAnotherAuthManager', fooHelper);
       grrApiHelperService.registerHelper(
           'Foo', 'SomeOtherAuthManager', barHelper);

       grrApiHelperService
           .buildStartFlow('C.1111222233334444', {
             foo: 'bar',
           })
           .then((result) => {
             expect(result).toEqual({});
             done();
           });

       $rootScope.$apply();
     });
});


exports = {};
