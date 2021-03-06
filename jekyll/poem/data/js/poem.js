// the translate button
gmodel="";
gtopic="";
previous_topic="";
previous_id=-1;
previous_nline = -1;
previous_lang = -1;

function to_disable_adjust(){
    var nline = $("input[name=nline]:checked").val();
    var lang = $("input[name=model]:checked").val();
    if ((nline != previous_nline) || (lang != previous_lang)){
	$("#adjust-button").prop('disabled',true);
    } else {
	$("#adjust-button").prop('disabled',false);
    }
    if (lang == 1){
	$("#adjust-button").prop('disabled',true);
    }
}

function onselect_language(n){
    // n = 1 English
    // n = 2 Spanish
    to_disable_adjust()
    if (n == 2){
	$("input[name=nline][value=14]").prop("checked",true);
	$("input[name=nline][value!=14]").parent().css('color','lightgrey');
	$("input[name=nline]").prop("disabled",true);

	$("input[name=genre][value=lyrical]").prop("checked",true);
	$("input[name=genre][value!=lyrical]").parent().css('color','lightgrey');
	$("input[name=genre]").prop("disabled",true);

	$("input[name=meter][value=iambic]").prop("checked",true);
	$("input[name=meter][value!=iambic]").parent().css('color','lightgrey');
	$("input[name=meter]").prop("disabled",true);
	
	$("input[name=format][value=ss]").prop("checked",true);
	$("input[name=format][value!=ss]").parent().css('color','lightgrey');
	$("input[name=format]").prop("disabled",true);

	$("input[name=encourage_words]").prop("disabled",true);
	$("input[name=disencourage_words]").prop("disabled",true);
	
	$("#enc").slider().slider("disable");
	$("#cwords").slider().slider("disable");
	$("#reps").slider().slider("disable");
	$("#allit").slider().slider("disable");
	$("#slant").slider().slider("disable");
	$("#wordlen").slider().slider("disable");
	$("#enc_weight").prop('disabled',true);
	$("#cword_weight").prop('disabled',true);
	$("#reps_weight").prop('disabled',true);
	$("#allit_weight").prop('disabled',true);
	$("#slant_weight").prop('disabled',true);
	$("#wordlen_weight").prop('disabled',true);
		

    } else if (n == 1){
	$("input[name=nline]").prop("disabled",false);
	$("input[name=nline]").parent().css('color','black');

	$("input[name=genre][value=lyrical]").prop("checked",true);
	$("input[name=genre][value!=lyrical]").parent().css('color','lightgrey');
	$("input[name=genre]").prop("disabled",true);

	$("input[name=meter][value=iambic]").prop("checked",true);
	$("input[name=meter][value!=iambic]").parent().css('color','lightgrey');
	$("input[name=meter]").prop("disabled",true);
	
	$("input[name=format][value=ss]").prop("checked",true);
	$("input[name=format][value!=ss]").parent().css('color','lightgrey');
	$("input[name=format]").prop("disabled",true);

	$("input[name=encourage_words]").prop("disabled",false);
	$("input[name=disencourage_words]").prop("disabled",false);
	
	$("#enc").slider().slider("enable");	
	$("#cwords").slider().slider("enable");
	$("#reps").slider().slider("enable");
	$("#allit").slider().slider("enable");
	$("#slant").slider().slider("disable");
	$("#wordlen").slider().slider("enable");
	$("#enc_weight").prop('disabled',false);
	$("#cword_weight").prop('disabled',false);
	$("#reps_weight").prop('disabled',false);
	$("#allit_weight").prop('disabled',false);
	$("#slant_weight").prop('disabled',true);
	$("#wordlen_weight").prop('disabled',false);

	
    }
}


$('#adjust-button').click(function() {
    var btn = $(this);
    $("#translate-button").prop('disabled',true);
    btn.button('loading');
    $("#poem").html("");

    lang = previous_lang;
    nline = previous_nline;
    id = previous_id;
    
    //style
    var encourage_words = $('input[name=encourage_words]').val();
    var disencourage_words = $('input[name=disencourage_words]').val();
    var enc_weight = $('input[name=enc_weight]').val();
    var cword = $('input[name=cword_weight]').val();
    var reps = $('input[name=reps_weight]').val();
    var allit = $('input[name=allit_weight]').val();
    var slant = $('input[name=slant_weight]').val();
    var wordlen = $('input[name=wordlen_weight]').val();

    eng_data = {
	topic:"repeat",
	k:1,
	model:"0",
	id:id,
	nline:nline,
	encourage_words:encourage_words,
	disencourage_words:disencourage_words,
	enc_weight:enc_weight,
	cword:cword,
	reps:reps,
	allit:allit,
	slant:slant,
	wordlen:wordlen,
	no_fsa:1
    };

    data = eng_data;

    left_time = 16;

    if (nline == "2"){
	left_time = 4;
    } else if (nline == "4") {
	left_time = 6;
    }
    
    estimation = ""
    var timer = setInterval( function() {
	estimation = "["+left_time + "s] "
	$.ajax(
	    {
		url : "http://cage.isi.edu:"+port+"/api/poem_status",
		data: {id:id},
		type:"GET",
		xhrFields:{withCredentials:false},
		success: function (response_data) {
		    left_time = left_time - 2
		    $("#status").html(estimation + response_data);
		}
	    }
	);
    },2000)

    $.ajax({
	url: "http://cage.isi.edu:"+port+"/api/poem_check",
	data: data,
	type:"GET",
	xhrFields: {
	    // The 'xhrFields' property sets additional fields on the XMLHttpRequest.
	    // This can be used to set the 'withCredentials' property.
	    // Set the value to 'true' if you'd like to pass cookies to the server.
	    // If this is enabled, your server must respond with the header
	    // 'Access-Control-Allow-Credentials: true'.
	    withCredentials: false
	},
	success: function(response_data) {
	    $("#translate-button").prop('disabled',false);
	    jd = $.parseJSON(response_data);
	    $("#poem").html(jd.poem);
	    $("#status").html("Ready");
	}
    }).always(function (){
	$("#translate-button").prop('disabled',false);
	btn.button('reset');
	clearInterval(timer);
    });

});


