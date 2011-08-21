
/*******************************************************************************
 jquery.mb.components
 Copyright (c) 2001-2010. Matteo Bicocchi (Pupunzi); Open lab srl, Firenze - Italy
 email: mbicocchi@open-lab.com
 site: http://pupunzi.com

 Licences: MIT, GPL
 http://www.opensource.org/licenses/mit-license.php
 http://www.gnu.org/licenses/gpl.html
 ******************************************************************************/

(function(a){a.fn.hoverIntent=function(k,j){var l={sensitivity:7,interval:100,timeout:0};l=a.extend(l,j?{over:k,out:j}:k);var n,m,h,d;var e=function(f){n=f.pageX;m=f.pageY};var c=function(g,f){f.hoverIntent_t=clearTimeout(f.hoverIntent_t);if((Math.abs(h-n)+Math.abs(d-m))<l.sensitivity){a(f).unbind("mousemove",e);f.hoverIntent_s=1;return l.over.apply(f,[g])}else{h=n;d=m;f.hoverIntent_t=setTimeout(function(){c(g,f)},l.interval)}};var i=function(g,f){f.hoverIntent_t=clearTimeout(f.hoverIntent_t);f.hoverIntent_s=0;return l.out.apply(f,[g])};var b=function(q){var o=(q.type=="mouseover"?q.fromElement:q.toElement)||q.relatedTarget;while(o&&o!=this){try{o=o.parentNode}catch(q){o=this}}if(o==this){return false}var g=jQuery.extend({},q);var f=this;if(f.hoverIntent_t){f.hoverIntent_t=clearTimeout(f.hoverIntent_t)}if(q.type=="mouseover"){h=g.pageX;d=g.pageY;a(f).bind("mousemove",e);if(f.hoverIntent_s!=1){f.hoverIntent_t=setTimeout(function(){c(g,f)},l.interval)}}else{a(f).unbind("mousemove",e);if(f.hoverIntent_s==1){f.hoverIntent_t=setTimeout(function(){i(g,f)},l.timeout)}}};return this.mouseover(b).mouseout(b)}})(jQuery);
/*******************************************************************************
 jquery.mb.components
 Copyright (c) 2001-2010. Matteo Bicocchi (Pupunzi); Open lab srl, Firenze - Italy
 email: mbicocchi@open-lab.com
 site: http://pupunzi.com

 Licences: MIT, GPL
 http://www.opensource.org/licenses/mit-license.php
 http://www.gnu.org/licenses/gpl.html
 ******************************************************************************/

/**
 * Sets the type of metadata to use. Metadata is encoded in JSON, and each property
 * in the JSON will become a property of the element itself.
 *
 * There are three supported types of metadata storage:
 *
 *   attr:  Inside an attribute. The name parameter indicates *which* attribute.
 *          
 *   class: Inside the class attribute, wrapped in curly braces: { }
 *   
 *   elem:  Inside a child element (e.g. a script tag). The
 *          name parameter indicates *which* element.
 *          
 * The metadata for an element is loaded the first time the element is accessed via jQuery.
 *
 * As a result, you can define the metadata type, use $(expr) to load the metadata into the elements
 * matched by expr, then redefine the metadata type and run another $(expr) for other elements.
 * 
 * @name $.metadata.setType
 *
 * @example <p id="one" class="some_class {item_id: 1, item_label: 'Label'}">This is a p</p>
 * @before $.metadata.setType("class")
 * @after $("#one").metadata().item_id == 1; $("#one").metadata().item_label == "Label"
 * @desc Reads metadata from the class attribute
 * 
 * @example <p id="one" class="some_class" data="{item_id: 1, item_label: 'Label'}">This is a p</p>
 * @before $.metadata.setType("attr", "data")
 * @after $("#one").metadata().item_id == 1; $("#one").metadata().item_label == "Label"
 * @desc Reads metadata from a "data" attribute
 * 
 * @example <p id="one" class="some_class"><script>{item_id: 1, item_label: 'Label'}</script>This is a p</p>
 * @before $.metadata.setType("elem", "script")
 * @after $("#one").metadata().item_id == 1; $("#one").metadata().item_label == "Label"
 * @desc Reads metadata from a nested script element
 * 
 * @param String type The encoding type
 * @param String name The name of the attribute to be used to get metadata (optional)
 * @cat Plugins/Metadata
 * @descr Sets the type of encoding to be used when loading metadata for the first time
 * @type undefined
 * @see metadata()
 */

