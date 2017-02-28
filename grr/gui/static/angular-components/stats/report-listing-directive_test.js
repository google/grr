'use strict';

goog.require('grrUi.stats.reportListingDirective.parseStatsReportsApiResponse');

goog.scope(function() {

describe('stats.reportListingDirective.parseStatsReportsApiResponse', function() {

  it('Parses the response into a jsTree-compatible format.', function() {
    var reports = [{
      desc: {
        name: 'FooReportPlugin',
        title: 'Foos\' Activity',
        type: 'SERVER',
      }
    }, {
      desc: {
        name: 'BarReportPlugin',
        title: 'Bars Reported Over Time',
        type: 'SERVER',
      }
    }, {
      desc: {
        name: 'BazReportPlugin',
        title: 'Baz Statistics',
        type: 'CLIENT',
      }
    }];

    var ret = grrUi.stats.reportListingDirective.parseStatsReportsApiResponse(
        reports);

    expect(ret).toEqual([
      {
        children:[
          {
            desc: {
              name: 'FooReportPlugin',
              title: 'Foos\' Activity',
              type: 'SERVER'
            },
            id: 'FooReportPlugin',
            text: 'Foos\' Activity'
          },
          {
            desc: {
              name: 'BarReportPlugin',
              title: 'Bars Reported Over Time',
              type: 'SERVER'
            },
            id: 'BarReportPlugin',
            text: 'Bars Reported Over Time'
          }
        ],
        state: {
          disabled: true,
          opened: true
        },
        text: 'Server'
      },
      {
        children:[
          {
            desc: {
              name: 'BazReportPlugin',
              title: 'Baz Statistics',
              type: 'CLIENT'
            },
            id: 'BazReportPlugin',
            text: 'Baz Statistics'
          }
        ],
        state: {
          disabled: true,
          opened: true
        },
        text: 'Client'
      }
    ]);
  });

});

});  // goog.scope
