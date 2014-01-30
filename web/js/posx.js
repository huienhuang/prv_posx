//2013-06-26


var __g_v_msgbox = null;

function MsgBox(title, msg, msg_type, cb) {
    if (!__g_v_msgbox) {
        __g_v_msgbox = $('<div id="__dlg_msgbox"></div>')
        .appendTo($('body'))
        .dialog({
            modal:true,
            autoOpen:false,
            width:700,
            close: function(event, ui) {
                var d = $(this).data('dlg_data');
                if (!d || d.cb === undefined) return;
                var cb = d.cb;
                if (cb.type === 0) cb.func.apply(cb.this || window, cb.args || []);
                if (cb.type === 1) window.location = '?';
                if (cb.type === 2) window.close();
                $(this).data('dlg_data', null);
            }
        });
    }
    __g_v_msgbox.data('dlg_data', {'cb': cb});
    if(msg_type)
        __g_v_msgbox.html(msg).dialog('option', 'title', title).dialog('open');
    else
        __g_v_msgbox.empty().append($('<pre></pre>').text(msg)).dialog('option', 'title', title).dialog('open');
}


function go_home() {
    var pn = window.location.pathname;
    var idx = pn.lastIndexOf('/');
    if (idx < 0) return;
    window.location = pn.substring(0, idx) + '/home';
}

function str_pad(s, n, f)
{
    f = f[0];
    for(var i = ('' + s).length; i < n; i++) s = f + s;
    return s;
}

function fmt_time(ts)
{
    var t = new Date();
    t.setTime(ts * 1000);
    
    var month = t.getMonth() + 1
    var day = t.getDate();
    var year = t.getFullYear();
    
    var hour = t.getHours();
    var minute = t.getMinutes();
    var second = t.getSeconds();
    
    var n = 'AM';
    if(hour >= 12) {
        hour -= 12;
        n = 'PM';
    }
    if(hour == 0) hour = 12;
    
    return str_pad(month, 2, '0') + '/' + str_pad(day, 2, '0') + '/' + year
            + ' ' + str_pad(hour, 2, '0') + ':' + str_pad(minute, 2, '0') + ':' + str_pad(second, 2, '0') + n;
}

