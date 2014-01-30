var g_v_hdr = null;
var g_v_action = null;
var g_v_users = null;
var g_v_user_sel = null;
var g_v_status_msg = null;
var g_us_timer = null;
var g_cur_uid = 0;
var g_cur_seq = 0;
var g_cur_user_data = null;
var g_v_admin_user_sel = null;
var g_v_admin_date_from = null;
var g_v_admin_date_to = null;
var g_v_admin_cmc_body = null;

function get_time_str(t)
{
    var h = t.getHours();
    var m = t.getMinutes();
    var s = t.getSeconds();
    
    var M = t.getMonth() + 1;
    var D = t.getDate();
    var Y = t.getFullYear();
    
    M = (M < 10 ? "0" : "") + M;
    D = (D < 10 ? "0" : "") + D;
    
    m = (m < 10 ? "0" : "") + m;
    s = (s < 10 ? "0" : "") + s;
    
    var p = h < 12 ? '\u4e0a\u5348' : '\u4e0b\u5348';
    
    if(h == 0)
        h = '12';
    else if(h > 12)
        h -= 12;
    
    h = (h < 10 ? "0" : "") + h;
    
    r = Y+'-'+M+'-'+D+' '+h+':'+m+':'+s+' '+p;
    
    return r;
}

function update_clock()
{
    var t = new Date();
    g_v_hdr.text("\u73b0\u5728\u65f6\u95f4"+': '+get_time_str(t));
}

function update_user_block()
{
    if(g_cur_user_data[0] == 1) {
        var t = new Date();
        t.setTime(g_cur_user_data[1] * 1000);
        var msg = '\u6b63\u5728\u4e0a\u73ed' + '<br/>' + '\u4ece ' + get_time_str(t) + ' \u5f00\u59cb';
        g_v_status_msg.html(msg);
        g_v_status_msg.show();
        
        g_v_action.text('\u4e0b\u73ed\u56de\u5bb6');
        g_v_action.addClass('cmc_action_out');
    } else {
        g_v_action.text('\u5f00\u59cb\u4e0a\u73ed');
        g_v_action.removeClass('cmc_action_out');
        g_v_status_msg.hide();
    }
    
    g_v_action.show();
}

function load_user_state_cb(d)
{
    if(d && d.res && (d.seq == g_cur_seq || d.seq > g_cur_seq && d.nzs) ) {
        var ud = d.res;
        var un = d.nzs;
        
        if(d.seq > g_cur_seq) {
            g_cur_seq = d.seq;
            var uid = g_v_user_sel.val();
            g_v_user_sel.empty();
            g_v_user_sel.append( $('<option value="0">-- \u9009\u62e9\u4f60\u7684\u540d\u5b57 --</option>') );
            for(var i = 0; i < un.length; i++) {
                var n = un[i];
                var v = ud[ '' + n[0] ];
                g_v_user_sel.append( $('<option value="'+n[0]+'" class="cmc_user_s'+v[0]+'"></option>').text(n[1]) );
            }
            
            if(uid && ud[uid]) g_v_user_sel.val(uid);
            g_v_users = g_v_user_sel.find('option');
            
        } else if(g_v_users) {
            for(var i = 1; i < g_v_users.length; i++) {
                var o = $(g_v_users[i]);
                var k = o.val();
                if(ud[k] == undefined) continue;
                var v = ud[k];
                var cls = 'cmc_user_s' + v[0];
                if( !o.hasClass(cls) ) {
                    o.removeClass().addClass(cls);
                    o.text(o.text());
                }
            }
            
        }
        
        if(g_cur_uid) {
            var v = ud['' + g_cur_uid];
            if(v) {
                if(!g_cur_user_data || g_cur_user_data[0] != v[0] || g_cur_user_data[1] != v[1]) {
                    g_cur_user_data = [ v[0], v[1] ];
                    update_user_block();
                }
            } else {
                g_v_user_sel.val('').change();
            }
            
        }
        
    }
    
    if(g_us_timer) { window.clearTimeout(g_us_timer); g_us_timer = null; }
    g_us_timer = window.setTimeout("load_user_state()", 3000);
}

