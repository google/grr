/*global Gallery,Dygraph,data */
Gallery.register(
  'dygraph-simple',  
  {
    name: 'Minimal Example',
    setup: function(parent) {
      parent.innerHTML = "<p>Minimal example of a dygraph chart:</p><div id='graphdiv'></div>" +
      "<p>Same data, specified in a parsed format:</p><div id='graphdiv2'></div>";
    },
    run: function() {
      new Dygraph(document.getElementById("graphdiv"),
          "Date,Temperature\n" +
          "2008-05-07,75\n" +
          "2008-05-08,70\n" +
          "2008-05-09,80\n");
      new Dygraph(document.getElementById("graphdiv2"),
          [ [ new Date("2008/05/07"), 75],
          [ new Date("2008/05/08"), 70],
          [ new Date("2008/05/09"), 80]
          ],
          {
            labels: [ "Date", "Temperature" ]
          });
    }
  });
