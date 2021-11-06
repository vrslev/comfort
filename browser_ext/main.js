var Safari = new Application("/Applications/Safari.app"); // eslint-disable-line no-undef

Safari.includeStandardAdditions = true;

function uneval(fn) {
  return `(${fn})()`;
}

function exec(fn) {
  return Safari.doJavaScript(uneval(fn), {
    in: Safari.windows[0].currentTab,
  });
}

function exit(message) {
  Safari.displayAlert(message);
  ObjC.import("stdlib"); // eslint-disable-line no-undef
  $.exit(0);
}

function get_customer_name() {
  return exec(
    () =>
      document.getElementsByClassName(
        "im-page--title-main-inner _im_page_peer_name"
      )[0].innerText
  );
}

function get_vk_url() {
  var url = exec(() => location.href);
  if (!(url && url.match("vk.com"))) {
    exit("Вы находитесь не на сайте VK");
  } else if (!url.match("vk.com/(im|gim)")) {
    exit("Вы находитесь не в диалогах VK");
  } else if (!url.match("sel=")) {
    exit("Вы находитесь не в диалоге VK");
  }
  return url;
}

function escape_html(text) {
  if (!text.match(/\w|\d/)) return "None";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function get_html() {
  function get_selected_html() {
    var sel = window.getSelection();
    if (sel.rangeCount) {
      var container = document.createElement("div");
      for (let i = 0; i < sel.rangeCount; i++) {
        container.appendChild(sel.getRangeAt(i).cloneContents());
      }
      return container.innerHTML;
    } else {
      return "None";
    }
  }
  var html = exec(get_selected_html);
  return escape_html(html);
}

function quote(text) {
  if (!text) return " ";
  return `"${text}"`;
}

function execute_python_script(args) {
  let cur_app = Application.currentApplication(); // eslint-disable-line no-undef
  cur_app.includeStandardAdditions = true;
  cur_app.doShellScript(
    [
      "cd",
      "~/Library/Services/comfort",
      "&&",
      "venv/bin/python",
      "-m",
      "comfort_browser_ext",
      ...args,
    ].join(" ")
  );
}

function process_sales_order() {
  let customer_name = get_customer_name();
  let vk_url = get_vk_url();
  let html = get_html();
  execute_python_script([
    "process_sales_order",
    quote(customer_name),
    quote(vk_url),
    quote(html),
  ]);
}

function validate_ikea_url() {
  var url = exec(() => location.href);
  if (!(url && url.match("ikea.com"))) {
    exit("Вы находитесь не на сайте IKEA");
  }
}

function get_token() {
  function _get_cookie(name) {
    // https://stackoverflow.com/questions/51312980/how-to-get-and-set-cookies-in-javascript
    var nameEQ = name + "=";
    var ca = document.cookie.split(";");
    for (var i = 0; i < ca.length; i++) {
      var c = ca[i];
      while (c.charAt(0) == " ") c = c.substring(1, c.length);
      if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
  }

  return _get_cookie("idp_reguser");
}

function update_token() {
  validate_ikea_url();
  let token = exec(get_token);
  execute_python_script(["update_token", token]);
  Safari.displayAlert("Информация для входа обновлена");
}

// eslint-disable-next-line no-unused-vars
function run() {
  let url = exec(() => location.href);
  if (url && url.match("vk.com")) {
    process_sales_order();
  } else if (url && url.match("ikea.com")) {
    update_token();
  } else {
    exit("Вы находитесь не на сайте VK или IKEA");
  }
}
