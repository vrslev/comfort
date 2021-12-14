/* global chrome */

async function get_tab() {
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.url.match("(127.0.0.1)|(new.vrs.family)")) {
    return tab;
  }
}

async function get_token() {
  let cookies = await chrome.cookies.getAll({ domain: ".ikea.com" });
  for (let cookie of cookies) {
    if (cookie.name == "idp_reguser") {
      return cookie.value;
    }
  }
}

async function send_token(tab, token) {
  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    // https://developer.chrome.com/docs/extensions/reference/scripting/#type-ExecutionWorld
    world: "MAIN",
    args: [token],
    func: (token) => {
      frappe.call("comfort.integrations.browser_ext.update_token", {
        token: token,
      });
    },
  });
}

async function main() {
  let tab = await get_tab();
  if (!tab) {
    alert("Go to ERP site");
    return;
  }

  let token = await get_token();
  if (!token) {
    chrome.tabs.create({
      url: "https://ikea.com/ru/ru/profile/login",
    });
    alert("Log in IKEA");
    return;
  }

  send_token(tab, token);
}

let el = document.getElementsByClassName("updater");
el[0].addEventListener("click", main);
