var kmc_xmlhttp;

var activities = {};
var append_activities = 0;

// This is where the incoming responses are identifed and handled.
function kmc_process_type(type, aa)
{
    if (type == 'redirect') // redirect to another page
    {
      var where = aa['where'];
      where = where.replace(/\%26/g,'&');
      window.location.href = where;

    } else if (type == 'message') // display a message on the current page
    {
      var code = aa['code'];
      var text  = aa['text'];
      var where_html = document.getElementById('message');

      if (where_html != null)
      {
        where_html.innerHTML = text + ' ('+code+')';
      }

    } else if (type == 'class') // insert class date/time/etc details into a page, replacing existing details when required.
    {
      var id = aa['id'];
      var name  = decodeURI(aa['name']);
      var trainer = decodeURI(aa['trainer']);
      var notes = decodeURI(aa['notes']);
      var when = aa['when'];
      var siz = aa['size'];
      var max = aa['max'];
      var action = aa['action'];

      kmc_add_to_container('listcontainer', kmc_class_details(id, name, trainer, when, notes, siz, max, action));

    } else if (type == 'attendee') // insert details of a class attendee into a page, replacing existing details when required.
    {
      var id = aa['id'];
      var name  = decodeURI(aa['name']);
      var action  = decodeURI(aa['action']);

      kmc_add_to_container('listattendee', kmc_class_attendee(id, name, action));

    } else if (type == 'skill') // insert details of a users skill into the a page, replacing existing details when required.
    {
      var id = aa['id'];
      var name = decodeURI(aa['name']);
      var trainer = decodeURI(aa['trainer']);
      var gained = aa['gained'];
      var state = decodeURI(aa['state']);

      kmc_add_to_container('listcontainer', kmc_my_skill(id,name,trainer,gained,state));
    }
}


// a print print function for a date
function kmc_show_date(when)
{
    var d = new Date(when * 1000)

    return d.toDateString()
}

// a print print function for date and time.
function kmc_show_time(when)
{
    var d = new Date(when * 1000)

    return d.toGMTString()
}

// an pretty formatted html block for class date/time/etc  
function kmc_class_details(id, name, trainer, when, notes,size, max, action)
{
  if (notes)
  {
    notes += '<br>';
  } else
  {
    notes = '';
  }
  s = '<div class="row border mt-3"><div class="col-8"><h3>';
  s += name + ' (';

  if (action == 'leave')
  {
    s += 'You+'+(size-1)+'/'+max+')';
  } else
  {
    s += size+'/'+max+')';
  }

  s += '</h3>';
  s += '<div>Scheduled: ' + kmc_show_time(when) + '<br>Trainer: ' + trainer+'<br>'+notes+'</div>';
  s += '</div><div class="col-4 text-end">';

  if (action == 'join')
  {
    s += '<button type="submit" class="btn btn-primary btn-block" onclick="command_join_class('+id+');"><h3>&nbsp;Join&nbsp;</h3></button>';

  } else if(action == 'leave')
  {
    s += '<button type="submit" class="btn btn-primary btn-block" onclick="command_leave_class('+id+');"><h3>&nbsp;Leave&nbsp;</h3></button>';

  } else if(action == 'cancel')
  {
    s += '<button type="submit" class="btn btn-primary btn-block" onclick="command_cancel_class('+id+');"><h3>&nbsp;Cancel&nbsp;</h3></button>';

  } else if(action == 'edit')
  {
    s += '<button type="submit" class="btn btn-primary btn-block" onclick="window.location.href=\'/class/'+id+'\';");><h3>&nbsp;Edit&nbsp;</h3></button>';

  } else if(action == 'pending')
  {
    s += '<h3>Pending</h3>';

  } else if(action == 'cancelled')
  {
    s += '<h3>Cancelled</h3>';
  } else
  {
    s += '&nbsp;'
  }

  s += "</div></div>";

  e = document.createElement("div");
  e.innerHTML = s;
  e.id = 'c'+id;
  return e;
}

// an pretty formatted html block for class attendee  
function kmc_class_attendee(id, name, action)
{
  s = '<div class="row border mt-3"><div class="col-8"><h3>' + name + '</h3></div><div class="col-4 text-end">';

  if(action == 'remove')
  {
    s += '<button type="submit" class="btn btn-primary btn-block" onclick="command_update_attendee('+id+',\'remove\');"><h3>&nbsp;Remove&nbsp;</h3></button>';

  } else if(action == 'update')
  {
    s += '<button type="submit" class="btn btn-primary btn-block" onclick="command_update_attendee('+id+',\'pass\');"><h3>&nbsp;Pass&nbsp;</h3></button>';
    s += '<button type="submit" class="btn btn-primary btn-block" onclick="command_update_attendee('+id+',\'fail\');"><h3>&nbsp;Failed&nbsp;</h3></button>';
  } else if(action == 'passed')
  {
    s += '<h3>Passed</h3>';

  } else if(action == 'failed')
  {
    s += '<h3>Failed</h3>';

  } else
  {
    s += '<h3>Cancelled</h3>';
  }

  s += "</div></div>";

  e = document.createElement("div");
  e.innerHTML = s;
  e.id = 'a'+id;
  return e;
}


