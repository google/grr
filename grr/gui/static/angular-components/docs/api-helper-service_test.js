'use strict';

goog.require('grrUi.docs.module');


describe('ApiHelperService', function() {
  var $rootScope, $q, grrApiService, grrApiHelperService;

  beforeEach(module(grrUi.docs.module.name));

  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrApiHelperService = $injector.get('grrApiHelperService');

    var deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          type: 'RDFString',
          value: 'FooBarAuthManager'
        }
      }
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    grrApiHelperService.clear();
  }));

  var fooHelper = {
    buildStartFlow: function(clientId, createFlowJson) {
      var deferred = $q.defer();
      deferred.resolve('foo start ' + clientId);
      return deferred.promise;
    }
  };

  var barHelper = {
    buildStartFlow: function(clientId, createFlowJson) {
      var deferred = $q.defer();
      deferred.resolve('bar start ' + clientId);
      return deferred.promise;
    }
  };

  it('builds start flow commands with helpers of all types', function(done) {
    grrApiHelperService.registerHelper('Foo', null, fooHelper);
    grrApiHelperService.registerHelper('Bar', null, barHelper);

    grrApiHelperService.buildStartFlow('C.1111222233334444', {
      foo: 'bar'
    }).then(function(result) {
      expect(result).toEqual({
        'Foo': {
          webAuthType: null,
          data: 'foo start C.1111222233334444'
        },
        'Bar': {
          webAuthType: null,
          data: 'bar start C.1111222233334444'
        }
      });
      done();
    });

    $rootScope.$apply();
  });

  it('uses helper with a matching webAuthType, if available', function(done) {
    grrApiHelperService.registerHelper('Foo', null, fooHelper);
    grrApiHelperService.registerHelper('Foo', 'FooBarAuthManager', barHelper);

    grrApiHelperService.buildStartFlow('C.1111222233334444', {
      foo: 'bar'
    }).then(function(result) {
      expect(result).toEqual({
        'Foo': {
          webAuthType: 'FooBarAuthManager',
          data: 'bar start C.1111222233334444'
        }
      });
      done();
    });

    $rootScope.$apply();
  });

  it('uses helper with null webAuthType if no matches', function(done) {
    grrApiHelperService.registerHelper('Foo', null, fooHelper);
    grrApiHelperService.registerHelper('Foo', 'SomeOtherAuthManager',
                                       barHelper);

    grrApiHelperService.buildStartFlow('C.1111222233334444', {
      foo: 'bar'
    }).then(function(result) {
      expect(result).toEqual({
        'Foo': {
          webAuthType: null,
          data: 'foo start C.1111222233334444'
        }
      });
      done();
    });

    $rootScope.$apply();
  });

  it('ignores helpers if no matches and no helper with null webAuthType', function(done) {
    grrApiHelperService.registerHelper('Foo', 'YetAnotherAuthManager', fooHelper);
    grrApiHelperService.registerHelper('Foo', 'SomeOtherAuthManager',
                                       barHelper);

    grrApiHelperService.buildStartFlow('C.1111222233334444', {
      foo: 'bar'
    }).then(function(result) {
      expect(result).toEqual({});
      done();
    });

    $rootScope.$apply();
  });
});
