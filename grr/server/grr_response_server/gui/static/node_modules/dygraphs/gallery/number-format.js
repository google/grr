/*global Gallery,Dygraph,data */
Gallery.register(
  'number-format',
  {
    name: 'Number formatting',
    setup: function(parent) {
      parent.innerHTML = 
          "<p>The default formatting mimicks printf with %.<i>p</i>g where <i>p</i> is" +
          "   the precision to use.  It turns out that JavaScript's toPrecision()" +
          "   method is almost but not exactly equal to %g; they differ for values" +
          "   with small absolute values (10^-1 to 10^-5 or so), with toPrecision()" +
          "   yielding strings that are longer than they should be (i.e. using fixed" +
          "   point where %g would use exponential).</p>" +

          "<p>This test is intended to check that our formatting works properly for a" +
          "   variety of precisions.</p>" +

          "<p>Precision to use (1 to 21):" +
          "  <input type='text' id='p_input' size='20'></p>" +
          "<p/>" +
          "<div id='content' style='font-family:Courier New,monospace'></div>";
    },
    run: function() {
      // Helper functions for generating an HTML table for holding the test
      // results.
      var createRow = function(columnType, columns) {
        var row = document.createElement('tr');
        for (var i = 0; i  < columns.length; i ++) {
          var th = document.createElement(columnType);
          var text = document.createTextNode(columns[i]);
          th.appendChild(text);
          row.appendChild(th);
        }
        return row;
      };

      var createHeaderRow = function(columns) {
        return createRow('th', columns);
      };

      var createDataRow = function(columns) {
        return createRow('td', columns);
      };

      var createTable = function(headerColumns, dataColumnsList) {
        var table = document.createElement('table');
        table.appendChild(createHeaderRow(headerColumns));
        for (var i = 0; i < dataColumnsList.length; i++) {
          table.appendChild(createDataRow(dataColumnsList[i]));
        }
        return table;
      };

      var updateTable = function() {
        var headers = ['Dygraph.floatFormat()', 'toPrecision()',
                       'Dygraph.floatFormat()', 'toPrecision()'];
        var numbers = [];
        var p = parseInt(document.getElementById('p_input').value, 10);

        for (var i = -10; i <= 10; i++) {
          var n = Math.pow(10, i);
          numbers.push([Dygraph.floatFormat(n, p),
                        n.toPrecision(p),
                        Dygraph.floatFormat(Math.PI * n, p),
                        (Math.PI * n).toPrecision(p)]);
        }

        // Check exact values of 0.
        numbers.push([Dygraph.floatFormat(0.0, p),
                      (0.0).toPrecision(p)]);

        var elem = document.getElementById('content');
        elem.innerHTML = '';
        elem.appendChild(createTable(headers, numbers));
      };

      document.getElementById('p_input').value = '4';
      document.getElementById('p_input').onchange = updateTable;
      updateTable();
    }
  });
