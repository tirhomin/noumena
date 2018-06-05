risklevel = 'low'
mode = 'keyword'
riskcolors = {"low":'yellow', 'medium':'orange', 'high':'red'}
kwgroupcolors = {'1':'f0f','2':'f80','3':'ff0',
                  '4':'0df','5':'000','6':'000','7':'0f0'}
function setcorpuscolorfromkw(){
  for (i = 1; i <= 7; i++) {
    $(".group"+i).each(function(index) {
      $(this).css('background-color',kwgroupcolors[i.toString()])
    });
  }
}

function LeftHeight(){
    var toolheight = $("#toolbar").height() + parseInt($("body").css('font-size'));
    var sheight = $(window).innerHeight();
    var leftheightmax = sheight - toolheight;
    $('#lefttoolbar').css('height',leftheightmax);
}

$(document).ready(function(){
    //progress bar logic
    var fback_clicked_names = new Array();
    var progress_percent = 0;
    $('.fback').click(function(e) {
      console.log(e.target.name); 
      if($.inArray(e.target.name,fback_clicked_names)==-1){
          progress_percent += 5.263;
          $('#progressbar').css('width',progress_percent.toString()+'%');
          fback_clicked_names.push(e.target.name)
      }
      if(progress_percent>99){$('#progressbar').css('background-color','#0D0');}
    });
    //end progress bar logic

    $('#openvideo').click(function(){
      console.log('starting video');
      $("#video1")[0].play();
      $.get("/viewedvideo", function( data ) {
        //do nothing
      });
    })

    $('.color').click(function(){
        var word = $(this).find('.word').text();
        var definition = $(this).find('.definition').text();
        $('#dictionary').show();
        $('#dictword').text(word);
        $('#dictdef').text(definition);
    });
    $('#dictx').click(function(){$('#dictionary').hide();});
    $('#content').css('margin-top',$('#toolbar').height());
    LeftHeight();
    $(window).on('resize', function(){LeftHeight();});

    var contentwidth = $("#content").width();
    /*
    $('#lefttoolbar').css('width',contentwidth*.35 - 6);
    $('#corpus').css('width',contentwidth*.62);
    */
    $('#corpusfile').change(function(){
      var filename = $('#corpusfile').val().split('\\').pop();
      $("#corpusfilename").text(filename);
    })
    //TODO merge these into one function for css class
    $('#keywordfile').change(function(){
      var filename = $('#keywordfile').val().split('\\').pop();
      $("#keywordfilename").text(filename);
    })
    /*
    //--- set left toolbar position if user is already scrolled
    var ctop = $('#corpus').offset().top;
    var sctop = $(document).scrollTop();
    if(sctop>ctop){sctop-=ctop}
    console.log(ctop,sctop);
    $('#lefttoolbar').css('margin-top',sctop)
    */
    // --- set keyword colordict for js to use when a user changes colors options later
    var scrollto = $('#scrollpos').val();
    window.scroll(0,scrollto);
    console.log('scrollto:',scrollto);

    var scrollchecker = setInterval(function() {
      var newscrollto = $('#scrollpos').val();
      if (newscrollto != scrollto ){
        //user has scrolled
         scrollto = newscrollto;
         $.get("/updatescroll?scrollpos="+scrollto, function( data ) {
           //do nothing
         });
       }
    }, 2000);


    for (i = 1; i <= 7; i++) {
      $(".group"+i).each(function(index) {
        var color = $('#color'+i).val();
        $(this).css('background-color',color)
        kwgroupcolors[i.toString()] = color;
      });
    }
    console.log(kwgroupcolors);

    // --- keep toolbar stuck to top when scrolling

    $(function() {
      $(window).scroll(function(){
        var sctop = $(document).scrollTop();
        $('#scrollpos').val(sctop);
      });
    });
    // ------ when user changes a color box:
    $(".custom").spectrum({
        change: function(color) {
            //---risklevel color
            color= color.toHexString().slice(1);
            if($(this).attr('id')=='riskcolor'){
                console.log('ITS An RCOLOR')
                riskcolors[risklevel] = color
                $(".color").each(function(index) {$(this).css('background-color','#'+riskcolors[risklevel]);});
                $.get( "/settings?risk="+risklevel+'&color='+riskcolors[risklevel]+"&mode="+mode, function( data ) {
                  $(".result").html(data);
                });
              }
            //------keyword colors:
            if($(this).attr('class')=='custom kwcolor'){
              //$(this).parent().
              console.log('kcl')
              var group = $(this).attr('id').slice(5);
              console.log('group'+group)
              $(".group"+group).each(function(index) {$(this).css('background-color','#'+color)});
              var urlstr = "/settings/kwcolor?colorid="+group+"&color="+color
              $.get( urlstr, function( data ) {
                $(".result").html(data);
              });

              kwgroupcolors[group] = color;
              mode = 'keyword';
              $('#modechoice').val(mode).change();
              setcorpuscolorfromkw();
            }
        }
    });

    // ----- when user changes modes:
    $('#modechoice').on('change', function (e) {
      mode = $(this).val()
      $.get( "/settings?mode="+$(this).val()+"&risk="+risklevel+"&color="+riskcolors[risklevel], function( data ) {
        $( ".result" ).html( data );
      });

      if ($(this).val() == 'keyword'){
        setcorpuscolorfromkw();
      }
      else {
        $(".color").each(function(index) {$(this).css('background-color','#'+riskcolors[risklevel]);});
      }

    });

    // --- when user changes risk levels
    $('#riskchoice').on('change', function (e) {
        //mode = 'profile';
        //$('#modechoice').val(mode).change();
        risklevel = this.value;
        $("#riskcolor").spectrum('set','#'+riskcolors[risklevel]);
        $.get( "/settings?risk="+risklevel+'&color='+riskcolors[risklevel], function( data ) {
          $( ".result" ).html( data );


          if(mode=='profile'){
            $(".color").each(function(index) {$(this).css('background-color','#'+riskcolors[risklevel]);});
          }

        });
    });

    // -- misc
    riskcolors['low'] = $('#low').val();
    riskcolors['medium'] = $('#medium').val();
    riskcolors['high'] = $('#high').val();
    risklevel = $('#risk').val();
    $("#riskcolor").spectrum('set','#'+riskcolors[risklevel]);
    mode = $('#mode').val();
    if(mode=='profile'){
      $(".color").each(function(index) {$(this).css('background-color','#'+riskcolors[risklevel]);});
    }


    // --- when user changes risk levels
    $('.pcbox').on('click', function (e) {
        var checkedboxes = '';
        $(".pcbox").each(function(index) {
            if($(this).prop('checked')){
                checkedboxes+= $(this).attr('name').slice(5) + ',';  
            }
        });
        console.log('checked boxes: '+checkedboxes)
        $.get( "/settings/cbox?b="+checkedboxes, function( data ) {
            1+1; //do nothing.
        });
    });



    console.log('risklevel',risklevel)
    console.log('mode',mode)
    console.log('riskcolor',riskcolors[risklevel])



});/*end document ready*/
