'use strict';

goog.require('grrUi.stats.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

describe('audit chart directive', function() {
  var $compile, $rootScope, typedData;

  beforeEach(module(
      '/static/angular-components/stats/audit-chart.html'));
  beforeEach(module(grrUi.stats.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(typedData) {
    $rootScope.typedData = typedData;

    var template = '<grr-audit-chart typed-data="typedData">' +
                   '</grr-audit-chart>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if the given data is undefined', function() {
    var element = renderTestTemplate(undefined);

    expect(element.find('th').length).toBe(0);
    expect(element.find('td').length).toBe(0);
  });

  it('shows the given data', function() {
    var element = renderTestTemplate({
      'value': {
        'audit_chart': {
          'value': {
            'rows': [
              {
                'value': {
                  'action': {
                    'value': 'HUNT_CREATED',
                    'type': 'EnumNamedValue'
                  },
                  'user': {
                    'value': 'GRRWorker',
                    'type': 'unicode'
                  },
                  'id': {
                    'value': 123,
                    'type': 'long'
                  },
                  'timestamp': {
                    'value': 1485174411000000,
                    'type': 'RDFDatetime'
                  },
                  'description': {
                    'value': 'Description of the hunt.',
                    'type': 'unicode'
                  },
                  'flow_name': {
                    'value': 'Flow Foo.',
                    'type': 'unicode'
                  },
                  'urn': {
                    'value': 'aff4:/hunts/H:12345678',
                    'type': 'RDFURN'
                  }
                },
                'type': 'AuditEvent'
              },
              {
                'value': {
                  'action': {
                    'value': 'HUNT_STARTED',
                    'type': 'EnumNamedValue'
                  },
                  'user': {
                    'value': 'GRRWorker',
                    'type': 'unicode'
                  },
                  'id': {
                    'value': 456,
                    'type': 'long'
                  },
                  'timestamp': {
                    'value': 1485174502000000,
                    'type': 'RDFDatetime'
                  },
                  'description': {
                    'value': 'Description of another hunt.',
                    'type': 'unicode'
                  },
                  'urn': {
                    'value': 'aff4:/hunts/H:87654321',
                    'type': 'RDFURN'
                  }
                },
                'type': 'AuditEvent'
              }
            ],
            'used_fields': [
              {
                'value': 'action',
                'type': 'unicode'
              },
              {
                'value': 'description',
                'type': 'unicode'
              },
              {
                'value': 'flow_name',
                'type': 'unicode'
              },
              {
                'value': 'timestamp',
                'type': 'unicode'
              },
              {
                'value': 'urn',
                'type': 'unicode'
              },
              {
                'value': 'user',
                'type': 'unicode'
              }
            ]
          },
          'type': 'ApiAuditChartReportData'
        },
        'representation_type': {
          'value': 'AUDIT_CHART',
          'type': 'EnumNamedValue'
        }
      },
      'type': 'ApiReportData'
    });

    var ths = element.find('th');
    expect(ths.length).toBe(6);
    // Labels are sorted alphabetically.
    expect(ths[0].innerText).toContain('Action');
    expect(ths[1].innerText).toContain('Description');
    expect(ths[2].innerText).toContain('Flow name');
    expect(ths[3].innerText).toContain('Timestamp');
    expect(ths[4].innerText).toContain('Urn');
    expect(ths[5].innerText).toContain('User');

    var tbodyTrs = element.find('tbody tr');
    expect(tbodyTrs.length).toBe(2);

    var getCellValue = function(td) {
      var semVal = $(td).find('grr-semantic-value');
      return semVal.scope().$eval(semVal.attr('value'));
    };

    var row0Tds = $(tbodyTrs[0]).find('td');
    expect(row0Tds.length).toBe(6);
    // Fields are sorted by label.
    expect(getCellValue(row0Tds[0])).toEqual({
      'value': 'HUNT_CREATED',
      'type': 'EnumNamedValue'
    });
    expect(getCellValue(row0Tds[1])).toEqual({
      'value': 'Description of the hunt.',
      'type': 'unicode'
    });
    expect(getCellValue(row0Tds[2])).toEqual({
      'value': 'Flow Foo.',
      'type': 'unicode'
    });
    expect(getCellValue(row0Tds[3])).toEqual({
      'value': 1485174411000000,
      'type': 'RDFDatetime'
    });
    expect(getCellValue(row0Tds[4])).toEqual({
      'value': 'aff4:/hunts/H:12345678',
      'type': 'RDFURN'
    });
    expect(getCellValue(row0Tds[5])).toEqual({
      'value': 'GRRWorker',
      'type': 'unicode'
    });

    var row1Tds = $(tbodyTrs[1]).find('td');
    expect(row1Tds.length).toBe(6);
    // Fields are sorted by label.
    expect(getCellValue(row1Tds[0])).toEqual({
      'value': 'HUNT_STARTED',
      'type': 'EnumNamedValue'
    });
    expect(getCellValue(row1Tds[1])).toEqual({
      'value': 'Description of another hunt.',
      'type': 'unicode'
    });
    expect(getCellValue(row1Tds[2])).toBe(undefined);
    expect(getCellValue(row1Tds[3])).toEqual({
      'value': 1485174502000000,
      'type': 'RDFDatetime'
    });
    expect(getCellValue(row1Tds[4])).toEqual({
      'value': 'aff4:/hunts/H:87654321',
      'type': 'RDFURN'
    });
    expect(getCellValue(row1Tds[5])).toEqual({
      'value': 'GRRWorker',
      'type': 'unicode'
    });
  });

});
