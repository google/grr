/*
* jQuery.splitter.js - animated splitter plugin
*
* version 1.0 (2010/01/02)
*
* Dual licensed under the MIT and GPL licenses:
*   http://www.opensource.org/licenses/mit-license.php
*   http://www.gnu.org/licenses/gpl.html
*
* Code cleaned up and made to pass jslint <scudette@gmail.com>. Also
* changed default behaviour to not animate when dragged.
*
*/

/**
* jQuery.splitter() plugin implements a two-pane resizable animated
* window, using existing DIV elements for layout.  For more details
* and demo visit: http://krikus.com/js/splitter
*
* @example $("#splitterContainer")
*               .splitter({
*                    splitVertical:true,
*                    A:$('#leftPane'),
*                    B:$('#rightPane'),
*                    closeableto:0});
*
* @desc Create a vertical splitter with toggle button.
*
* @example $("#splitterContainer")
*               .splitter({
*                   minAsize:100,
*                   maxAsize:300,
*                   splitVertical:true,
*                   A:$('#leftPane'),
*                   B:$('#rightPane'),
*                   slave:$("#rightSplitterContainer"),
*                   closeableto:0});
*
* @desc Create a vertical splitter with toggle button, with minimum
* and maximum width for plane A and bind resize event to the slave
* element.
*
* @name splitter
* @type jQuery
* @param Object options Options for the splitter ( required).
* @cat Plugins/Splitter
* @return jQuery.
* @author Kristaps Kukurs (contact@krikus.com)
*/

(function($) {
   $.fn.splitter = function(args) {
     args = args || {};
     return this.each(function() {
         splitterImpl($(this), args);//end each
         });//end splitter
     };
})(jQuery);