function load_user_state()
{
    if(g_us_timer) { window.clearTimeout(g_us_timer); g_us_timer = null; }
    $.get('?fn=getstate', {seq: g_cur_seq}, load_user_state_cb, 'json').error(delay_load_user_state);
}

function delay_load_user_state()
{
    if(g_us_timer) { window.clearTimeout(g_us_timer); g_us_timer = null; }
    g_us_timer = window.setTimeout("load_user_state()", 5000);
}

function cmc_user_change()
{
    var uid = parseInt($(this).val());
    if(!uid) uid = 0;
    g_cur_uid = uid;
    g_cur_user_data = null;
    g_v_status_msg.hide();
    g_v_action.hide();
    if(!uid) return;
    load_user_state();
}

function cmc_action_cb(d)
{
    g_v_user_sel.val('').change();
    load_user_state();
    
    if(d && d.res) {
        g_v_status_msg.text('\u63d0\u4ea4\u6210\u529f');
    } else {
        g_v_status_msg.text('\u53d1\u751f\u9519\u8bef');
    }
    
    g_v_status_msg.show();
}

function cmc_action_click()
{
    if(!g_cur_uid) return false;
    
    g_v_action.hide();
    $.get('?fn=setstate&uid=' + g_cur_uid+ '&out=' + (g_cur_user_data[0] == 1 ? 1 : 0), cmc_action_cb, 'json');
    
    return false;
}

function user_time_list_click(uid)
{
    g_v_admin_user_sel.val(uid).change();
    return false;
}

function get_user_time_list_cb(d)
{
    if(!d || !d.res) return;
    
    var a = d.res;
    var t = new Date();
    var s = '';
    
    g_v_admin_cmc_body.empty();
    if(d.uid) {
        var s = '<table class="pxm_tbl"><tr><th>In Time</th><th>Out Time</th><th>Total Hours</th></tr>';
        var h = 0.0;
        for(var i = 0; i < a.length; i++) {
            var r = a[i];
            var p = 0.0;
            if(r[1]) p = (r[1] - r[0]) / 3600.0;
            h += p;
            t.setTime(r[0] * 1000);
            s += '<tr' + (i % 2 == 1 ? ' class="alt"' : '') + '><td>' + get_time_str(t);
            s += '</td><td>';
            if(r[1]) {
                t.setTime(r[1] * 1000);
                s += get_time_str(t);
            }
            s += '</td><td>' + p.toFixed(2) + '</td></tr>'
        }
        s += '<tr><td></td><td></td><td>' + h.toFixed(2) + '</td></tr></table>';
        g_v_admin_cmc_body.html(s);
        
    } else {
        var s = $('<table class="pxm_tbl"><tr><th>Id</th><th>Name</th><th>In</th><th>Out</th></tr></table>');
        for(var i = 0; i < a.length; i++) {
            var r = a[i];
            
            var t_in = '';
            if(r[2]) {
                t.setTime(r[2] * 1000);
                t_in = get_time_str(t);
            }
            
            var t_out = '';
            if(r[3]) {
                t.setTime(r[3] * 1000);
                t_out = get_time_str(t);
            }
            
            s.append( $('<tr onclick="return user_time_list_click(' + r[0] + ')"><td>' + r[0] + '</td></tr>')
                     .append( $('<td></td>').text(r[1]) )
                     .append( $('<td></td>').text(t_in) )
                     .append( $('<td></td>').text(t_out) )
                     
                     );
        }
        
        g_v_admin_cmc_body.append(s);
    }
    
}

function get_user_time_list(d, i)
{
    g_v_admin_cmc_body.empty();
    var uid = parseInt( g_v_admin_user_sel.val() );
    if(!uid) uid = 0;
    
    var fts = g_v_admin_date_from.datepicker("getDate").getTime() / 1000;
    var tts = g_v_admin_date_to.datepicker("getDate").getTime() / 1000 + 86400;
    if(fts >= tts) return;
    
    $.get('?fn=timelist', {uid:uid, fts:fts, tts:tts}, get_user_time_list_cb, 'json');
}


