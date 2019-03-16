/*global Gallery,Dygraph,data */
Gallery.register(
  'avoid-min-zero',
  {
    name: "Avoid Min Zero",
    setup: function(parent) {
      parent.innerHTML =
          "<p>1: Line chart with axis at zero problem:</p><div id='graph1'></div> " +
          "<p>2: Step chart with axis at zero problem:</p><div id='graphd2'></div> " +
          "<p>3: Line chart with <code>avoidMinZero</code> option:</p><div id='graph3'></div> " +
          "<p>4: Step chart with <code>avoidMinZero</code> option:</p><div id='graphd4'></div> ";
    },
    run: function() {
    new Dygraph(document.getElementById("graph1"),
        "Date,Temperature\n" +
        "2008-05-07,0\n" +
        "2008-05-08,1\n" +
        "2008-05-09,0\n" +
        "2008-05-10,0\n" +
        "2008-05-11,3\n" +
        "2008-05-12,4\n"
    );
    new Dygraph(document.getElementById("graphd2"),
        "Date,Temperature\n" +
        "2008-05-07,0\n" +
        "2008-05-08,1\n" +
        "2008-05-09,0\n" +
        "2008-05-10,0\n" +
        "2008-05-11,3\n" +
        "2008-05-12,4\n",
        {
           stepPlot: true
        }
    );
    new Dygraph(document.getElementById("graph3"),
        "Date,Temperature\n" +
        "2008-05-07,0\n" +
        "2008-05-08,1\n" +
        "2008-05-09,0\n" +
        "2008-05-10,0\n" +
        "2008-05-11,3\n" +
        "2008-05-12,4\n",
        {
            avoidMinZero: true
        }
    );
    new Dygraph(document.getElementById("graphd4"),
        "Date,Temperature\n" +
        "2008-05-07,0\n" +
        "2008-05-08,1\n" +
        "2008-05-09,0\n" +
        "2008-05-10,0\n" +
        "2008-05-11,3\n" +
        "2008-05-12,4\n",
        {
           stepPlot: true,
           avoidMinZero: true
        }
    );
  }
});
