'use strict';

goog.module('grrUi.stats.auditChartDirectiveTest');

const {statsModule} = goog.require('grrUi.stats.stats');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('audit chart directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(
      '/static/angular-components/stats/audit-chart.html'));
  beforeEach(module(statsModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (typedData) => {
    $rootScope.typedData = typedData;

    const template = '<grr-audit-chart typed-data="typedData">' +
        '</grr-audit-chart>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if the given data is undefined', () => {
    const element = renderTestTemplate(undefined);

    expect(element.find('th').length).toBe(0);
    expect(element.find('td').length).toBe(0);
  });

  it('shows the given data', () => {
    const element = renderTestTemplate({
      'value': {
        'audit_chart': {
          'value': {
            'rows': [
              {
                'value': {
                  'action': {
                    'value': 'HUNT_CREATED',
                    'type': 'EnumNamedValue',
                  },
                  'user': {
                    'value': 'GRRWorker',
                    'type': 'unicode',
                  },
                  'id': {
                    'value': 123,
                    'type': 'long',
                  },
                  'timestamp': {
                    'value': 1485174411000000,
                    'type': 'RDFDatetime',
                  },
                  'description': {
                    'value': 'Description of the hunt.',
                    'type': 'unicode',
                  },
                  'flow_name': {
                    'value': 'Flow Foo.',
                    'type': 'unicode',
                  },
                  'urn': {
                    'value': 'aff4:/hunts/H:12345678',
                    'type': 'RDFURN',
                  },
                },
                'type': 'AuditEvent',
              },
              {
                'value': {
                  'action': {
                    'value': 'HUNT_STARTED',
                    'type': 'EnumNamedValue',
                  },
                  'user': {
                    'value': 'GRRWorker',
                    'type': 'unicode',
                  },
                  'id': {
                    'value': 456,
                    'type': 'long',
                  },
                  'timestamp': {
                    'value': 1485174502000000,
                    'type': 'RDFDatetime',
                  },
                  'description': {
                    'value': 'Description of another hunt.',
                    'type': 'unicode',
                  },
                  'urn': {
                    'value': 'aff4:/hunts/H:87654321',
                    'type': 'RDFURN',
                  },
                },
                'type': 'AuditEvent',
              },
            ],
            'used_fields': [
              {
                'value': 'action',
                'type': 'unicode',
              },
              {
                'value': 'description',
                'type': 'unicode',
              },
              {
                'value': 'flow_name',
                'type': 'unicode',
              },
              {
                'value': 'timestamp',
                'type': 'unicode',
              },
              {
                'value': 'urn',
                'type': 'unicode',
              },
              {
                'value': 'user',
                'type': 'unicode',
              },
            ],
          },
          'type': 'ApiAuditChartReportData',
        },
        'representation_type': {
          'value': 'AUDIT_CHART',
          'type': 'EnumNamedValue',
        },
      },
      'type': 'ApiReportData',
    });

    const ths = element.find('th');
    expect(ths.length).toBe(6);
    // Labels are sorted alphabetically.
    expect(ths[0].innerText).toContain('Action');
    expect(ths[1].innerText).toContain('Description');
    expect(ths[2].innerText).toContain('Flow name');
    expect(ths[3].innerText).toContain('Timestamp');
    expect(ths[4].innerText).toContain('Urn');
    expect(ths[5].innerText).toContain('User');

    const tbodyTrs = element.find('tbody tr');
    expect(tbodyTrs.length).toBe(2);

    const getCellValue = ((td) => {
      const semVal = $(td).find('grr-semantic-value');
      return semVal.scope().$eval(semVal.attr('value'));
    });

    const row0Tds = $(tbodyTrs[0]).find('td');
    expect(row0Tds.length).toBe(6);
    // Fields are sorted by label.
    expect(getCellValue(row0Tds[0])).toEqual({
      'value': 'HUNT_CREATED',
      'type': 'EnumNamedValue',
    });
    expect(getCellValue(row0Tds[1])).toEqual({
      'value': 'Description of the hunt.',
      'type': 'unicode',
    });
    expect(getCellValue(row0Tds[2])).toEqual({
      'value': 'Flow Foo.',
      'type': 'unicode',
    });
    expect(getCellValue(row0Tds[3])).toEqual({
      'value': 1485174411000000,
      'type': 'RDFDatetime',
    });
    expect(getCellValue(row0Tds[4])).toEqual({
      'value': 'aff4:/hunts/H:12345678',
      'type': 'RDFURN',
    });
    expect(getCellValue(row0Tds[5])).toEqual({
      'value': 'GRRWorker',
      'type': 'unicode',
    });

    const row1Tds = $(tbodyTrs[1]).find('td');
    expect(row1Tds.length).toBe(6);
    // Fields are sorted by label.
    expect(getCellValue(row1Tds[0])).toEqual({
      'value': 'HUNT_STARTED',
      'type': 'EnumNamedValue',
    });
    expect(getCellValue(row1Tds[1])).toEqual({
      'value': 'Description of another hunt.',
      'type': 'unicode',
    });
    expect(getCellValue(row1Tds[2])).toBe(undefined);
    expect(getCellValue(row1Tds[3])).toEqual({
      'value': 1485174502000000,
      'type': 'RDFDatetime',
    });
    expect(getCellValue(row1Tds[4])).toEqual({
      'value': 'aff4:/hunts/H:87654321',
      'type': 'RDFURN',
    });
    expect(getCellValue(row1Tds[5])).toEqual({
      'value': 'GRRWorker',
      'type': 'unicode',
    });
  });
});


exports = {};
