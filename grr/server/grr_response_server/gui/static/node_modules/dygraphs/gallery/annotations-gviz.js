/*global Gallery,Dygraph,data */
/*global google */
Gallery.register(
  'annotations-gviz',
  {
    name: 'Annotation Gviz (broken)',
    title: 'Comparison of Gviz and Dygraphs annotated timelines',
    setup : function(parent) {
      parent.innerHTML = 
          "<h3>Google AnnotatedTimeline:</h3>" +
          "<div id='gviz_div' style='width: 700px; height: 240px;'></div>" +
          "<h3>Dygraph.GVizChart:</h3>" +
          "<div id='dg_div' style='width: 700px; height: 240px;'></div>";
    },
    run: function() {
      var drawChart = function() {
        var data = new google.visualization.DataTable();
        data.addColumn('date', 'Date');
        data.addColumn('number', 'Sold Pencils');
        data.addColumn('string', 'title1');
        data.addColumn('string', 'text1');
        data.addColumn('number', 'Sold Pens');
        data.addColumn('string', 'title2');
        data.addColumn('string', 'text2');
        data.addRows([
          [new Date(2008, 1 ,1), 30000, undefined, undefined, 40645, undefined, undefined],
          [new Date(2008, 1 ,2), 14045, undefined, undefined, 20374, undefined, undefined],
          [new Date(2008, 1 ,3), 55022, undefined, undefined, 50766, undefined, undefined],
          [new Date(2008, 1 ,4), 75284, undefined, undefined, 14334, 'Out of Stock','Ran out of stock on pens at 4pm'],
          [new Date(2008, 1 ,5), 41476, 'Bought Pens','Bought 200k pens', 66467, undefined, undefined],
          [new Date(2008, 1 ,6), 33322, undefined, undefined, 39463, undefined, undefined]
        ]);

        var chart = new google.visualization.AnnotatedTimeLine(document.getElementById('gviz_div'));
        chart.draw(data, {displayAnnotations: true});

      };
      google.setOnLoadCallback(drawChart);
      var f = function() { alert("!"); };
      google.setOnLoadCallback(f);
      var g = new Dygraph.GVizChart(document.getElementById("dg_div"));
      g.draw(data, {displayAnnotations: true, labelsKMB: true});
    }
  });
