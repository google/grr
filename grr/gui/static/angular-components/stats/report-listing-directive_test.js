'use strict';

goog.require('grrUi.stats.reportListingDirective.parseStatsReportsApiResponse');

goog.scope(function() {

describe('stats.reportListingDirective.parseStatsReportsApiResponse', function() {

  it('Parses the response into a jsTree-compatible format.', function() {
    var typedReports = [
      {value: {desc: {value:{
        name: {value: 'FooReportPlugin'},
        title: {value: 'Foos\' Activity'},
        type: {value: 'SERVER'},
      }}}},

      {value: {desc: {value:{
        name: {value: 'BarReportPlugin'},
        title: {value: 'Bars Reported Over Time'},
        type: {value: 'SERVER'},
      }}}},

      {value: {desc: {value:{
        name: {value: 'BazReportPlugin'},
        title: {value: 'Baz Statistics'},
        type: {value: 'CLIENT'},
      }}}}
    ];

    var ret = grrUi.stats.reportListingDirective.parseStatsReportsApiResponse(
        typedReports);

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