$('#translate-button').click(function() {
    var btn = $(this);
    $("#adjust-button").prop('disabled',true);
    btn.button('loading');
    $("#poem").html("");
    $("#config").html("");
    $("#rhyme-info").html("");
    $("#rhyme-words").html("");
    $("#pc").html("");
    $("#exact-rhyme-candidates").html("");
    $("#slant-rhyme-candidates").html("");

    var lang = $("input[name=model]:checked").val();

    var nline = $("input[name=nline]:checked").val();

    port = 8080;
    if (lang == 1){
	port = 8081;
    }

    var model = "0";
    var topic = $('#input-topic').val();
    topic = topic.replace(/ /g, "_");
    if (topic == ""){
	if (lang == 0){
	    topic = "civil_war";
	} else {
	    topic = "guerra_civil";
	}
    }

    id = Math.round(Math.random()*10000) + 1
    gmodel = model;
    gtopic = topic;






    //style
    var encourage_words = $('input[name=encourage_words]').val();
    var disencourage_words = $('input[name=disencourage_words]').val();
    var enc_weight = $('input[name=enc_weight]').val();
    var cword = $('input[name=cword_weight]').val();
    var reps = $('input[name=reps_weight]').val();
    var allit = $('input[name=allit_weight]').val();
    var slant = $('input[name=slant_weight]').val();
    var wordlen = $('input[name=wordlen_weight]').val();

    eng_data = {
	    topic:topic,
	    k:1,
	    model:model,
	    id:id,
	    nline:nline,
	    encourage_words:encourage_words,
	    disencourage_words:disencourage_words,
	    enc_weight:enc_weight,
	    cword:cword,
	    reps:reps,
	    allit:allit,
	    slant:slant,
	    wordlen:wordlen
	};
    spa_data = {
	    topic:topic,
	    k:1,
	    model:model,
	    id:id,
	    nline:nline,
	};
    data = eng_data;
    if (port ==1 ) // spanish
    {
	data = eng_data;
    }

    left_time = 40;
    if (lang == 1){
	left_time = 60;
    } else {
	if (nline == "2"){
	    left_time = 14;
	} else if (nline == "4") {
	    left_time = 18;
	}
    }
    estimation = ""
    var timer = setInterval( function() {
	estimation = "["+left_time + "s] "
	$.ajax(
	    {
		url : "http://cage.isi.edu:"+port+"/api/poem_status",
		data: {id:id},
		type:"GET",
		xhrFields:{withCredentials:false},
		success: function (response_data) {
		    left_time = left_time - 2
		    $("#status").html(estimation + response_data);
		}
	    }
	);
    },2000)

    $.ajax({
	url: "http://cage.isi.edu:"+port+"/api/poem_check",
	data: data,
	type:"GET",
	xhrFields: {
	    // The 'xhrFields' property sets additional fields on the XMLHttpRequest.
	    // This can be used to set the 'withCredentials' property.
	    // Set the value to 'true' if you'd like to pass cookies to the server.
	    // If this is enabled, your server must respond with the header
	    // 'Access-Control-Allow-Credentials: true'.
	    withCredentials: false
	},
	success: function(response_data) {
	    previous_id = id;
	    previous_nline = nline;
	    previous_lang = lang;
	    $("#adjust-button").prop('disabled',false);

	    jd = $.parseJSON(response_data);
	    $("#poem").html(jd.poem);
	    $("#config").html(jd.config);
	    $("#rhyme-info").html(jd.rhyme_info);
	    $("#rhyme-words").html(jd.rhyme_words);
	    $("#exact-rhyme-candidates").html(jd.exact_rhyme_candidates);
	    $("#slant-rhyme-candidates").html(jd.slant_rhyme_candidates);
	    $("#pc").html(jd.pc);
	    $("#status").html("Ready");
	}
    }).always(function (){
	btn.button('reset');
	clearInterval(timer);
    });


});

onselect_language(1);
