frappe.listview_settings["Purchase Order"] = {
  add_fields: ["status"],
  get_indicator: function (doc) {
    if (in_list(["Cancelled", "Draft"], doc.status)) {
      return [__(doc.status), "red"];
    } else if (doc.status == "To Receive") {
      return [__(doc.status), "orange"];
    } else if (doc.status === "Completed") {
      return [__(doc.status), "green"];
    }
  },
};
