
function create_new_paper()
{
    var paper = g_v_labelpaper.clone();
    g_v_body.append(paper);
    paper.find('.le_elem').click(edit_elem);
    return paper;
}

function find_new_label()
{
    var paper = g_v_body.children('.labelpaper:last');
    if (!paper.length) paper = create_new_paper();
    
    var label = paper.children('.label_active:last');
    if(label.length) {
        label = label.next();
        if(!label.length) {
            paper = create_new_paper();
            label = paper.children('div:first');
        }
    } else
        label = paper.children('div:first');
    
    return label;
}

function add_label(item)
{
    var label = find_new_label();
    label.addClass('label_active');
    fill_label(label, item);
    g_v_body.scrollTop( label.offset().top );
}

function fill_label(label, item)
{
    _fill_label(label, setup_data(item));
}

function text_to_html(v)
{
    v = v + '';
    g_v_escape.empty();
    var s = 0, e = 0, m = v.length, c;
    while(e < m) {
        c = v[e];
        if(c === '\n' || c === ' ') {
            g_v_escape.append( document.createTextNode(v.substring(s, e)) );
            if (c === '\n') g_v_escape.append('<br>');
            else if (c === ' ') g_v_escape.append('&nbsp;<wbr>');
            s = e + 1;
        }
        e++;
    }
    if(s < e) g_v_escape.append( document.createTextNode(v.substring(s, e)) );
    return g_v_escape.html();
}

function html_to_text(elem)
{
    var a = elem.html().replace(/<br>/gi, '\n').replace(/&nbsp;<wbr>/gi, ' ');
    return g_v_escape.html(a).text();
}

function _fill_label(label, data)
{
    var lst = label.children('.le_elem');
    for(var i = 0; i < lst.length; i++) {
        var v = $(lst[i]);
        var a = text_to_html(data[i] || '');
        (v.hasClass('le_elem_multi') ? v.find('td') : v).html(a);
    }
}

function edit_elem()
{
    var elem = $(this);
    wrap_elem = elem.hasClass('le_elem_multi') ? g_v_le_multi : g_v_le_single;
    var js = wrap_elem.data('js');
    if(js.v !== undefined) return;
    
    js.v = elem;
    wrap_elem.val( html_to_text(js.type ? elem.find('td') : elem) );
    elem.append(wrap_elem);
    wrap_elem.width(elem.width()).height(elem.height());
    wrap_elem.focus();
    elem.hasClass('le_id') && wrap_elem.select();
}

function refresh_paper(label)
{
    var paper = label.parent();
    if(!paper.children('.label_active').length) paper.remove();
}

function change_elem()
{
    var wrap_elem = $(this);
    var js = wrap_elem.data('js');
    var elem = js.v;
    if(elem === undefined) return;
    js.v = undefined;
    
    var val = wrap_elem.detach().val();
    var c_elem = js.type ? elem.find('td') : elem;
    if(html_to_text(c_elem) === val) return;
    c_elem.html( text_to_html(val) );
    
    if(!elem.hasClass('le_id')) return;
    load_by_id(elem.parent(), val);
}

function load_by_id(label, id)
{
    label.removeClass('label_active');
    if(!id) {
        _fill_label(label, {});
        refresh_paper(label);
        return;
    }
    $.get('sync?fn=get_item', {'item_no':id}, function(js) {
        if(!js || !js.length) { refresh_paper(label); return; }
        label.addClass('label_active');
        fill_label(label, js);
    }, 'json').error(function() {
        refresh_paper(label);
    });
}


$(function() {

g_v_body = $('body');
g_v_labelpaper = $('.labelpaper').remove();
g_v_escape = $('<div></div>');

g_v_le_single = $('<input type="text" id="le_single" />').data('js', {'type':0}).click(function(evt) {
    evt.stopPropagation();
}).blur(change_elem);
g_v_le_multi = $('<textarea id="le_multi"></textarea>').data('js', {'type':1}).click(function(evt) {
    evt.stopPropagation();
}).blur(change_elem);


window.onbeforeunload = function(e) {
    if(g_v_body.find('.label_active').length) return "Leave?";
    return undefined;
}

});