// an pretty formatted html block for skill  
function kmc_my_skill(id,name,trainer,gained,state)
{
  s  = '<div class="row border mt-3">';
  s += '<div class="col-8"><h3>' + name + '</h3>';


  if(state == 'trainer')
  {
    s += '<div>Gained: ' + kmc_show_date(gained) + '<br>Trainer: ' + trainer+'<br></div></div>';
    s += '<div class="col-4 text-end">';
    s += '<button type="submit" class="btn btn-primary btn-block" onclick="window.location.href=\'/create/'+id+'\';");><h3>&nbsp;Create Class&nbsp;</h3></button>';

  } else if(state == 'scheduled')
  {
    s += '<div>Scheduled: ' + kmc_show_date(gained) + '<br>Trainer: ' + trainer+'<br></div></div>';
    s += '<div class="col-4 text-end">';
    s += '<h3>Scheduled</h3>';
  } else if(state == 'pending')
  {
    s += '<div>Scheduled: ' + kmc_show_date(gained) + '<br>Trainer: ' + trainer+'<br></div></div>';
    s += '<div class="col-4 text-end">';
    s += '<h3>Pending</h3>';
  } else if(state == 'failed')
  {
    s += '<div>Scheduled: ' + kmc_show_date(gained) + '<br>Trainer: ' + trainer+'<br></div></div>';
    s += '<div class="col-4 text-end">';
    s += '<h3>Failed</h3>';
  } else if(state == 'passed')
  {
    s += '<div>Gained: ' + kmc_show_date(gained) + '<br>Trainer: ' + trainer+'<br></div></div>';
    s += '<div class="col-4 text-end">';
    s += '<h3>Passed</h3>';
  } else
  {
    s += '<div>Scheduled: ' + kmc_show_date(gained) + '<br>Trainer: ' + trainer+'<br></div></div>';
    s += '<div class="col-4 text-end">';
    s += '<h3>Err</h3>';
  }

  s += "</div></div>";

  e = document.createElement("div");
  e.innerHTML = s;
  e.id = 's'+id;
  return e;
}

function kmc_radio_value(radio)
{
  var rs = document.getElementsByName(radio);

  for (var i = 0, length = rs.length; i < length; i++)
  {
    if (rs[i].checked)
    {
      return rs[i].value;
    }
  }
  return '-1';
}

function kmc_response()
{
  var res;
  var aa;

  if (kmc_xmlhttp.readyState == 4)
  {
    res = kmc_xmlhttp.responseText;

    aa = JSON.parse(res)

    for(var i = 0, len = aa.length; i < len; i += 1)
    {
      var type = aa[i]['type'];
  
      kmc_process_type(type, aa[i]);
    }
  }
}

function kmc_send_post(where,what)
{
    kmc_xmlhttp = new XMLHttpRequest()
    kmc_xmlhttp.onreadystatechange=kmc_response;
    kmc_xmlhttp.open('POST',where,true);
    kmc_xmlhttp.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
    kmc_xmlhttp.send(what);
}

// action commands

function kmc_add_to_container(which, what)
{
  c = document.getElementById(what.id);
  if(c)
  {
    c.innerHTML=what.innerHTML;
  } else
  {
    container = document.getElementById(which);
    if (container)
    {
      container.appendChild(what);
    }
  }
}

encodeURIComponent

function kmc_fetch_class()
{
  id = window.location.href.split('/').pop();
  kmc_send_post('/action?command=get_class','{"id":'+id+'}');
}

function kmc_fetch_my_skills()
{
  kmc_send_post('/action?command=get_my_skills','');
}

function kmc_fetch_upcoming()
{
    kmc_send_post('/action?command=get_upcoming','');
}

function command_login()
{

    username = encodeURIComponent(document.getElementById('ofUser').value);
    password = encodeURIComponent(document.getElementById('ofPassword').value);

    kmc_send_post('/action?command=login','{"username":"'+username+'","password":"'+password+'"}');
}

function command_logout()
{
    kmc_send_post('/action?command=logout','');
}

function command_join_class(id)
{
    kmc_send_post('/action?command=join_class','{"id":'+id+'}');
}

function command_leave_class(id)
{
    kmc_send_post('/action?command=leave_class','{"id":'+id+'}');
}

function command_update_attendee(id, state)
{
    kmc_send_post('/action?command=update_attendee','{"id":'+id+',"state":"'+state+'"}');
}

function command_cancel_class(id)
{
    kmc_send_post('/action?command=cancel_class','{"id":'+id+'}');
}


function command_create_class()
{
  id = window.location.href.split('/').pop();
  day = encodeURIComponent(document.getElementById('ofDay').value);
  month = encodeURIComponent(document.getElementById('ofMonth').value);
  year = encodeURIComponent(document.getElementById('ofYear').value);
  hour = encodeURIComponent(document.getElementById('ofHour').value);
  minute = encodeURIComponent(document.getElementById('ofMinute').value);
  note = encodeURIComponent(document.getElementById('ofNote').value);
  max = encodeURIComponent(document.getElementById('ofMax').value);
  kmc_send_post('/action?command=create_class', '{"id":' + id + ',"day":' + day + ',"month":' + month + ',"year":' + year + ',"hour":' + hour + ',"minute":' + minute + ',"note":"' + note+ '", "max":' + max + '}');
}

