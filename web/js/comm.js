var g_v_data_date = null;
var g_v_data_user = null;
var g_v_data_cont = null;
var g_v_recnum_srch = null;
var g_ul = null;
var g_last_recnum = null;

function load_user(uid)
{
	g_v_data_user.val(uid).change()
	return false;
}

function render_main_stat()
{
	var ul = g_ul;
	var opts = '<option value="0"> - Select User - </option>';
	var tbl = '<table class="pxm_tbl"><tr><th>clerk</th><th>total</th><th>other_total</th><th>acct_total</th><th>acct_recv_pending</th><th>acct_ret_pending</th><th>acct_recv</th><th>acct_ret</th><th>acct_recv_prev</th><th>acct_ret_prev</th><th>estimated_total</th></tr>';
	for(var i = 0; i < ul.length; i++) {
		var u = ul[i];
		opts += '<option value="'+(i+1)+'">'+u[0]+'</option>';
			
		var et = u[2] + u[6] + u[7] + u[8] + u[9];
		tbl += '<tr'+(i%2?'':' class="alt"')+' onclick="return load_user('+(i+1)+')"><td>'+u[0]+'</td><td>'+u[1].toFixed(2)+'</td><td>'+u[2].toFixed(2)+'</td><td>'+u[3].toFixed(2)+'</td><td>'+u[4].toFixed(2)+'</td><td>'+u[5].toFixed(2)+'</td><td>'+u[6].toFixed(2)+'</td><td>'+u[7].toFixed(2)+'</td><td>'+u[8].toFixed(2)+'</td><td>'+u[9].toFixed(2)+'</td><td>'+et.toFixed(2)+'</td></tr>';
			
	}
	tbl += '</table>';
	
	
	g_v_data_user.html(opts).show();
	g_v_data_cont.html(tbl);
}

function data_date_change_cb(d)
{
	if(d && d.date && d.userlist && d.date == g_v_data_date.val()) {
		g_ul = d.userlist;
		render_main_stat();
		if(d.err) g_v_data_cont.append( $('<pre class="errlog"></pre>').text(d.err) );
	}
}

function data_date_change()
{
	var t = g_v_data_date.val();
	g_ul = null;
	g_v_data_cont.html('');
	g_v_data_user.html('').hide();
	g_v_recnum_srch.val('').hide();
	
	if(t) $.get('', {fn: 'cr', 'date': t}, data_date_change_cb, 'json');
	
}

function data_user_change()
{
	g_v_data_cont.html('');
	
	var pos = parseInt(g_v_data_user.val());
	if(!g_ul) return;
	if(!pos) {g_v_recnum_srch.hide(); render_main_stat(); return;}
	if(!(pos > 0 && pos <= g_ul.length)) return;
	
	var u = g_ul[pos-1];
	var tbl = '<table class="pxm_tbl"><tr><th>clerk</th><th>total</th><th>other_total</th><th>acct_total</th><th>acct_recv_pending</th><th>acct_ret_pending</th><th>acct_recv</th><th>acct_ret</th><th>acct_recv_prev</th><th>acct_ret_prev</th><th>estimated_total</th></tr>';
	var et = u[2] + u[6] + u[7] + u[8] + u[9];
	tbl += '<tr'+(i%2?'':' class="alt"')+'><td>'+u[0]+'</td><td>'+u[1].toFixed(2)+'</td><td>'+u[2].toFixed(2)+'</td><td>'+u[3].toFixed(2)+'</td><td>'+u[4].toFixed(2)+'</td><td>'+u[5].toFixed(2)+'</td><td>'+u[6].toFixed(2)+'</td><td>'+u[7].toFixed(2)+'</td><td>'+u[8].toFixed(2)+'</td><td>'+u[9].toFixed(2)+'</td><td>'+et.toFixed(2)+'</td></tr>';
	tbl += '</table>';
		
	tbl += '<table class="pxm_tbl"><tr><th>receipt_num</th><th>total</th><th>account</th><th>clerk</th><th>recved</th><th>qb_invoice_date</th><th>qb_docnum</th><th>customer</th><th>date</th></tr>';
		
	var i;
	var r;
		
	r = u[10];
	for(i = 0; i < r.length; i++) {
		var m = r[i];
		tbl += '<tr'+(i%2?'':' class="alt"')+'><td class="rec_'+m[0]+'">'+m[0]+'</td><td>'+m[1].toFixed(2)+'</td><td>'+m[2].toFixed(2)+'</td><td>'+m[3]+'</td><td>'+m[4]+'</td><td>'+(m[5]?m[5]:'')+'</td><td'+(m[6]?' class="rec_'+m[6]+'"':'')+'>'+(m[6]?m[6]:'')+'</td><td>'+m[9]+'</td><td>'+m[8]+'</td></tr>';
		}
	tbl += '</table>';
		
	tbl += '<table class="pxm_tbl"><tr><th>receipt_num</th><th>total</th><th>account</th><th>clerk</th><th>recved</th><th>qb_invoice_date</th><th>qb_docnum</th><th>customer</th><th>date</th></tr>';

	r = u[11];
	for(i = 0; i < r.length; i++) {
		var m = r[i];
		tbl += '<tr'+(i%2?'':' class="alt"')+'><td class="rec_'+m[0]+'">'+m[0]+'</td><td>'+m[1].toFixed(2)+'</td><td>'+m[2].toFixed(2)+'</td><td>'+m[3]+'</td><td>'+m[4]+'</td><td>'+(m[5]?m[5]:'')+'</td><td'+(m[6]?' class="rec_'+m[6]+'"':'')+'>'+(m[6]?m[6]:'')+'</td><td>'+m[9]+'</td><td>'+m[8]+'</td></tr>';
		}
	tbl += '</table>';
		
	g_v_data_cont.html(tbl);
	g_v_recnum_srch.show();
}

function recnum_search_keyup(event)
{
	if (event.which == '13' && !event.shiftKey) {
		if(g_last_recnum) {
			g_v_data_cont.find('.rec_' + g_last_recnum).removeClass('highlight');
			g_last_recnum = null;
		}
		
		var v = $(this).val();
		if( !v || !v.match(/^[0-9]+$/gi) ) return;
		
		var r = g_v_data_cont.find('.rec_' + v);
		if(r.length <= 0) return;
		
		g_last_recnum = v;
		var top = r.offset().top - g_v_data_cont.offset().top;
		$(document).scrollTop(top);
		r.addClass('highlight');
	}
}

$(function() {
	g_v_data_date = $('.data_date').change(data_date_change);
	g_v_data_user = $('.data_user').change(data_user_change);
	g_v_data_cont = $('.data_cont');
	g_v_recnum_srch = $('#recnum_search').keyup(recnum_search_keyup);
	
	$('.btn_home').button();
	
	g_v_data_date.change();
});



