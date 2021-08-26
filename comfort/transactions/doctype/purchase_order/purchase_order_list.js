frappe.listview_settings["Purchase Order"] = {
  add_fields: ["status"],
  get_indicator: (doc) => {
    // TODO: This not working
    if (["Cancelled", "Draft"].includes(doc.status)) {
      return [__(doc.status), "red"];
    } else if (doc.status == "To Receive") {
      return [__(doc.status), "orange"];
    } else if (doc.status === "Completed") {
      return [__(doc.status), "green"];
    }
  },
};
