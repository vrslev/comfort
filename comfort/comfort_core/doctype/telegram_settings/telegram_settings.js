frappe.ui.form.on("Telegram Settings", {
  get_chat_id(frm) {
    frappe.confirm(__("To proceed you need to add bot to the chat"), () => {
      frappe.call({
        method:
          "comfort.comfort_core.doctype.telegram_settings.telegram_settings.get_chats",
        callback: (r) => {
          let ids = r.message.map((c) => c.id);
          let titles = r.message.map((c) => c.title);
          frappe.prompt(
            {
              label: __("Chat"),
              fieldname: "chat",
              fieldtype: "Select",
              options: titles.join("\n"),
            },
            ({ chat }) => {
              frm.set_value("chat_id", ids[titles.findIndex((c) => c == chat)]);
              frm.save();
            }
          );
        },
      });
    });
  },
});
