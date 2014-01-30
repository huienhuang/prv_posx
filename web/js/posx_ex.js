function __itemsearch_render_item(ul, item)
{
    var d = item[3];
    
    var unit = d.units[d.default_uom_idx];
    var qty = unit[3] ? Math.floor(unit[3] != 1 ? d.qty[0] / unit[3] : d.qty[0]) : 'E';
    return $('<li class="srch_item"></li>').append(
        $('<a></a>')
            .append($('<span></span>').text(item[1]))
            .append($('<span></span>').text(d.units[0][1]))
            .append($('<span></span>').text( '$' + unit[0][0] + (unit[2] ? '/' + unit[2] : '') + ' (' + qty +')' ))
            .append($('<span></span>').text(item[2]))
    ).appendTo(ul);
    
}

function __ac_item_search_response(event, ui) {
    var ct = ui.content;
    var term = $.trim( $(this).data("ui-autocomplete").term.toLowerCase() );
        
    for(var i = 0; i < ct.length; i++) {
        var c = ct[i];
        var item = c[3] = $.parseJSON(c[3]);
        var units = item.units;
            
        if (c[4] !== null) {
            var upc_uom_idx = parseInt(c[4]);
            if(upc_uom_idx >= 0 && upc_uom_idx < units.length) item.default_uom_idx = upc_uom_idx;
                
        } else if(term) {
            for(var u = 0; u < units.length; u++) {
                var alu = units[u][1];
                if(alu && alu.toLowerCase() === term) {
                    item.default_uom_idx = u;
                    break;
                }
            }
        }
            
    }
}

function init_item_ac(sel, cb)
{
    var ac = $(sel).autocomplete({
        autoFocus: true,
        source: "sync?fn=itemsearch",
        minLength: 1,
        select: cb,
        response: __ac_item_search_response
    });
    ac.data("ui-autocomplete")._renderItem = __itemsearch_render_item;
    
    return ac;
}


