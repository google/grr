'use strict';

goog.require('grrUi.docs.module');


describe('ApiHelperCurlService', function() {
  var $rootScope, grrApiHelperCurlService;

  beforeEach(module(grrUi.docs.module.name));

  beforeEach(module(function($provide) {
    $provide.value('$window', {
      location: {
        origin: 'http://localhost:42'
      }
    });
  }));

  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
    grrApiHelperCurlService = $injector.get('grrApiHelperCurlService');
  }));

  var startFlowRequest = `CSRFTOKEN=\`curl http://localhost:42 -o /dev/null -s -c - | grep csrftoken  | cut -f 7\`; \\
\tcurl -X POST -H "Content-Type: application/json" -H "X-CSRFToken: $CSRFTOKEN" \\
\thttp://localhost:42/api/v2/clients/C.1111222233334444/flows -d @- << EOF
{
  "foo": "bar"
}
EOF`;

  it('builds start flow request', function(done) {
    grrApiHelperCurlService.buildStartFlow(
        'C.1111222233334444', {foo: 'bar'}).then(function(cmd) {
          expect(cmd).toBe(startFlowRequest);
          done();
        }.bind(this));

    $rootScope.$apply();
  });
});