function splitterImpl(splitter, args) {
  var _ghost;    //splitbar  ghosted element
  var splitPos;  // current splitting position
  var _splitPos; // saved splitting position
  var _initPos;  //initial mouse position
  var _ismovingNow = false; // animaton state flag

  // Default opts
  var direction = (args.splitHorizontal ? 'h' : 'v');
  var opts = $.extend({ minAsize: 0, //minimum width/height in PX of
                                     //the first (A) div.
                        maxAsize: 0, //maximum width/height in PX of
                                     //the first (A) div.
                        minBsize: 0, //minimum width/height in PX of
                                     //the second (B) div.
                        maxBsize: 0, //maximum width/height in PX of
                                     //the second (B) div.
                        ghostClass: 'working',// class name for
                                              // _ghosted splitter and
                                              // hovered button
                        invertClass: 'invert',//class name for invert
                                              //splitter button
                        animSpeed: 250 //animation speed in ms
                      },{
                        v: { // Vertical
                          moving: 'left',
                          sizing: 'width',
                          eventPos: 'pageX',
                          splitbarClass: 'splitbarV',
                          buttonClass: 'splitbuttonV',
                          cursor: 'e-resize'
                          },
                        h: { // Horizontal
                          moving: 'top',
                          sizing: 'height',
                          eventPos: 'pageY',
                          splitbarClass: 'splitbarH',
                          buttonClass: 'splitbuttonH',
                          cursor: 'n-resize'
                        }}[direction], args);

  //setup elements
  var mychilds = splitter.children(); //$(">*", splitter[0]);
  var A = args.A;        // left/top frame
  var B = args.B;// right/bottom frame
  var slave = args.slave;//optional, elemt forced to receive resize event

  //Create splitbar
  var C = $('<div><span></span></div>');

  A.after(C);

  C.attr({ 'class': opts.splitbarClass,
           unselectable: 'on' })

    .css({ 'cursor': opts.cursor,
           'user-select': 'none',
           '-webkit-user-select': 'none',
           '-khtml-user-select': 'none',
           '-moz-user-select': 'none'})
    .bind('mousedown', startDrag);

  if (opts.closeableto != undefined) {
    var Bt = $('<div></div>').css('cursor', 'pointer');

    C.append(Bt);
    Bt.attr({ 'class': opts.buttonClass,
              unselectable: 'on'
            });

    Bt.hover(function() {
               $(this).addClass(opts.ghostClass);
             }, function() {
               $(this).removeClass(opts.ghostClass);
             });

    Bt.mousedown(function(e) {
        if (e.target != this) return false;

        Bt.toggleClass(opts.invertClass).hide();
        splitTo((splitPos == opts.closeableto) ?
            _splitPos : opts.closeableto, true, true);
        return false;
        });
  }

  //reset size to default.
  var perc = (A[opts.sizing]() / splitter[opts.sizing]() * 100).toFixed(1);

  splitTo(perc, false, true);

  // resize  event handlers;
  splitter.bind('resize', function(e, size) {
    if (e.target != this) return;
    splitTo(splitPos, false, true);
  });

  // This causes problems when having multiple splitters in the same window.
  // $(window).bind('resize', function() {
  //  splitTo(splitPos, false, true);
  // });

  //C.onmousedown=startDrag
  function startDrag(e) {
    if (e.target != this) return;

    _ghost = _ghost || C.clone(false).insertAfter(A);
    splitter._initPos = C.position();
    splitter._initPos[opts.moving] -= C[opts.sizing]();

    _ghost.addClass(opts.ghostClass)
        .css('position', 'absolute')
        .css('z-index', '250')
        .css('-webkit-user-select', 'none')
        .width(C.width()).height(C.height())
        .css(opts.moving, splitter._initPos[opts.moving]);

    // Add a "masking" div to prevent iframes from stealing drag events.
    if (A.find('IFRAME').length > 0 || B.find('IFRAME').length > 0) {
      var mask = $('<div class="splitterMask"></div>').insertAfter(_ghost);
      mask.css('position', 'absolute')
          .css('z-index', '20000')
          .css('width', '100%')
          .css('height', '100%')
          .css('overflow', 'hidden');
    }

    // Safari selects A/B text on a move
    mychilds.css('-webkit-user-select', 'none');

    A._posSplit = e[opts.eventPos];

    $(document)
        .bind('mousemove', performDrag)
        .bind('mouseup', endDrag);
  }


  //document.onmousemove=performDrag
  function performDrag(e) {
    if (!_ghost || !A) return;

    var incr = e[opts.eventPos] - A._posSplit;
    var new_position = splitter._initPos[opts.moving] + incr;
    var max_position = B.position()[opts.moving] + B[opts.sizing]();

    if(new_position > max_position) new_position = max_position;

    _ghost.css(opts.moving, new_position);
  }

  //C.onmouseup=endDrag
  function endDrag(e) {
    var p = _ghost.offset();
    $('div.splitterMask').remove();
    _ghost.remove();
    _ghost = null;

    // let Safari select text again
    mychilds.css('-webkit-user-select', 'text');

    $(document)
        .unbind('mousemove', performDrag)
        .unbind('mouseup', endDrag);

    var perc = (((p[opts.moving] - splitter.offset()[opts.moving]) /
        splitter[opts.sizing]()) * 100).toFixed(1);

    splitTo(perc, (splitter._initPos[opts.moving] > p[opts.moving]), true);
    splitter._initPos = 0;
  }

  //Perform actual splitting and animate it;
  function splitTo(perc, reversedorder, fast) {
    //generally MSIE problem
    if (_ismovingNow || perc == undefined) return;
    _ismovingNow = true;

    //do not save accidental events
    if (splitPos && splitPos > 10 && splitPos < 90)
      _splitPos = splitPos;
    splitPos = perc;

    var barsize = C[opts.sizing]() + (2 * parseInt(
        C.css('border-' + opts.moving + '-width'))); //+ border. cehap&dirty
    var splitsize = splitter[opts.sizing]();
    var percpx = 0;

    if (opts.closeableto != perc) {
      percpx = Math.max(parseInt((splitsize / 100) * perc), opts.minAsize);

      if (opts.maxAsize)percpx = Math.min(percpx, opts.maxAsize);

    } else {
      percpx = parseInt((splitsize / 100) * perc, 0);
    }

    if (opts.maxBsize) {
      if ((splitsize - percpx) > opts.maxBsize)
        percpx = splitsize - opts.maxBsize;
    }
    if (opts.minBsize) {
      if ((splitsize - percpx) < opts.minBsize)
        percpx = splitsize - opts.minBsize;
    }

    var sizeA = Math.max(0, (percpx - barsize));
    var sizeB = Math.max(0, (splitsize - sizeA - barsize));

    if (fast) {
      A.show().css(opts.sizing, sizeA + 'px');
      B.show().css(opts.sizing, sizeB + 'px');

      Bt.show();

      if (!$.browser.msie) {
        mychilds.trigger('resize');
        if (slave) slave.trigger('resize');
      }

      _ismovingNow = false;

      return;
    }

    //reduces flickering if total percentage becomes more than 100
    //(possible while animating)
    if (reversedorder) {
      var anob = {};
      anob[opts.sizing] = sizeA + 'px';
      A.show()
        .animate(anob, opts.animSpeed, function() {
            Bt.fadeIn('fast');

            if ($(this)[opts.sizing]() < 2) {
              this.style.display = 'none';
              B.stop(true, true);
              B[opts.sizing](splitsize + 'px');
            }}
        );

      var anob2 = {};
      anob2[opts.sizing] = sizeB + 'px';

      B.show()
        .animate(anob2, opts.animSpeed, function() {
            Bt.fadeIn('fast');

            if ($(this)[opts.sizing]() < 2) {
              this.style.display = 'none';
              A.stop(true, true);
              A[opts.sizing](splitsize + 'px');
            }
         });

      } else {
        var anob = {};

        anob[opts.sizing] = sizeB + 'px';
        B.show()
          .animate(anob, opts.animSpeed, function() {
              Bt.fadeIn('fast');
              if ($(this)[opts.sizing]() < 2) {
                this.style.display = 'none';
                A.stop(true, true);
                A[opts.sizing](splitsize + 'px');
              }
          });

        anob[opts.sizing] = sizeA + 'px';
        A.show()
            .animate(anob, opts.animSpeed, function() {
              Bt.fadeIn('fast');
              if ($(this)[opts.sizing]() < 2) {
                this.style.display = 'none';
                B.stop(true, true);
                B[opts.sizing](splitsize + 'px');}
              });
    }
    //trigger resize evt
    splitter.queue(function() {
      setTimeout(function() {
        splitter.dequeue();
        _ismovingNow = false;
        mychilds.trigger('resize');if (slave)slave.trigger('resize');
      }, opts.animSpeed + 5);
    });
  }; //end splitTo()
}