(function($) {

$.extend({
	metadata : {
		defaults : {
			type: 'class',
			name: 'metadata',
			cre: /({.*})/,
			single: 'metadata'
		},
		setType: function( type, name ){
			this.defaults.type = type;
			this.defaults.name = name;
		},
		get: function( elem, opts ){
			var settings = $.extend({},this.defaults,opts);
			// check for empty string in single property
			if ( !settings.single.length ) settings.single = 'metadata';
			
			var data = $.data(elem, settings.single);
			// returned cached data if it already exists
			if ( data ) return data;
			
			data = "{}";
			
			if ( settings.type == "class" ) {
				var m = settings.cre.exec( elem.className );
				if ( m )
					data = m[1];
			} else if ( settings.type == "elem" ) {
				if( !elem.getElementsByTagName )
					return undefined;
				var e = elem.getElementsByTagName(settings.name);
				if ( e.length )
					data = $.trim(e[0].innerHTML);
			} else if ( elem.getAttribute != undefined ) {
				var attr = elem.getAttribute( settings.name );
				if ( attr )
					data = attr;
			}
			
			if ( data.indexOf( '{' ) <0 )
			data = "{" + data + "}";
			
			data = eval("(" + data + ")");
			
			$.data( elem, settings.single, data );
			return data;
		}
	}
});

/**
 * Returns the metadata object for the first member of the jQuery object.
 *
 * @name metadata
 * @descr Returns element's metadata object
 * @param Object opts An object contianing settings to override the defaults
 * @type jQuery
 * @cat Plugins/Metadata
 */
$.fn.metadata = function( opts ){
	return $.metadata.get( this[0], opts );
};

})(jQuery);
/*******************************************************************************
 jquery.mb.components
 Copyright (c) 2001-2010. Matteo Bicocchi (Pupunzi); Open lab srl, Firenze - Italy
 email: mbicocchi@open-lab.com
 site: http://pupunzi.com

 Licences: MIT, GPL
 http://www.opensource.org/licenses/mit-license.php
 http://www.gnu.org/licenses/gpl.html
 ******************************************************************************/

/*
 * jQuery.mb.components: jquery.mb.flipV
 * version: 1.1
 * © 2001 - 2009 Matteo Bicocchi (pupunzi), Open Lab
 *
 */

