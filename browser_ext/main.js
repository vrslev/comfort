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

function get_html() {
  function get_selected_html() {
    var html = "";
    if (typeof window.getSelection != "undefined") {
      var sel = window.getSelection();
      if (sel.rangeCount) {
        var container = document.createElement("div");
        for (var i = 0, len = sel.rangeCount; i < len; ++i) {
          container.appendChild(sel.getRangeAt(i).cloneContents());
        }
        html = container.innerHTML;
      }
    } else if (typeof document.selection != "undefined") {
      if (document.selection.type == "Text") {
        html = document.selection.createRange().htmlText;
      }
    }
    return html;
  }
  var html = exec(get_selected_html);
  if (!html) exit("Выделите текст");
  return html;
}

function escape_quotes(text) {
  if (!text) return;
  text.replace('"', '"');
  return `"${text}"`;
}

function execute_python_script(customer_name, vk_url, html) {
  var cur_app = Application.currentApplication(); // eslint-disable-line no-undef
  cur_app.includeStandardAdditions = true;
  cur_app.doShellScript(
    [
      "cd",
      "~/github/comfort-browser-ext",
      "&&",
      "venv/bin/python",
      "-m",
      "comfort_browser_ext",
      escape_quotes(customer_name),
      escape_quotes(vk_url),
      escape_quotes(html),
    ].join(" ")
  );
}

// eslint-disable-next-line no-unused-vars
function run() {
  let customer_name = get_customer_name();
  let vk_url = get_vk_url();
  let html = get_html();
  execute_python_script(customer_name, vk_url, html);
}
