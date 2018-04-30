'use strict';

goog.module('grrUi.stats.reportListingDirectiveTest');

const {parseStatsReportsApiResponse} = goog.require('grrUi.stats.reportListingDirective');

describe('stats.reportListingDirective.parseStatsReportsApiResponse', () => {
  it('Parses the response into a jsTree-compatible format.', () => {
    const reports = [
      {
        desc: {
          name: 'FooReportPlugin',
          title: 'Foos\' Activity',
          type: 'SERVER',
        },
      },
      {
        desc: {
          name: 'BarReportPlugin',
          title: 'Bars Reported Over Time',
          type: 'SERVER',
        },
      },
      {
        desc: {
          name: 'BazReportPlugin',
          title: 'Baz Statistics',
          type: 'CLIENT',
        },
      }
    ];

    const ret = parseStatsReportsApiResponse(reports);

    expect(ret).toEqual([
      {
        children: [
          {
            desc: {
              name: 'FooReportPlugin',
              title: 'Foos\' Activity',
              type: 'SERVER',
            },
            id: 'FooReportPlugin',
            text: 'Foos\' Activity',
          },
          {
            desc: {
              name: 'BarReportPlugin',
              title: 'Bars Reported Over Time',
              type: 'SERVER',
            },
            id: 'BarReportPlugin',
            text: 'Bars Reported Over Time',
          },
        ],
        state: {
          disabled: true,
          opened: true,
        },
        text: 'Server',
      },
      {
        children: [
          {
            desc: {
              name: 'BazReportPlugin',
              title: 'Baz Statistics',
              type: 'CLIENT',
            },
            id: 'BazReportPlugin',
            text: 'Baz Statistics',
          },
        ],
        state: {
          disabled: true,
          opened: true,
        },
        text: 'Client',
      },
    ]);
  });
});


exports = {};