(function($) {
  var isIE=$.browser.msie;
  jQuery.fn.encHTML = function() {
    return this.each(function(){
      var me   = $(this);
      var html = me.text();
      me.text(html.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g, escape("'")).replace(/"/g,escape('"')));
//      me.text(html.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g, "’").replace(/"/g,"“"));
    });
  };
  $.mbflipText= {
    author:"Matteo Bicocchi",
    version:"1.1",
    flipText:function(tb){
      var UTF8encoded=$("meta[http-equiv=Content-Type]").attr("content") && $("meta[http-equiv=Content-Type]").attr("content").indexOf("utf-8")>-1;
      return this.each(function(){
        var el= $(this);
        var h="";
        var w="";

        var label="";
        var bgcol=(el.css("background-color") && el.css("background-color") != "rgba(0, 0, 0, 0)") ? el.css("background-color"):"#fff";
        var fontsize= parseInt(el.css('font-size'))>0?parseInt(el.css('font-size')):14;
        var fontfamily=el.css('font-family')?el.css('font-family').replace(/\'/g, '').replace(/"/g,''):"Arial";
        var fontcolor=el.css('color')? el.css('color'):"#000";

        if ($.browser.msie){
          if(!tb) el.css({'writing-mode': 'tb-rl', height:h, filter: 'fliph() flipv("") ', whiteSpace:"nowrap", lineHeight:fontsize+2+"px"}).css('font-weight', 'normal');
          label=$("<span style='writing-mode: tb-rl; whiteSpace:nowrap; height:"+h+"; width:"+w+"; line-height:"+(fontsize+2)+"px'>"+el.html()+"</span>");
        }else{

          var dim=el.getFlipTextDim(false);

          h=dim[1];
          w=dim[0];
          if(!isIE ) el.encHTML();
          var txt= el.text();

          var rot="-90";
          var ta="end";
          var xFix=0;
          var yFix=$.browser.opera ? parseInt(w)-(parseInt(w)/4): $.browser.safari?5:0;
          if (tb){
            yFix=$.browser.opera?20:0;
            xFix= $.browser.safari?(fontsize/4):0;
            rot="90, "+((parseInt(w)/2)-xFix)+", "+parseInt(w)/2;
            ta="start";
          }
          var onClick= el.attr("onclick") || el.attr("href");
          var clickScript= onClick?"<div class='pointer' style='position:absolute;top:0;left:0;width:100%;height:100%;background:transparent'/>":"";

          label=$("<object class='flip_label' style='height:"+h+"px; width:"+w+"px;' type='image/svg+xml' data='data:image/svg+xml; charset=utf-8 ," +
                  "<svg xmlns=\"http://www.w3.org/2000/svg\">" +
                  "<rect x=\"0\" y=\"0\" width=\""+w+"px\" height=\""+h+"px\" fill=\""+bgcol+"\" stroke=\"none\"/>"+
                  "<text  x=\"-"+xFix+"\" y=\""+yFix+"\" font-family=\""+fontfamily+"\"  fill=\""+fontcolor+"\" font-size=\""+fontsize+"\"  style=\"text-anchor: "+ta+"; " +
                  "dominant-baseline: hanging\" transform=\"rotate("+rot+")\" text-rendering=\"optimizeSpeed\">"+txt+"</text></svg>'></object>" +
                  clickScript +
                  "");
        }
        var wrapper= onClick ? $("<div/>").css("position","relative"): $("");
        var cssPos= el.wrap(wrapper).css("position")!="absolute" || el.css("position")!="fixed"  ?"relative" : el.css("position");
        el.html(label).css({position:cssPos, width:w});
      });
    },
    getFlipTextDim:function(enc){
      var el= $(this);
//      if(!enc && !isIE) el.encHTML();
      var txt= el.html();
      var fontsize= parseInt(el.css('font-size'));
      var fontfamily=el.css('font-family').replace(/'/g, '').replace(/"/g,'');
      if (fontfamily==undefined) fontfamily="Arial";
      var placeHolder=$("<span/>").css({position:"absolute",top:-100, whiteSpace:"noWrap", fontSize:fontsize, fontFamily: fontfamily});
      placeHolder.text(txt);
      $("body").append(placeHolder);
      var h = (placeHolder.outerWidth()!=0?placeHolder.outerWidth():(16+txt.length*fontsize*.60));
      var w = (placeHolder.outerHeight()!=0?placeHolder.outerHeight()+5:50);
      placeHolder.remove();
      return [w,h];
    }
  };
  $.fn.mbFlipText=$.mbflipText.flipText;
  $.fn.getFlipTextDim=$.mbflipText.getFlipTextDim;

})(jQuery);
// javascript/jquery_mb_extruder/inc/mbExtruder.js
/*******************************************************************************
 jquery.mb.components
 Copyright (c) 2001-2010. Matteo Bicocchi (Pupunzi); Open lab srl, Firenze - Italy
 email: mbicocchi@open-lab.com
 site: http://pupunzi.com

 Licences: MIT, GPL
 http://www.opensource.org/licenses/mit-license.php
 http://www.gnu.org/licenses/gpl.html
 ******************************************************************************/

/*
 * Name:jquery.mb.extruder
 * Version: 2.1
 * dependencies: jquery.metadata.js, jquery.mb.flipText.js, jquery.hoverintent.js
 */


(function($) {
  document.extruder=new Object();
  document.extruder.left = 0;
  document.extruder.top = 0;
  document.extruder.bottom = 0;
  document.extruder.right = 0;
  document.extruder.idx=0;
  var isIE=$.browser.msie;

  $.mbExtruder= {
    author:"Matteo Bicocchi",
    version:"2.1",
    defaults:{
      width:350,
      positionFixed:true,
      sensibility:800,
      position:"top",
      accordionPanels:true,
      top:"auto",
      extruderOpacity:1,
      flapMargin:35,
      textOrientation:"bt", // or "tb" (top-bottom or bottom-top)
      onExtOpen:function(){},
      onExtContentLoad:function(){},
      onExtClose:function(){},
      hidePanelsOnClose:true,
      autoCloseTime:0,
      slideTimer:300
    },

    buildMbExtruder: function(options){
      return this.each (function (){
        this.options = {};
        $.extend (this.options, $.mbExtruder.defaults);
        $.extend (this.options, options);
        this.idx=document.extruder.idx;
        document.extruder.idx++;
        var extruder,extruderContent,wrapper,extruderStyle,wrapperStyle,txt,timer;
        extruder= $(this);
        extruderContent=extruder.html();

        extruder.css("zIndex",100);

        var isVertical = this.options.position=="left" || this.options.position=="right";

        var extW= isVertical?1: this.options.width;

        var c= $("<div/>").addClass("content").css({overflow:"hidden", width:extW});
        c.append(extruderContent);
        extruder.html(c);

        var position=this.options.positionFixed?"fixed":"absolute";
        extruder.addClass("extruder");
        extruder.addClass(this.options.position);
        var isHorizontal = this.options.position=="top" || this.options.position=="bottom";
        extruderStyle=
                this.options.position=="top"?
                {position:position,top:0,left:"50%",marginLeft:-this.options.width/2,width:this.options.width}:
                        this.options.position=="bottom"?
                        {position:position,bottom:0,left:"50%",marginLeft:-this.options.width/2,width:this.options.width}:
                                this.options.position=="left"?
                                {position:position,top:0,left:0,width:1}:
                                {position:position,top:0,right:0,width:1};
        extruder.css(extruderStyle);
        if(!isIE) extruder.css({opacity:this.options.extruderOpacity});
        extruder.wrapInner("<div class='ext_wrapper'></div>");
        wrapper= extruder.find(".ext_wrapper");

        wrapperStyle={position:"absolute", width:isVertical?1:this.options.width};
        wrapper.css(wrapperStyle);


        if (isHorizontal){
          this.options.position=="top"?document.extruder.top++:document.extruder.bottom++;
          if (document.extruder.top>1 || document.extruder.bottom>1){
            alert("more than 1 mb.extruder on top or bottom is not supported jet... hope soon!");
            return;
          }
        }

        if ($.metadata){
          $.metadata.setType("class");
          if (extruder.metadata().title) extruder.attr("extTitle",extruder.metadata().title);
          if (extruder.metadata().url) extruder.attr("extUrl",extruder.metadata().url);
          if (extruder.metadata().data) extruder.attr("extData",extruder.metadata().data);
        }
        var flapFooter=$("<div class='footer'/>");
        var flap=$("<div class='flap'><span class='flapLabel'/></div>");
        if (document.extruder.bottom){
          wrapper.prepend(flapFooter);
          wrapper.prepend(flap);
        }else{
          wrapper.append(flapFooter);
          wrapper.append(flap);
        }

        txt=extruder.attr("extTitle")?extruder.attr("extTitle"): "";
        var flapLabel = extruder.find(".flapLabel");
        flapLabel.text(txt);
        if(isVertical){
          flapLabel.html(txt).css({whiteSpace:"noWrap"});//,height:this.options.flapDim
          var orientation= this.options.textOrientation == "tb";
          var labelH=extruder.find('.flapLabel').getFlipTextDim()[1];
          extruder.find('.flapLabel').mbFlipText(orientation);
        }else{
          flapLabel.html(txt).css({whiteSpace:"noWrap"});
        }

        if (extruder.attr("extUrl")){
            extruder.setMbExtruderContent({
              url:extruder.attr("extUrl"),
              data:extruder.attr("extData"),
              callback: function(){
                if (extruder.get(0).options.onExtContentLoad) extruder.get(0).options.onExtContentLoad();
              }
          })
        }else{
          var container=$("<div>").addClass("text").css({width:extruder.get(0).options.width-20, height:extruder.height()-20, overflowY:"auto"});
          c.wrapInner(container);
          extruder.setExtruderVoicesAction();
        }

        flap.bind("click",function(){
          if (!extruder.attr("open")){
            extruder.openMbExtruder();
          }else{
            extruder.closeMbExtruder();
          }
        });

        c.bind("mouseleave", function(){
          $(document).one("click.extruder"+extruder.get(0).idx,function(){extruder.closeMbExtruder();});
          timer=setTimeout(function(){

            if(extruder.get(0).options.autoCloseTime > 0){
              extruder.closeMbExtruder();
            }
          },extruder.get(0).options.autoCloseTime);
        }).bind("mouseenter", function(){clearTimeout(timer); $(document).unbind("click.extruder"+extruder.get(0).idx);});

        if (isVertical){
          c.css({ height:"100%"});
          if(this.options.top=="auto") {
            flap.css({top:100+(this.options.position=="left"?document.extruder.left:document.extruder.right)});
            this.options.position=="left"?document.extruder.left+=labelH+this.options.flapMargin:document.extruder.right+= labelH+this.options.flapMargin;
          }else{
            flap.css({top:this.options.top});
          }
          var clicDiv=$("<div/>").css({position:"absolute",top:0,left:0,width:"100%",height:"100%",background:"transparent"});
          flap.append(clicDiv);
        }
      });
    },

    setMbExtruderContent: function(options){
      this.options = {
        url:false,
        data:"",
        callback:function(){}
      };
      $.extend (this.options, options);
      if (!this.options.url || this.options.url.length==0){
        alert("internal error: no URL to call");
        return;
      }
      var url=this.options.url;
      var data=this.options.data;
      var where=$(this), voice;
      var cb= this.options.callback;
      var container=$("<div>").addClass("container");
      if (!($.browser.msie && $.browser.version<=7))
        container.css({width:$(this).get(0).options.width});
      where.find(".content").wrapInner(container);
      $.ajax({
        type: "POST",
        url: url,
        data: data,
        success: function(html){
          where.find(".container").append(html);
          voice=where.find(".voice");
          voice.hover(function(){$(this).addClass("hover");},function(){$(this).removeClass("hover");});
          where.setExtruderVoicesAction();
          if (cb) {
            setTimeout(function(){cb();},100);
          }
        }
      });
    },

    openMbExtruder:function(c){
      var extruder= $(this);
      extruder.attr("open",true);
      $(document).unbind("click.extruder"+extruder.get(0).idx);
      var opt= extruder.get(0).options;
      extruder.addClass("open");
      if(!isIE) extruder.css("opacity",1);
      var position= opt.position;
      extruder.mb_bringToFront();
      if (position=="top" || position=="bottom"){
        extruder.find('.content').slideDown( opt.slideTimer);
        if(opt.onExtOpen) opt.onExtOpen();
      }else{

        if(!isIE) $(this).css("opacity",1);
        extruder.find('.ext_wrapper').css({width:""});
        extruder.find('.content').css({overflowX:"hidden", display:"block"});
        extruder.find('.content').animate({ width: opt.width}, opt.slideTimer);
        if(opt.onExtOpen) opt.onExtOpen();
      }
      if (c) {
        setTimeout(function(){
          $(document).one("click.extruder"+extruder.get(0).idx,function(){extruder.closeMbExtruder();});
        },100);
      }
    },

    closeMbExtruder:function(){
      var extruder= $(this);
      extruder.removeAttr("open");
      var opt= extruder.get(0).options;
      extruder.removeClass("open");
      $(document).unbind("click.extruder"+extruder.get(0).idx);
      if(!isIE) extruder.css("opacity",opt.extruderOpacity);
      if(opt.hidePanelsOnClose) extruder.hidePanelsOnClose();
      if (opt.position=="top" || opt.position=="bottom"){
        extruder.find('.content').slideUp(opt.slideTimer);
        if(opt.onExtClose) opt.onExtClose();
      }else if (opt.position=="left" || opt.position=="right"){
        extruder.find('.content').css({overflow:"hidden"});
        extruder.find('.content').animate({ width: 1 }, opt.slideTimer,function(){
          extruder.find('.ext_wrapper').css({width:1});
          extruder.find('.content').css({overflow:"hidden",display:"none"});
          if(opt.onExtClose) opt.onExtClose();
        });
      }
    }
  };

  jQuery.fn.mb_bringToFront= function(){
    var zi=10;
    $('*').each(function() {
      if($(this).css("position")=="absolute" ||$(this).css("position")=="fixed"){
        var cur = parseInt($(this).css('zIndex'));
        zi = cur > zi ? parseInt($(this).css('zIndex')) : zi;
      }
    });
    $(this).css('zIndex',zi+=1);
    return zi;
  };

  /*
   * EXTRUDER CONTENT
   */

  $.fn.setExtruderVoicesAction=function(){
    var extruder=$(this);
    var opt=extruder.get(0).options;
    var voices= $(this).find(".voice");
    voices.each(function(){
      var voice=$(this);
      if ($.metadata){
        $.metadata.setType("class");
        if (voice.metadata().panel) voice.attr("panel",voice.metadata().panel);
        if (voice.metadata().data) voice.attr("data",voice.metadata().data);
        if (voice.metadata().disabled) voice.attr("setDisabled", voice.metadata().disabled);
      }

      if (voice.attr("setDisabled"))
        voice.disableExtruderVoice();

      if (voice.attr("panel") && voice.attr("panel")!="false"){
        voice.append("<span class='settingsBtn'/>");
        voice.find(".settingsBtn").css({opacity:.5});
        voice.find(".settingsBtn").hover(
                function(){
                  $(this).css({opacity:1});
                },
                function(){
                  $(this).not(".sel").css({opacity:.5});
                }).click(function(){
          if ($(this).parents().hasClass("sel")){
            if(opt.accordionPanels)
              extruder.hidePanelsOnClose();
            else
              $(this).closePanel();
            return;
          }

          if(opt.accordionPanels){
            extruder.find(".optionsPanel").slideUp(400,function(){$(this).remove();});
            voices.removeClass("sel");
            voices.find(".settingsBtn").removeClass("sel").css({opacity:.5});
          }
          var content=$("<div class='optionsPanel'></div>");
          voice.after(content);
          $.ajax({
            type: "POST",
            url: voice.attr("panel"),
            data: voice.attr("data"),
            success: function(html){
              var c= $(html);
              content.html(c);
              content.children().not(".text")
                      .addClass("panelVoice")
                      .click(function(){
                extruder.closeMbExtruder();
              });
              content.slideDown(400);
            }
          });
          voice.addClass("sel");
          voice.find(".settingsBtn").addClass("sel").css({opacity:1});
        });
      }

      if (voice.find("a").length==0 && voice.attr("panel")){
        voice.find(".label").not(".disabled").css("cursor","pointer").click(function(){
          voice.find(".settingsBtn").click();
        });
      }

      if ((!voice.attr("panel") ||voice.attr("panel")=="false" ) && (!voice.attr("setDisabled") || voice.attr("setDisabled")!="true")){
        voice.find(".label").click(function(){
          extruder.hidePanelsOnClose();
          extruder.closeMbExtruder();
        });
      }
    });
  };

  $.fn.disableExtruderVoice=function(){
    var voice=$(this);
    var label = voice.find(".label");
    voice.removeClass("sel");
    voice.next(".optionsPanel").slideUp(400,function(){$(this).remove();});
    voice.attr("setDisabled",true);
    label.css("opacity",.4);
    voice.hover(function(){$(this).removeClass("hover");},function(){$(this).removeClass("hover");});
    label.addClass("disabled").css("cursor","default");
    voice.find(".settingsBtn").hide();
    voice.bind("click",function(event){
      event.stopPropagation();
      return false;
    });
  };

  $.fn.enableExtruderVoice=function(){
    var voice=$(this);
    voice.attr("setDisabled",false);
    voice.find(".label").css("opacity",1);
    voice.find(".label").removeClass("disabled").css("cursor","pointer");
    voice.unbind("click");
    voice.find(".settingsBtn").show();
  };

  $.fn.hidePanelsOnClose=function(){
    var voices= $(this).find(".voice");
    $(this).find(".optionsPanel").slideUp(400,function(){$(this).remove();});
    voices.removeClass("sel");
    voices.find(".settingsBtn").removeClass("sel").css("opacity",.5);
  };

  $.fn.openPanel=function(){
    var voice=$(this).hasClass("voice") ? $(this) : $(this).find(".voice");
    voice.each(function(){
      if($(this).hasClass("sel")) return;
      $(this).find(".settingsBtn").click();
    })
  };

  $.fn.closePanel=function(){
    var voice=$(this).hasClass("voice") ? $(this) : $(this).parent(".voice");
    voice.next(".optionsPanel").slideUp(400,function(){$(this).remove();});
    voice.removeClass("sel");
    $(this).removeClass("sel").css("opacity",.5);
  };

  $.fn.buildMbExtruder=$.mbExtruder.buildMbExtruder;
  $.fn.setMbExtruderContent=$.mbExtruder.setMbExtruderContent;
  $.fn.closeMbExtruder=$.mbExtruder.closeMbExtruder;
  $.fn.openMbExtruder=$.mbExtruder.openMbExtruder;

})(jQuery);
