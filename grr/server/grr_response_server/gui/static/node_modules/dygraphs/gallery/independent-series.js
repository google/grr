/*global Gallery,Dygraph,data */
Gallery.register(
  'independent-series',
  {
    name: 'Independent Series',
    title: 'Independent Series',
    setup: function(parent) {
      parent.innerHTML = [
    "<p>By using the <i>connectSeparated</i> attribute, it's possible to display a chart of several time series with completely independent x-values.</p> ",
    "",
    "<p>The trick is to specify values for the series at the union of the x-values of all series. For one series' x values, specify <code>null</code> for each of the other series.</p> ",
    "",
    "<div id='graph' style='float: right; margin-right: 50px; width: 400px; height: 300px;'></div> ",
    "<p>For example, say you had two series:</p> ",
    "<table><tr> ",
    "<td valign=top> ",
    "<table> ",
    "  <table class='thinborder'> ",
    "    <tr><th>x</th><th>A</th></tr> ",
    "    <tr><td>2</td><td>2</td></tr> ",
    "    <tr><td>4</td><td>6</td></tr> ",
    "    <tr><td>6</td><td>4</td></tr> ",
    "  </table> ",
    "</td> ",
    "<td valign=top style='padding-left:25px;'> ",
    "  <table class='thinborder'> ",
    "    <tr><th>x</th><th>B</th></tr> ",
    "    <tr><td>1</td><td>3</td></tr> ",
    "    <tr><td>3</td><td>7</td></tr> ",
    "    <tr><td>5</td><td>5</td></tr> ",
    "  </table> ",
    "</td> ",
    "</tr></table> ",
    "",
    "<p>Then you would specify the following CSV or native data:</p> ",
    "<table><tr> ",
    "<td valign=top> ",
    "(CSV) ",
    "<pre id='csv1'></pre> ",
    "</td> ",
    "<td valign=top style='padding-left: 25px;'>",
    "(native) ",
    "<pre id='native1'></pre> ",
    "</td> ",
    "</tr></table> ",
    "",
    "<h3>Encoding a gap</h3>",
    "<p>There's one extra wrinkle. What if one of the series has a missing ",
    "value, i.e. what if your series are something like </p> ",
    "",
    "<table><tr> ",
    "<td valign=top> ",
    "<table> ",
    "  <table class='thinborder'> ",
    "    <tr><th>x</th><th>A</th></tr> ",
    "    <tr><td>2</td><td>2</td></tr> ",
    "    <tr><td>4</td><td>4</td></tr> ",
    "    <tr><td>6</td><td>(gap)</td></tr> ",
    "    <tr><td>8</td><td>8</td></tr> ",
    "    <tr><td>10</td><td>10</td></tr> ",
    "  </table> ",
    "</td> ",
    "<td valign=top style='padding-left:25px;'> ",
    "  <table class='thinborder'> ",
    "    <tr><th>x</th><th>B</th></tr> ",
    "    <tr><td>1</td><td>3</td></tr> ",
    "    <tr><td>3</td><td>5</td></tr> ",
    "    <tr><td>5</td><td>7</td></tr> ",
    "  </table> ",
    "</td> ",
    "</tr></table> ",
    "",
    "<div id='graph2' style='float: right; margin-right: 50px; width: 400px; height: 300px;'></div> ",
    "<p>The gap would normally be encoded as a null, or missing value. But when you use <code>connectSeparatedPoints</code>, that has a special meaning. Instead, you have to use <code>NaN</code>. This is a bit of a hack, but it gets the job done.</p> ",
    "",
    "<table><tr> ",
    "<td valign=top> ",
    "(CSV) ",
    "<pre id='csv2'></pre> ",
    "</td> ",
    "<td valign=top style='padding-left: 25px;'> ",
    "(native) ",
    "<pre id='native2'></pre> ",
    "</td> ",
    "</tr></table>"].join("\n");
    },
    run: function() {
      document.getElementById("csv1").textContent =
          "X,A,B\n" +
          "1,,3\n" +
          "2,2,\n" +
          "3,,7\n" +
          "4,6,\n" +
          "5,,5\n" +
          "6,4,";

      document.getElementById("native1").textContent =
          "[\n" +
          "  [1, null, 3],\n" +
          "  [2, 2, null],\n" +
          "  [3, null, 7],\n" +
          "  [4, 6, null],\n" +
          "  [5, null, 5],\n" +
          "  [6, 4, null]\n" +
          "]";

      document.getElementById("csv2").textContent =
          "X,A,B\n" +
          "1,,3\n" +
          "2,2,\n" +
          "3,,5\n" +
          "4,4,\n" +
          "6,Nan,\n" +
          "8,8,\n" +
          "10,10,";

      document.getElementById("native2").textContent =
          "[\n" +
          "  [1, null, 3],\n" +
          "  [2, 2, null],\n" +
          "  [3, null, 5],\n" +
          "  [4, 4, null],\n" +
          "  [5, null, 7],\n" +
          "  [6, NaN, null],\n" +
          "  [8, 8, null]\n" +
          "  [10, 10, null]\n" +
          "]";

      new Dygraph(
        document.getElementById('graph'),
        [
          [1, null, 3],
          [2, 2, null],
          [3, null, 7],
          [4, 5, null],
          [5, null, 5],
          [6, 3, null]
        ],
        {
          labels: ['x', 'A', 'B' ],
          connectSeparatedPoints: true,
          drawPoints: true
        }
      );

    new Dygraph(
      document.getElementById('graph2'),
      'x,A,B  \n' +
      '1,,3   \n' +
      '2,2,   \n' +
      '3,,5   \n' +
      '4,4,   \n' +
      '5,,7   \n' +
      '6,NaN, \n' +
      '8,8,   \n' +
      '10,10, \n',
      {
        labels: ['x', 'A', 'B' ],
        connectSeparatedPoints: true,
        drawPoints: true
      }
    );
    }
  });

